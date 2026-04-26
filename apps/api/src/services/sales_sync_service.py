"""
Sincronización de ventas desde Alegra → inventory_movements
y cálculo de rotación de inventario por producto.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import AsyncSessionFactory
from ..database.models import AlegraConnection, InventoryMovement, Product
from .integrations.alegra_integration import decrypt_token, AlegraClient

logger = logging.getLogger(__name__)


class SalesSyncService:

    async def sync_sales_from_alegra(
        self,
        tenant_id: str,
        date_start: str = None,
    ) -> dict:
        """
        Sincroniza ventas de Alegra → inventory_movements (tipo='salida').

        Obtiene las credenciales del tenant desde AlegraConnection,
        llama GET /invoices y registra cada línea de venta como
        un movimiento de salida idempotente.

        Retorna { synced, errors, date_start }.
        """
        if not date_start:
            date_start = (date.today() - timedelta(days=30)).isoformat()

        async with AsyncSessionFactory() as session:
            conn = await self._get_alegra_connection(session, tenant_id)
            if not conn:
                return {"synced": 0, "errors": 0, "date_start": date_start,
                        "error": "Alegra no conectado para este tenant"}

            try:
                raw_token = decrypt_token(conn.alegra_token)
            except Exception as exc:
                logger.error(f"Token Alegra inválido para {tenant_id}: {exc}")
                return {"synced": 0, "errors": 1, "date_start": date_start,
                        "error": "Token Alegra inválido"}

            client = AlegraClient(email=conn.alegra_user_email, token=raw_token)

            try:
                invoices = await client.get_invoices(
                    date_start=date_start,
                    limit=30,  # Alegra sandbox limita a 30 por request
                )
            except Exception as exc:
                logger.error(f"Error al traer facturas de Alegra para {tenant_id}: {exc}")
                return {"synced": 0, "errors": 1, "date_start": date_start,
                        "error": str(exc)}

            synced = 0
            errors = 0

            for invoice in invoices:
                try:
                    count = await self._process_sale_invoice(
                        session=session,
                        tenant_id=tenant_id,
                        invoice=invoice,
                    )
                    synced += count
                except Exception as exc:
                    logger.error(
                        f"Error procesando venta {invoice.get('id')} "
                        f"para tenant {tenant_id}: {exc}"
                    )
                    errors += 1

            await session.commit()

        return {"synced": synced, "errors": errors, "date_start": date_start}

    async def _get_alegra_connection(
        self, session: AsyncSession, tenant_id: str
    ) -> AlegraConnection | None:
        result = await session.execute(
            select(AlegraConnection).where(
                AlegraConnection.tenant_id == tenant_id,
                AlegraConnection.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def _process_sale_invoice(
        self,
        session: AsyncSession,
        tenant_id: str,
        invoice: dict,
    ) -> int:
        """
        Procesa una factura de venta de Alegra y registra las salidas
        en inventory_movements. Retorna la cantidad de líneas sincronizadas.
        """
        invoice_id = str(invoice.get("id", ""))
        invoice_date_raw = invoice.get("date", "")

        # Alegra devuelve fechas como "YYYY-MM-DD" o como objeto
        if isinstance(invoice_date_raw, dict):
            invoice_date_raw = invoice_date_raw.get("date", "")

        try:
            invoice_date = date.fromisoformat(str(invoice_date_raw)[:10])
        except (ValueError, TypeError):
            invoice_date = date.today()

        items = invoice.get("items", [])
        synced = 0

        for item in items:
            item_id = str(item.get("id", ""))
            quantity = float(item.get("quantity", 0) or 0)
            price = float(item.get("price", 0) or 0)
            name = item.get("name", "") or ""
            origen_id = f"{invoice_id}_{item_id}"

            if quantity <= 0:
                continue

            # Deduplicación idempotente
            existing = await session.execute(
                select(InventoryMovement).where(
                    InventoryMovement.tenant_id == tenant_id,
                    InventoryMovement.origen == "factura_venta_alegra",
                    InventoryMovement.origen_id == origen_id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Buscar producto local por alegra_item_id
            product_result = await session.execute(
                select(Product).where(
                    Product.tenant_id == tenant_id,
                    Product.alegra_item_id == item_id,
                )
            )
            product = product_result.scalar_one_or_none()

            movement = InventoryMovement(
                tenant_id=tenant_id,
                product_id=product.id if product else None,
                product_code=product.product_code if product else None,
                description=name,
                quantity=Decimal(str(quantity)),
                movement_type="sale",        # campo original — requerido NOT NULL
                tipo="salida",
                origen="factura_venta_alegra",
                origen_id=origen_id,
                unit_price=Decimal(str(price)),
                fecha=invoice_date,
            )
            session.add(movement)

            if product:
                product.current_stock = max(
                    Decimal("0"),
                    (product.current_stock or Decimal("0")) - Decimal(str(quantity)),
                )
                product.quantity = int(product.current_stock)
                session.add(product)

            synced += 1

        return synced

    async def calculate_rotation(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> list[dict]:
        """
        Calcula rotación de inventario por producto para el período indicado.

        Rotación = unidades_vendidas / stock_actual
        Días de stock = stock_actual / (unidades_vendidas / days)
        """
        async with AsyncSessionFactory() as session:
            rows = await session.execute(
                text("""
                    SELECT
                        im.product_id,
                        im.description,
                        SUM(im.quantity)                   AS unidades_vendidas,
                        SUM(im.quantity * im.unit_price)   AS valor_vendido,
                        p.current_stock                    AS stock_actual
                    FROM inventory_movements im
                    LEFT JOIN products p ON im.product_id = p.id
                    WHERE im.tenant_id   = :tenant_id
                      AND im.tipo        = 'salida'
                      AND im.origen      = 'factura_venta_alegra'
                      AND im.fecha       >= CURRENT_DATE - CAST(:days AS INT) * INTERVAL '1 day'
                    GROUP BY im.product_id, im.description, p.current_stock
                    ORDER BY unidades_vendidas DESC
                """),
                {"tenant_id": tenant_id, "days": days},
            )

            resultado = []
            for row in rows:
                unidades = float(row.unidades_vendidas or 0)
                stock = float(row.stock_actual or 0)
                valor = float(row.valor_vendido or 0)

                rotacion = round(unidades / stock, 2) if stock > 0 else 0.0
                dias_stock = (
                    round(stock / (unidades / days), 0)
                    if unidades > 0
                    else 999.0
                )

                resultado.append({
                    "product_id": str(row.product_id) if row.product_id else None,
                    "description": row.description or "",
                    "unidades_vendidas": unidades,
                    "valor_vendido": valor,
                    "stock_actual": stock,
                    "rotacion": rotacion,
                    "dias_stock": dias_stock,
                })

        return resultado
