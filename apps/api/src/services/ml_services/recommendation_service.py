"""
Servicio de recomendaciones inteligentes de inventario.

Genera dos tipos de alertas accionables:
  1. restock     — productos que se están agotando
  2. dead_stock  — capital inmovilizado sin movimiento

Fuentes de datos (sin ML externo):
  - products          : stock actual, mínimos, precios
  - invoice_line_items + processed_invoices : historial de compras como
                        proxy de velocidad de rotación
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import AsyncSessionFactory
from ...database.models import (
    InvoiceLineItem,
    ProcessedInvoice,
    Product,
)

logger = logging.getLogger(__name__)

# ── Configuración de umbrales ────────────────────────────────────────────────
DEAD_STOCK_DAYS       = 45      # días sin movimiento → capital muerto
WARNING_STOCK_RATIO   = 1.5     # current_stock ≤ min*1.5 → advertencia
VELOCITY_WINDOW_DAYS  = 90      # ventana para calcular velocidad de compra
MIN_CAPITAL_ALERT     = 50_000  # capital mínimo para alertar (COP)


# ── Dataclasses internos ─────────────────────────────────────────────────────

@dataclass
class _Velocity:
    product_code: str
    total_qty: float
    invoice_count: int
    last_date: Optional[datetime]
    per_day: float          # unidades compradas / día


@dataclass
class RestockRec:
    type: str = "restock"
    priority: str = "warning"           # critical | warning
    product_code: str = ""
    description: str = ""
    category: Optional[str] = None
    supplier_name: Optional[str] = None
    current_stock: float = 0
    min_stock: float = 0
    suggested_qty: float = 0
    last_price: Optional[float] = None
    estimated_cost: float = 0
    days_until_stockout: Optional[int] = None
    velocity_per_day: Optional[float] = None
    insight: str = ""


@dataclass
class DeadStockRec:
    type: str = "dead_stock"
    priority: str = "medium"            # high | medium
    product_code: str = ""
    description: str = ""
    category: Optional[str] = None
    current_stock: float = 0
    capital_tied: float = 0
    days_without_movement: int = 0
    potential_monthly_gain: float = 0
    alternatives: list = field(default_factory=list)
    insight: str = ""


# ── Servicio principal ───────────────────────────────────────────────────────

class RecommendationService:

    async def get_recommendations(self, tenant_id: str) -> dict:
        async with AsyncSessionFactory() as session:
            velocities = await self._calc_velocities(session, tenant_id)
            restock    = await self._restock_alerts(session, tenant_id, velocities)
            dead       = await self._dead_stock_alerts(session, tenant_id, velocities)

        return {
            "restock":      [_to_dict(r) for r in restock],
            "dead_stock":   [_to_dict(r) for r in dead],
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_restock":   len(restock),
                "critical_restock": sum(1 for r in restock if r.priority == "critical"),
                "total_dead_stock": len(dead),
                "total_capital_tied": sum(r.capital_tied for r in dead),
            },
        }

    # ── Velocidades ──────────────────────────────────────────────────────────

    async def _calc_velocities(
        self, session: AsyncSession, tenant_id: str
    ) -> dict[str, _Velocity]:
        """
        Velocidad de compra por product_code desde invoice_line_items
        en los últimos VELOCITY_WINDOW_DAYS días.
        """
        cutoff = datetime.utcnow() - timedelta(days=VELOCITY_WINDOW_DAYS)

        rows = (await session.execute(
            select(
                InvoiceLineItem.product_code,
                func.sum(InvoiceLineItem.quantity).label("total_qty"),
                func.count(ProcessedInvoice.id.distinct()).label("inv_count"),
                func.max(ProcessedInvoice.upload_timestamp).label("last_date"),
            )
            .join(ProcessedInvoice, InvoiceLineItem.invoice_id == ProcessedInvoice.id)
            .where(and_(
                ProcessedInvoice.tenant_id == tenant_id,
                ProcessedInvoice.status == "completed",
                ProcessedInvoice.upload_timestamp >= cutoff,
                InvoiceLineItem.product_code.isnot(None),
            ))
            .group_by(InvoiceLineItem.product_code)
        )).all()

        result: dict[str, _Velocity] = {}
        for row in rows:
            qty = float(row.total_qty or 0)
            if row.product_code and qty > 0:
                result[row.product_code] = _Velocity(
                    product_code=row.product_code,
                    total_qty=qty,
                    invoice_count=row.inv_count,
                    last_date=row.last_date,
                    per_day=qty / VELOCITY_WINDOW_DAYS,
                )
        return result

    # ── Alertas de reabastecimiento ──────────────────────────────────────────

    async def _restock_alerts(
        self, session: AsyncSession, tenant_id: str, velocities: dict
    ) -> list[RestockRec]:

        products = (await session.execute(
            select(Product)
            .where(and_(
                Product.tenant_id == tenant_id,
                Product.min_stock > 0,
                Product.current_stock <= Product.min_stock * WARNING_STOCK_RATIO,
            ))
            .order_by(Product.current_stock / Product.min_stock)
        )).scalars().all()

        recs: list[RestockRec] = []
        for p in products:
            current    = float(p.current_stock or 0)
            minimum    = float(p.min_stock or 0)
            maximum    = float(p.max_stock) if p.max_stock else minimum * 3
            last_price = float(p.last_purchase_price) if p.last_purchase_price else None
            vel        = velocities.get(p.product_code)

            priority       = "critical" if current <= minimum else "warning"
            suggested_qty  = max(maximum - current, minimum)
            estimated_cost = suggested_qty * last_price if last_price else 0

            days_until: Optional[int] = None
            if vel and vel.per_day > 0:
                days_until = max(0, int(current / vel.per_day))

            recs.append(RestockRec(
                priority=priority,
                product_code=p.product_code,
                description=p.description,
                category=p.category,
                supplier_name=p.supplier_name,
                current_stock=current,
                min_stock=minimum,
                suggested_qty=round(suggested_qty),
                last_price=last_price,
                estimated_cost=round(estimated_cost),
                days_until_stockout=days_until,
                velocity_per_day=round(vel.per_day, 2) if vel else None,
                insight=_restock_text(
                    p.description, current, minimum, suggested_qty,
                    p.supplier_name, last_price, estimated_cost, days_until, priority,
                ),
            ))
        return recs

    # ── Capital muerto ───────────────────────────────────────────────────────

    async def _dead_stock_alerts(
        self, session: AsyncSession, tenant_id: str, velocities: dict
    ) -> list[DeadStockRec]:

        # Última fecha de compra por product_code desde facturas
        last_dates: dict[str, datetime] = {
            row.product_code: row.last_date
            for row in (await session.execute(
                select(
                    InvoiceLineItem.product_code,
                    func.max(ProcessedInvoice.upload_timestamp).label("last_date"),
                )
                .join(ProcessedInvoice, InvoiceLineItem.invoice_id == ProcessedInvoice.id)
                .where(and_(
                    ProcessedInvoice.tenant_id == tenant_id,
                    ProcessedInvoice.status == "completed",
                    InvoiceLineItem.product_code.isnot(None),
                ))
                .group_by(InvoiceLineItem.product_code)
            )).all()
            if row.product_code
        }

        products = (await session.execute(
            select(Product)
            .where(and_(
                Product.tenant_id == tenant_id,
                Product.current_stock > 0,
                Product.last_purchase_price.isnot(None),
            ))
        )).scalars().all()

        # Índice por categoría para buscar alternativas
        by_category: dict[str, list[Product]] = {}
        for p in products:
            by_category.setdefault(p.category or "Sin categoría", []).append(p)

        now  = datetime.utcnow()
        recs: list[DeadStockRec] = []

        for p in products:
            last_date = last_dates.get(p.product_code)
            if last_date:
                days_since = (now - last_date).days
            else:
                # Sin historial en facturas: usar updated_at como proxy
                days_since = (now - p.updated_at).days if p.updated_at else DEAD_STOCK_DAYS + 1

            if days_since < DEAD_STOCK_DAYS:
                continue

            capital = float(p.current_stock) * float(p.last_purchase_price)
            if capital < MIN_CAPITAL_ALERT:
                continue

            alternatives = _find_alternatives(p, by_category.get(p.category or "", []), velocities)
            gain         = _monthly_gain(capital, alternatives)
            priority     = "high" if capital > 500_000 else "medium"

            recs.append(DeadStockRec(
                priority=priority,
                product_code=p.product_code,
                description=p.description,
                category=p.category,
                current_stock=float(p.current_stock),
                capital_tied=round(capital),
                days_without_movement=days_since,
                potential_monthly_gain=round(gain),
                alternatives=alternatives,
                insight=_dead_stock_text(
                    p.description, days_since, capital, p.category, alternatives, gain,
                ),
            ))

        recs.sort(key=lambda r: r.capital_tied, reverse=True)
        return recs


# ── Helpers internos ─────────────────────────────────────────────────────────

def _to_dict(rec) -> dict:
    return rec.__dict__


def _find_alternatives(
    product: Product,
    peers: list[Product],
    velocities: dict,
) -> list[dict]:
    """Productos de la misma categoría con mejor rotación."""
    alts = []
    for p in peers:
        if p.id == product.id:
            continue
        vel = velocities.get(p.product_code)
        if not vel:
            continue
        margin = None
        if p.sale_price and p.last_purchase_price:
            sale = float(p.sale_price)
            cost = float(p.last_purchase_price)
            if cost > 0:
                margin = round((sale - cost) / sale * 100, 1)
        alts.append({
            "product_code":   p.product_code,
            "description":    p.description,
            "velocity_per_day": round(vel.per_day, 2),
            "margin":         margin,
        })
    alts.sort(key=lambda a: a["velocity_per_day"], reverse=True)
    return alts[:3]


def _monthly_gain(capital: float, alternatives: list[dict]) -> float:
    if not alternatives or not capital:
        return 0
    margin = alternatives[0].get("margin") or 0
    return round(capital * (margin / 100)) if margin > 0 else 0


# ── Builders de texto (templates en español) ─────────────────────────────────

def _restock_text(
    description: str,
    current: float,
    minimum: float,
    suggested_qty: float,
    supplier: Optional[str],
    last_price: Optional[float],
    estimated_cost: float,
    days_until: Optional[int],
    priority: str,
) -> str:
    if current == 0:
        stock_part = "está agotado"
    else:
        stock_part = f"tiene {current:.0f} unidades (mínimo: {minimum:.0f})"

    if days_until is None:
        timing = " Sin historial de consumo suficiente para proyectar fecha."
    elif days_until == 0:
        timing = " Se agotó."
    elif days_until <= 3:
        timing = f" Se agota en {days_until} día{'s' if days_until != 1 else ''}. ¡Urgente!"
    elif days_until <= 7:
        timing = f" Se agota en ~{days_until} días."
    else:
        timing = f" A este ritmo se agota en ~{days_until} días."

    supplier_part = f" Proveedor: {supplier}." if supplier else ""

    if last_price and estimated_cost:
        price_part = (
            f" Último precio: ${last_price:,.0f}/u."
            f" Comprar {suggested_qty:.0f} u = ~${estimated_cost:,.0f}."
        )
    else:
        price_part = f" Se recomienda comprar {suggested_qty:.0f} unidades."

    return f"{description} {stock_part}.{timing}{supplier_part}{price_part}"


def _dead_stock_text(
    description: str,
    days: int,
    capital: float,
    category: Optional[str],
    alternatives: list[dict],
    gain: float,
) -> str:
    capital_str = f"${capital:,.0f}"

    if alternatives:
        alt  = alternatives[0]
        name = alt["description"]
        vel  = alt.get("velocity_per_day")
        mgn  = alt.get("margin")
        alt_part = f" En la misma categoría ({category}), {name}"
        if vel:
            alt_part += f" rota {vel:.1f} u/día"
        if mgn:
            alt_part += f" con {mgn:.1f}% de margen"
        alt_part += "."
    else:
        alt_part = ""

    gain_part = (
        f" Liquidar y reinvertir podría generar ~${gain:,.0f}/mes adicionales."
        if gain > 0 else ""
    )

    return (
        f"{description} lleva {days} días sin movimiento "
        f"con {capital_str} inmovilizados.{alt_part}{gain_part}"
    )


# ── Singleton ────────────────────────────────────────────────────────────────

recommendation_service = RecommendationService()
