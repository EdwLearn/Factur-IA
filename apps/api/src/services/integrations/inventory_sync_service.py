"""
InventorySyncService — Sincronización bidireccional FacturIA ↔ Alegra

Flujo:
  1. PULL  Alegra → FacturIA : actualiza precios locales desde Alegra
  2. PUSH  FacturIA → Alegra : crea/actualiza ítems en Alegra con precios locales
  3. CONTACTS FacturIA → Alegra : crea/actualiza contactos (proveedores) en Alegra

El servicio es tolerante a fallos: un ítem que falla no aborta el resto.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

def _now_naive() -> datetime:
    """Datetime UTC sin timezone para columnas naive de la BD."""
    return datetime.utcnow()

def _now_aware() -> datetime:
    """Datetime UTC con timezone para lógica de comparación."""
    return datetime.now(timezone.utc)

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import AsyncSessionFactory
from ...database.models import Product, Supplier, Tenant
from .alegra_integration import AlegraClient, get_client_from_config

logger = logging.getLogger(__name__)

# Pausa entre llamadas a Alegra para respetar rate limits (ms)
_RATE_LIMIT_DELAY = 0.25


@dataclass
class SyncResult:
    tenant_id: str
    pushed_items: int = 0        # Nuevos ítems creados en Alegra
    updated_items: int = 0       # Ítems actualizados en Alegra
    pulled_items: int = 0        # Precios actualizados desde Alegra
    synced_contacts: int = 0     # Contactos creados/actualizados en Alegra
    errors: list[str] = field(default_factory=list)
    synced_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def total_synced_items(self) -> int:
        return self.pushed_items + self.updated_items + self.pulled_items

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "pushed_items": self.pushed_items,
            "updated_items": self.updated_items,
            "pulled_items": self.pulled_items,
            "synced_contacts": self.synced_contacts,
            "synced_items": self.total_synced_items,
            "errors": self.errors,
            "synced_at": self.synced_at,
        }


class InventorySyncService:
    """Orquesta la sincronización de inventario entre FacturIA y Alegra."""

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    async def sync_tenant(self, tenant_id: str) -> SyncResult:
        """Sincroniza inventario y contactos para un tenant específico."""
        result = SyncResult(tenant_id=tenant_id)

        async with AsyncSessionFactory() as session:
            tenant = (await session.execute(
                select(Tenant).where(Tenant.tenant_id == tenant_id)
            )).scalar_one_or_none()

            if not tenant:
                result.errors.append(f"Tenant {tenant_id} no encontrado")
                return result

            try:
                client = get_client_from_config(tenant.integration_config)
            except ValueError as exc:
                result.errors.append(f"Alegra no conectado: {exc}")
                return result

        # Ejecutar las 3 fases — cada una tiene su propia sesión de BD
        await self._pull_from_alegra(client, tenant_id, result)
        await self._push_to_alegra(client, tenant_id, result)
        await self._sync_contacts(client, tenant_id, result)

        logger.info(
            f"[sync:{tenant_id}] pulled={result.pulled_items} "
            f"pushed={result.pushed_items} updated={result.updated_items} "
            f"contacts={result.synced_contacts} errors={len(result.errors)}"
        )
        return result

    async def sync_all_tenants(self) -> list[SyncResult]:
        """Sincroniza todos los tenants con Alegra conectado. Usado por el job periódico."""
        async with AsyncSessionFactory() as session:
            tenants = (await session.execute(select(Tenant))).scalars().all()

        results = []
        for tenant in tenants:
            cfg = (tenant.integration_config or {}).get("alegra")
            if not cfg or cfg.get("status") != "active":
                continue
            try:
                result = await self.sync_tenant(tenant.tenant_id)
                results.append(result)
            except Exception as exc:
                logger.error(f"[sync:{tenant.tenant_id}] fallo inesperado: {exc}")
                results.append(SyncResult(
                    tenant_id=tenant.tenant_id,
                    errors=[str(exc)],
                ))
        return results

    # ------------------------------------------------------------------
    # Phase 1: PULL — Alegra → FacturIA
    # Actualiza precios de venta locales si Alegra tiene un precio diferente
    # ------------------------------------------------------------------

    async def _pull_from_alegra(
        self, client: AlegraClient, tenant_id: str, result: SyncResult
    ) -> None:
        try:
            alegra_items = await self._get_all_alegra_items(client)
        except Exception as exc:
            result.errors.append(f"PULL fallo al obtener ítems de Alegra: {exc}")
            return

        if not alegra_items:
            return

        # Construir mapa id → item para lookup rápido
        items_by_id: dict[str, dict] = {str(item["id"]): item for item in alegra_items}

        async with AsyncSessionFactory() as session:
            # Solo productos con alegra_item_id conocido
            products = (await session.execute(
                select(Product).where(
                    and_(
                        Product.tenant_id == tenant_id,
                        Product.alegra_item_id.isnot(None),
                    )
                )
            )).scalars().all()

            now = _now_naive()
            updated = 0

            for product in products:
                alegra_item = items_by_id.get(str(product.alegra_item_id))
                if not alegra_item:
                    continue

                alegra_price = _extract_alegra_price(alegra_item)
                if alegra_price is not None and alegra_price > 0:
                    local_price = float(product.sale_price) if product.sale_price else None
                    # Solo actualizar si la diferencia es significativa (> 1%)
                    if local_price is None or abs(alegra_price - local_price) / max(local_price, 1) > 0.01:
                        product.sale_price = alegra_price
                        product.alegra_synced_at = now
                        updated += 1

            if updated:
                await session.commit()
            result.pulled_items = updated

    # ------------------------------------------------------------------
    # Phase 2: PUSH — FacturIA → Alegra
    # Crea ítems sin alegra_item_id; actualiza los que cambiaron precio
    # ------------------------------------------------------------------

    async def _push_to_alegra(
        self, client: AlegraClient, tenant_id: str, result: SyncResult
    ) -> None:
        async with AsyncSessionFactory() as session:
            products = (await session.execute(
                select(Product).where(Product.tenant_id == tenant_id)
            )).scalars().all()

        now = _now_naive()

        for product in products:
            await asyncio.sleep(_RATE_LIMIT_DELAY)
            try:
                if not product.alegra_item_id:
                    alegra_id = await self._create_alegra_item(client, product)
                    if alegra_id:
                        async with AsyncSessionFactory() as session:
                            p = (await session.execute(
                                select(Product).where(Product.id == product.id)
                            )).scalar_one_or_none()
                            if p:
                                p.alegra_item_id = alegra_id
                                p.alegra_synced_at = now
                                await session.commit()
                        result.pushed_items += 1
                else:
                    # Actualizar si el precio cambió desde la última sync
                    # Ambos son naive para que la comparación funcione
                    needs_update = (
                        product.alegra_synced_at is None
                        or (product.updated_at and product.updated_at > product.alegra_synced_at)
                    )
                    if needs_update and product.sale_price:
                        await self._update_alegra_item(client, product)
                        async with AsyncSessionFactory() as session:
                            p = (await session.execute(
                                select(Product).where(Product.id == product.id)
                            )).scalar_one_or_none()
                            if p:
                                p.alegra_synced_at = now
                                await session.commit()
                        result.updated_items += 1

            except Exception as exc:
                msg = f"PUSH ítem '{product.product_code}': {exc}"
                logger.warning(f"[sync:{tenant_id}] {msg}")
                result.errors.append(msg)

    # ------------------------------------------------------------------
    # Phase 3: CONTACTS — Proveedores → Alegra contacts
    # ------------------------------------------------------------------

    async def _sync_contacts(
        self, client: AlegraClient, tenant_id: str, result: SyncResult
    ) -> None:
        async with AsyncSessionFactory() as session:
            suppliers = (await session.execute(
                select(Supplier).where(Supplier.tenant_id == tenant_id)
            )).scalars().all()

        now = _now_naive()

        for supplier in suppliers:
            await asyncio.sleep(_RATE_LIMIT_DELAY)
            try:
                if not supplier.alegra_contact_id:
                    alegra_id = await self._create_alegra_contact(client, supplier)
                    if alegra_id:
                        async with AsyncSessionFactory() as session:
                            s = (await session.execute(
                                select(Supplier).where(Supplier.id == supplier.id)
                            )).scalar_one_or_none()
                            if s:
                                s.alegra_contact_id = alegra_id
                                s.updated_at = now
                                await session.commit()
                        result.synced_contacts += 1
                else:
                    # Actualizar datos de contacto si el proveedor fue modificado
                    await self._update_alegra_contact(client, supplier)
                    result.synced_contacts += 1

            except Exception as exc:
                msg = f"CONTACT '{supplier.company_name}': {exc}"
                logger.warning(f"[sync:{tenant_id}] {msg}")
                result.errors.append(msg)

    # ------------------------------------------------------------------
    # Helpers: Alegra item CRUD
    # ------------------------------------------------------------------

    async def _get_all_alegra_items(self, client: AlegraClient) -> list[dict]:
        """Pagina sobre GET /items hasta obtener todos."""
        all_items: list[dict] = []
        start = 0
        limit = 30
        while True:
            batch = await client.get_items(limit=limit, start=start)
            if not batch:
                break
            all_items.extend(batch)
            if len(batch) < limit:
                break
            start += limit
        return all_items

    async def _create_alegra_item(self, client: AlegraClient, product: Product) -> Optional[str]:
        """Crea el ítem en Alegra y retorna su ID."""
        payload = _build_item_payload(product, is_create=True)
        resp = await client.create_item(payload)
        alegra_id = resp.get("id")
        return str(alegra_id) if alegra_id else None

    async def _update_alegra_item(self, client: AlegraClient, product: Product) -> None:
        """Actualiza el ítem en Alegra usando PUT con payload completo."""
        payload = _build_item_payload(product)
        await client.update_item(str(product.alegra_item_id), payload)

    # ------------------------------------------------------------------
    # Helpers: Alegra contact CRUD
    # ------------------------------------------------------------------

    async def _create_alegra_contact(self, client: AlegraClient, supplier: Supplier) -> Optional[str]:
        """Crea el contacto en Alegra y retorna su ID."""
        payload = _build_contact_payload(supplier)
        resp = await client.create_contact(payload)
        alegra_id = resp.get("id")
        return str(alegra_id) if alegra_id else None

    async def _update_alegra_contact(self, client: AlegraClient, supplier: Supplier) -> None:
        """Actualiza el contacto en Alegra usando PUT con payload completo."""
        payload = _build_contact_payload(supplier)
        await client.update_contact(str(supplier.alegra_contact_id), payload)


# ------------------------------------------------------------------
# Payload builders
# ------------------------------------------------------------------

def _build_item_payload(product: Product, is_create: bool = False) -> dict:
    """
    Construye el payload para crear/actualizar un ítem en Alegra.
    En creación (is_create=True) incluye el bloque inventory requerido por POST /bills.
    En actualizaciones NO se incluye inventory para no pisar la cantidad real en bodega.
    """
    payload: dict = {
        "name": product.description[:255],
        "reference": product.product_code,
        "type": "product",
        "price": [{"idPriceList": 1, "price": float(product.sale_price) if product.sale_price else 0}],
    }

    if is_create:
        payload["status"] = "active"
        payload["inventory"] = {
            "unit": "unit",
            "unitCost": float(product.unit_price) if product.unit_price else 0,
            "warehouses": [{"id": "1", "initialQuantity": 0}],
        }

    return payload


def _build_contact_payload(supplier: Supplier) -> dict:
    """
    Construye el payload para crear un contacto proveedor en Alegra.
    Campos requeridos: name, identification, kindOfPerson, identificationObject.
    """
    # Limpiar el NIT (quitar guión y dígito verificador si viene "XXXXXXXXX-X")
    raw_nit = (supplier.nit or "").strip()
    nit_number = raw_nit.split("-")[0].strip()

    payload: dict = {
        "name": supplier.company_name,
        "identification": nit_number,
        "kindOfPerson": "LEGAL_ENTITY",       # Requerido por Alegra Colombia
        "identificationObject": {
            "type": "NIT",
            "number": nit_number,
        },
        "type": [{"id": "vendor"}],
    }
    if supplier.email:
        payload["email"] = supplier.email
    if supplier.phone:
        payload["phonePrimary"] = supplier.phone
    if supplier.address or supplier.city:
        payload["address"] = {
            "address": supplier.address or "",
            "city": supplier.city or "",
            "department": supplier.department or "",
        }
    return payload


def _extract_alegra_price(alegra_item: dict) -> Optional[float]:
    """Extrae el precio de venta principal de un ítem de Alegra."""
    prices = alegra_item.get("price", [])
    if isinstance(prices, list) and prices:
        # La lista principal de precios — tomar el primero (precio general)
        first = prices[0]
        price_val = first.get("price") if isinstance(first, dict) else None
        if price_val is not None:
            try:
                return float(price_val)
            except (ValueError, TypeError):
                pass
    return None


def _map_unit(unit_measure: str) -> str:
    """Mapea unidades locales a los identificadores que acepta Alegra."""
    mapping = {
        "UNIDAD": "unit",
        "KG": "kg",
        "GRAMO": "g",
        "G": "g",
        "LITRO": "l",
        "L": "l",
        "ML": "ml",
        "CAJA": "box",
        "DOCENA": "dozen",
        "PAR": "pair",
    }
    return mapping.get(unit_measure.upper(), "unit")


# Singleton
inventory_sync_service = InventorySyncService()
