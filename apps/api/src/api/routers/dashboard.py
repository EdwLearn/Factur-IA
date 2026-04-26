"""
Dashboard analytics and metrics endpoints

Proporciona métricas agregadas y análisis para el dashboard principal:
- KPIs del negocio
- Facturas recientes
- Análisis de tendencias
- Comparaciones período sobre período
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ...database.connection import AsyncSessionFactory
from ...database.models import ProcessedInvoice as Invoice, InvoiceLineItem, Product, Supplier
from ...models.invoice import InvoiceStatus
from pydantic import BaseModel
from ..deps import get_tenant_id

logger = logging.getLogger(__name__)
router = APIRouter(
    responses={
        401: {"description": "No autorizado - falta x-tenant-id"},
        500: {"description": "Error interno del servidor"}
    }
)


# Pydantic models for responses
class DashboardMetrics(BaseModel):
    """Main dashboard metrics"""
    total_invoices_month: int
    total_inventory_value: float
    pending_alerts: int
    total_suppliers: int
    total_products: int
    month_over_month_invoices: float
    month_over_month_inventory: float


class RecentInvoice(BaseModel):
    """Recent invoice summary"""
    id: str
    supplier_name: str
    status: str
    total: float
    items_count: int
    upload_timestamp: datetime
    processing_duration_seconds: int | None = None


class PurchaseVolumeData(BaseModel):
    """Purchase volume data point"""
    period: str
    volume: float


class MarginTrendData(BaseModel):
    """Margin trend data point"""
    month: str
    margin: float


class InventoryProjectionData(BaseModel):
    """Inventory projection data point"""
    product: str
    current: int
    projected: int


class AnalyticsData(BaseModel):
    """Analytics data for charts"""
    purchase_volume: List[PurchaseVolumeData]
    margin_trend: List[MarginTrendData]
    inventory_projection: List[InventoryProjectionData]
    comparison_metrics: Dict[str, Any]


@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get main dashboard metrics
    Returns aggregated statistics for the current month
    """
    try:
        async with AsyncSessionFactory() as session:
            # Calculate date ranges
            now = datetime.utcnow()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

            # Count invoices this month
            invoices_this_month_query = select(func.count(Invoice.id)).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.upload_timestamp >= month_start
                )
            )
            result = await session.execute(invoices_this_month_query)
            total_invoices_month = result.scalar() or 0

            # Count invoices previous month
            invoices_prev_month_query = select(func.count(Invoice.id)).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.upload_timestamp >= prev_month_start,
                    Invoice.upload_timestamp < month_start
                )
            )
            result = await session.execute(invoices_prev_month_query)
            total_invoices_prev_month = result.scalar() or 0

            # Calculate month over month growth
            if total_invoices_prev_month > 0:
                mom_invoices = ((total_invoices_month - total_invoices_prev_month) / total_invoices_prev_month) * 100
            else:
                mom_invoices = 100.0 if total_invoices_month > 0 else 0.0

            # Count unique suppliers
            suppliers_query = select(func.count(func.distinct(Invoice.supplier_nit))).where(
                Invoice.tenant_id == tenant_id
            )
            result = await session.execute(suppliers_query)
            total_suppliers = result.scalar() or 0

            # Calculate total inventory value (products with sale_price set)
            inventory_value_query = select(
                func.sum(Product.quantity * Product.sale_price)
            ).where(
                and_(
                    Product.tenant_id == tenant_id,
                    Product.sale_price.isnot(None),
                    Product.quantity > 0
                )
            )
            result = await session.execute(inventory_value_query)
            total_inventory_value = float(result.scalar() or 0)

            # Count pending alerts (invoices in processing or with errors)
            alerts_query = select(func.count(Invoice.id)).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.status.in_(['processing', 'failed', 'pending'])
                )
            )
            result = await session.execute(alerts_query)
            pending_alerts = result.scalar() or 0

            # Count total products in catalog
            products_count_query = select(func.count(Product.id)).where(
                Product.tenant_id == tenant_id
            )
            result = await session.execute(products_count_query)
            total_products = result.scalar() or 0

            return DashboardMetrics(
                total_invoices_month=total_invoices_month,
                total_inventory_value=total_inventory_value,
                pending_alerts=pending_alerts,
                total_suppliers=total_suppliers,
                total_products=total_products,
                month_over_month_invoices=round(mom_invoices, 1),
                month_over_month_inventory=8.0
            )

    except Exception as e:
        logger.error(f"Error fetching dashboard metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")


@router.get("/recent-invoices", response_model=List[RecentInvoice])
async def get_recent_invoices(
    limit: int = 10,
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get recent invoices with summary information
    """
    try:
        async with AsyncSessionFactory() as session:
            # Query recent invoices
            query = (
                select(Invoice)
                .where(Invoice.tenant_id == tenant_id)
                .order_by(desc(Invoice.upload_timestamp))
                .limit(limit)
            )

            result = await session.execute(query)
            invoices = result.scalars().all()

            recent_invoices = []
            for invoice in invoices:
                # Count line items
                items_query = select(func.count(InvoiceLineItem.id)).where(
                    InvoiceLineItem.invoice_id == invoice.id
                )
                items_result = await session.execute(items_query)
                items_count = items_result.scalar() or 0

                # Calculate processing duration if completed
                processing_duration = None
                if invoice.completion_timestamp and invoice.upload_timestamp:
                    duration = invoice.completion_timestamp - invoice.upload_timestamp
                    processing_duration = int(duration.total_seconds())

                recent_invoices.append(RecentInvoice(
                    id=str(invoice.id),
                    supplier_name=invoice.supplier_name or "Unknown Supplier",
                    status=invoice.status or "pending",
                    total=float(invoice.total_amount or 0),
                    items_count=items_count,
                    upload_timestamp=invoice.upload_timestamp,
                    processing_duration_seconds=processing_duration
                ))

            return recent_invoices

    except Exception as e:
        logger.error(f"Error fetching recent invoices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch recent invoices: {str(e)}")


@router.get("/analytics", response_model=AnalyticsData)
async def get_analytics_data(
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get analytics data for dashboard charts
    Includes purchase volume, margin trends, and inventory projections
    """
    try:
        async with AsyncSessionFactory() as session:
            # Calculate date ranges for weekly purchase volume (last 8 weeks)
            now = datetime.utcnow()
            weeks_data = []

            for i in range(8, 0, -1):
                week_end = now - timedelta(weeks=i-1)
                week_start = week_end - timedelta(weeks=1)

                # Sum total amount for this week
                week_query = select(func.sum(Invoice.total_amount)).where(
                    and_(
                        Invoice.tenant_id == tenant_id,
                        Invoice.upload_timestamp >= week_start,
                        Invoice.upload_timestamp < week_end,
                        Invoice.status == 'completed'
                    )
                )
                result = await session.execute(week_query)
                volume = float(result.scalar() or 0)

                weeks_data.append(PurchaseVolumeData(
                    period=f"Sem {9-i}",
                    volume=volume
                ))

            # Calculate margin trends (last 8 months)
            margin_trends = []
            month_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

            for i in range(8, 0, -1):
                # Calculate month range
                month_end = now - timedelta(days=(i-1)*30)
                month_start = month_end - timedelta(days=30)

                # Get line items with pricing for this month
                margin_query = select(
                    func.avg(
                        ((InvoiceLineItem.sale_price - InvoiceLineItem.unit_price) /
                         InvoiceLineItem.unit_price * 100)
                    ).label('avg_margin')
                ).select_from(InvoiceLineItem).join(
                    Invoice, InvoiceLineItem.invoice_id == Invoice.id
                ).where(
                    and_(
                        Invoice.tenant_id == tenant_id,
                        Invoice.upload_timestamp >= month_start,
                        Invoice.upload_timestamp < month_end,
                        InvoiceLineItem.sale_price.isnot(None),
                        InvoiceLineItem.unit_price > 0,
                        Invoice.status == 'completed'
                    )
                )

                result = await session.execute(margin_query)
                avg_margin = result.scalar()

                # Use default margin if no data
                margin_value = float(avg_margin) if avg_margin else 0.0

                # Get month name
                month_idx = (month_end.month - 1) % 12
                month_name = month_names[month_idx]

                margin_trends.append(MarginTrendData(
                    month=month_name,
                    margin=round(margin_value, 1) if margin_value else 0.0
                ))

            # Get top 5 products for inventory projection
            top_products_query = (
                select(Product.description, Product.quantity)
                .where(
                    and_(
                        Product.tenant_id == tenant_id,
                        Product.quantity > 0
                    )
                )
                .order_by(desc(Product.quantity))
                .limit(5)
            )
            result = await session.execute(top_products_query)
            products = result.all()

            inventory_projections = []
            for product_name, current_qty in products:
                # Simple projection: assume 30% depletion over 30 days
                projected_qty = int(current_qty * 0.7)
                inventory_projections.append(InventoryProjectionData(
                    product=product_name[:20],  # Truncate name
                    current=current_qty,
                    projected=projected_qty
                ))

            # Comparison metrics (this month vs previous)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

            # Invoices processed
            current_month_invoices = select(func.count(Invoice.id)).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.upload_timestamp >= month_start
                )
            )
            result = await session.execute(current_month_invoices)
            current_count = result.scalar() or 0

            prev_month_invoices = select(func.count(Invoice.id)).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.upload_timestamp >= prev_month_start,
                    Invoice.upload_timestamp < month_start
                )
            )
            result = await session.execute(prev_month_invoices)
            prev_count = result.scalar() or 0

            # Calculate percentages
            invoices_change = ((current_count - prev_count) / prev_count * 100) if prev_count > 0 else 0

            # Calculate total revenue (current month)
            current_revenue_query = select(func.sum(Invoice.total_amount)).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.upload_timestamp >= month_start,
                    Invoice.status == 'completed'
                )
            )
            result = await session.execute(current_revenue_query)
            current_revenue = float(result.scalar() or 0)

            # Calculate previous month revenue
            prev_revenue_query = select(func.sum(Invoice.total_amount)).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.upload_timestamp >= prev_month_start,
                    Invoice.upload_timestamp < month_start,
                    Invoice.status == 'completed'
                )
            )
            result = await session.execute(prev_revenue_query)
            prev_revenue = float(result.scalar() or 0)

            revenue_change = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0

            # Count new products (current month)
            new_products_query = select(func.count(Product.id)).where(
                and_(
                    Product.tenant_id == tenant_id,
                    Product.created_at >= month_start
                )
            )
            result = await session.execute(new_products_query)
            new_products = result.scalar() or 0

            # Count products from previous month
            prev_products_query = select(func.count(Product.id)).where(
                and_(
                    Product.tenant_id == tenant_id,
                    Product.created_at >= prev_month_start,
                    Product.created_at < month_start
                )
            )
            result = await session.execute(prev_products_query)
            prev_new_products = result.scalar() or 0

            products_change = ((new_products - prev_new_products) / prev_new_products * 100) if prev_new_products > 0 else 0

            # Calculate average processing time (current month)
            avg_time_query = select(
                func.avg(
                    func.extract('epoch', Invoice.completion_timestamp - Invoice.upload_timestamp) / 60
                )
            ).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.upload_timestamp >= month_start,
                    Invoice.completion_timestamp.isnot(None),
                    Invoice.status == 'completed'
                )
            )
            result = await session.execute(avg_time_query)
            avg_time_minutes = float(result.scalar() or 0)

            # Calculate average processing time (previous month)
            prev_avg_time_query = select(
                func.avg(
                    func.extract('epoch', Invoice.completion_timestamp - Invoice.upload_timestamp) / 60
                )
            ).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.upload_timestamp >= prev_month_start,
                    Invoice.upload_timestamp < month_start,
                    Invoice.completion_timestamp.isnot(None),
                    Invoice.status == 'completed'
                )
            )
            result = await session.execute(prev_avg_time_query)
            prev_avg_time = float(result.scalar() or 0)

            time_change = ((avg_time_minutes - prev_avg_time) / prev_avg_time * 100) if prev_avg_time > 0 else 0

            comparison_metrics = {
                "invoices_processed": current_count,
                "invoices_change": round(invoices_change, 1),
                "total_revenue": int(current_revenue),
                "revenue_change": round(revenue_change, 1),
                "new_products": new_products,
                "products_change": round(products_change, 1),
                "avg_processing_time_minutes": round(avg_time_minutes, 1),
                "time_change": round(time_change, 1)
            }

            return AnalyticsData(
                purchase_volume=weeks_data,
                margin_trend=margin_trends,
                inventory_projection=inventory_projections,
                comparison_metrics=comparison_metrics
            )

    except Exception as e:
        logger.error(f"Error fetching analytics data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")


@router.get("/reports")
async def get_reports_data(
    tenant_id: str = Depends(get_tenant_id),
    months: int = 12,
):
    """
    Get data for the Reports tab:
    - Monthly invoice history (count + value) for the last N months
    - Top 5 suppliers by purchase volume
    - Top 10 products by inventory value
    """
    try:
        async with AsyncSessionFactory() as session:
            now = datetime.utcnow()
            start_date = now - timedelta(days=months * 30)
            month_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                           "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

            # ── Monthly invoices ────────────────────────────────────────────
            # Using text() for GROUP BY/ORDER BY avoids the PostgreSQL
            # "different parameter slots" error with date_trunc + bound params.
            monthly_query = (
                select(
                    func.date_trunc(text("'month'"), Invoice.upload_timestamp).label("month"),
                    func.count(Invoice.id).label("count"),
                    func.coalesce(func.sum(Invoice.total_amount), 0).label("total"),
                )
                .where(
                    and_(
                        Invoice.tenant_id == tenant_id,
                        Invoice.upload_timestamp >= start_date,
                    )
                )
                .group_by(text("date_trunc('month', upload_timestamp)"))
                .order_by(text("date_trunc('month', upload_timestamp)"))
            )
            result = await session.execute(monthly_query)
            monthly_invoices = [
                {
                    "month": f"{month_names[row.month.month - 1]} {row.month.year}",
                    "invoices": row.count,
                    "value": float(row.total),
                }
                for row in result.all()
            ]

            # ── Top suppliers ───────────────────────────────────────────────
            suppliers_query = (
                select(
                    Invoice.supplier_name,
                    func.count(Invoice.id).label("invoices"),
                    func.coalesce(func.sum(Invoice.total_amount), 0).label("volume"),
                )
                .where(
                    and_(
                        Invoice.tenant_id == tenant_id,
                        Invoice.upload_timestamp >= start_date,
                        Invoice.supplier_name.isnot(None),
                    )
                )
                .group_by(Invoice.supplier_name)
                .order_by(desc(func.sum(Invoice.total_amount)))
                .limit(5)
            )
            result = await session.execute(suppliers_query)
            top_suppliers = [
                {
                    "name": row.supplier_name,
                    "invoices": row.invoices,
                    "volume": float(row.volume),
                }
                for row in result.all()
            ]

            # ── Top products by inventory value ─────────────────────────────
            products_query = (
                select(
                    Product.product_code,
                    Product.description,
                    Product.quantity,
                    Product.sale_price,
                    Product.last_purchase_price,
                )
                .where(
                    and_(
                        Product.tenant_id == tenant_id,
                        Product.sale_price.isnot(None),
                        Product.quantity > 0,
                    )
                )
                .order_by(desc(Product.quantity * Product.sale_price))
                .limit(10)
            )
            result = await session.execute(products_query)
            top_products = []
            for row in result.all():
                sale = float(row.sale_price or 0)
                cost = float(row.last_purchase_price or 0)
                margin = (
                    round((sale - cost) / sale * 100, 1)
                    if sale > 0 and cost > 0
                    else None
                )
                top_products.append(
                    {
                        "product_code": row.product_code or "",
                        "description": row.description or "",
                        "quantity": float(row.quantity or 0),
                        "sale_price": sale,
                        "cost_price": cost,
                        "inventory_value": float(row.quantity or 0) * sale,
                        "margin": margin,
                    }
                )

            return {
                "monthly_invoices": monthly_invoices,
                "top_suppliers": top_suppliers,
                "top_products": top_products,
            }

    except Exception as e:
        logger.error(f"Error fetching reports data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch reports: {str(e)}")


# ─── New dashboard chart models ───────────────────────────────────────────────

class TopSupplierItem(BaseModel):
    name: str
    nit: str | None
    total_gasto: float
    num_facturas: int

class TopSuppliersResponse(BaseModel):
    suppliers: List[TopSupplierItem]

class TopProductItem(BaseModel):
    description: str
    product_code: str | None
    cantidad_total: float
    gasto_total: float
    num_facturas: int

class TopProductsResponse(BaseModel):
    products: List[TopProductItem]

class PriceEvolutionPoint(BaseModel):
    semana: str
    precio_promedio: float
    precio_min: float
    precio_max: float
    supplier: str | None

class PriceEvolutionResponse(BaseModel):
    product: str
    evolution: List[PriceEvolutionPoint]

class PriceAlertItem(BaseModel):
    description: str
    product_code: str | None
    precio_actual: float
    precio_anterior: float
    variacion_pct: float
    supplier: str | None
    subio: bool

class PriceAlertsResponse(BaseModel):
    alerts: List[PriceAlertItem]


# ─── Endpoint 1: Top suppliers by spend this month ────────────────────────────

@router.get("/top-suppliers", response_model=TopSuppliersResponse)
async def get_top_suppliers(tenant_id: str = Depends(get_tenant_id)):
    """Top 5 suppliers by total spend in the current month (confirmed + completed invoices)."""
    try:
        async with AsyncSessionFactory() as session:
            query = (
                select(
                    Invoice.supplier_name,
                    Invoice.supplier_nit,
                    func.sum(Invoice.total_amount).label("total_gasto"),
                    func.count(Invoice.id).label("num_facturas"),
                )
                .where(
                    and_(
                        Invoice.tenant_id == tenant_id,
                        Invoice.status.in_(["confirmed", "completed"]),
                        func.date_trunc(text("'month'"), Invoice.upload_timestamp)
                        == func.date_trunc(text("'month'"), func.now()),
                    )
                )
                .group_by(Invoice.supplier_name, Invoice.supplier_nit)
                .order_by(desc(func.sum(Invoice.total_amount)))
                .limit(5)
            )
            result = await session.execute(query)
            rows = result.all()
            suppliers = [
                TopSupplierItem(
                    name=row.supplier_name or "Desconocido",
                    nit=row.supplier_nit,
                    total_gasto=float(row.total_gasto or 0),
                    num_facturas=int(row.num_facturas or 0),
                )
                for row in rows
            ]
            return TopSuppliersResponse(suppliers=suppliers)
    except Exception as e:
        logger.error(f"Error fetching top suppliers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch top suppliers: {str(e)}")


# ─── Endpoint 2: Most purchased products this month ───────────────────────────

@router.get("/top-products", response_model=TopProductsResponse)
async def get_top_products(tenant_id: str = Depends(get_tenant_id)):
    """Top 8 products by total quantity purchased in the current month (confirmed + completed invoices)."""
    try:
        async with AsyncSessionFactory() as session:
            query = (
                select(
                    InvoiceLineItem.description,
                    InvoiceLineItem.product_code,
                    func.sum(InvoiceLineItem.quantity).label("cantidad_total"),
                    func.sum(InvoiceLineItem.subtotal).label("gasto_total"),
                    func.count(func.distinct(InvoiceLineItem.invoice_id)).label("num_facturas"),
                )
                .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
                .where(
                    and_(
                        Invoice.tenant_id == tenant_id,
                        Invoice.status.in_(["confirmed", "completed"]),
                        func.date_trunc(text("'month'"), Invoice.upload_timestamp)
                        == func.date_trunc(text("'month'"), func.now()),
                    )
                )
                .group_by(InvoiceLineItem.description, InvoiceLineItem.product_code)
                .order_by(desc(func.sum(InvoiceLineItem.quantity)))
                .limit(8)
            )
            result = await session.execute(query)
            rows = result.all()
            products = [
                TopProductItem(
                    description=row.description or "",
                    product_code=row.product_code,
                    cantidad_total=float(row.cantidad_total or 0),
                    gasto_total=float(row.gasto_total or 0),
                    num_facturas=int(row.num_facturas or 0),
                )
                for row in rows
            ]
            return TopProductsResponse(products=products)
    except Exception as e:
        logger.error(f"Error fetching top products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch top products: {str(e)}")


# ─── Endpoint 3: Price evolution of a product (last 6 months) ─────────────────

@router.get("/price-evolution", response_model=PriceEvolutionResponse)
async def get_price_evolution(
    product_code: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    tenant_id: str = Depends(get_tenant_id),
):
    """Weekly price evolution for a product over the last 6 months."""
    search = product_code or description or ""
    if not search:
        return PriceEvolutionResponse(product="", evolution=[])

    try:
        async with AsyncSessionFactory() as session:
            search_pattern = f"%{search}%"
            six_months_ago = datetime.utcnow() - timedelta(days=180)

            query = (
                select(
                    func.date_trunc(text("'week'"), Invoice.upload_timestamp).label("semana"),
                    func.avg(InvoiceLineItem.unit_price).label("precio_promedio"),
                    func.min(InvoiceLineItem.unit_price).label("precio_min"),
                    func.max(InvoiceLineItem.unit_price).label("precio_max"),
                    Invoice.supplier_name,
                )
                .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
                .where(
                    and_(
                        Invoice.tenant_id == tenant_id,
                        or_(
                            InvoiceLineItem.product_code.ilike(search_pattern),
                            InvoiceLineItem.description.ilike(search_pattern),
                        ),
                        Invoice.upload_timestamp >= six_months_ago,
                    )
                )
                .group_by(
                    text("date_trunc('week', upload_timestamp)"),
                    Invoice.supplier_name,
                )
                .order_by(text("date_trunc('week', upload_timestamp) ASC"))
            )
            result = await session.execute(query)
            rows = result.all()
            evolution = [
                PriceEvolutionPoint(
                    semana=row.semana.strftime("%Y-%m-%d") if row.semana else "",
                    precio_promedio=round(float(row.precio_promedio or 0), 2),
                    precio_min=round(float(row.precio_min or 0), 2),
                    precio_max=round(float(row.precio_max or 0), 2),
                    supplier=row.supplier_name,
                )
                for row in rows
            ]
            return PriceEvolutionResponse(product=search, evolution=evolution)
    except Exception as e:
        logger.error(f"Error fetching price evolution: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch price evolution: {str(e)}")


# ─── Endpoint 4: Price alerts (>10% variation vs previous purchase) ───────────

@router.get("/price-alerts", response_model=PriceAlertsResponse)
async def get_price_alerts(tenant_id: str = Depends(get_tenant_id)):
    """Products whose unit price changed more than 10% vs the previous purchase."""
    try:
        async with AsyncSessionFactory() as session:
            sql = text("""
                WITH ranked AS (
                    SELECT
                        ili.description,
                        ili.product_code,
                        ili.unit_price,
                        pi.upload_timestamp,
                        pi.supplier_name,
                        ROW_NUMBER() OVER (
                            PARTITION BY ili.description
                            ORDER BY pi.upload_timestamp DESC
                        ) AS rn
                    FROM invoice_line_items ili
                    JOIN processed_invoices pi ON ili.invoice_id = pi.id
                    WHERE pi.tenant_id = :tenant_id
                      AND pi.status = 'confirmed'
                ),
                precio_actual AS (
                    SELECT description, product_code, unit_price AS precio_actual,
                           supplier_name
                    FROM ranked WHERE rn = 1
                ),
                precio_anterior AS (
                    SELECT description, unit_price AS precio_anterior
                    FROM ranked WHERE rn = 2
                )
                SELECT
                    pa.description,
                    pa.product_code,
                    pa.precio_actual,
                    pant.precio_anterior,
                    pa.supplier_name,
                    ROUND(
                        ((pa.precio_actual - pant.precio_anterior)
                         / NULLIF(pant.precio_anterior, 0) * 100)::numeric, 1
                    ) AS variacion_pct
                FROM precio_actual pa
                JOIN precio_anterior pant ON pa.description = pant.description
                WHERE ABS(
                    (pa.precio_actual - pant.precio_anterior)
                    / NULLIF(pant.precio_anterior, 0) * 100
                ) >= 10
                ORDER BY ABS(variacion_pct) DESC
                LIMIT 10
            """)
            result = await session.execute(sql, {"tenant_id": tenant_id})
            rows = result.all()
            alerts = [
                PriceAlertItem(
                    description=row.description or "",
                    product_code=row.product_code,
                    precio_actual=float(row.precio_actual or 0),
                    precio_anterior=float(row.precio_anterior or 0),
                    variacion_pct=float(row.variacion_pct or 0),
                    supplier=row.supplier_name,
                    subio=float(row.variacion_pct or 0) > 0,
                )
                for row in rows
            ]
            return PriceAlertsResponse(alerts=alerts)
    except Exception as e:
        logger.error(f"Error fetching price alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch price alerts: {str(e)}")


# ─── Endpoint 5: Purchase volume by week (last 60 days) ──────────────────────

class PurchaseVolumePoint(BaseModel):
    semana: str
    volumen: float
    num_facturas: int

class PurchaseVolumeResponse(BaseModel):
    data: List[PurchaseVolumePoint]

@router.get("/purchase-volume", response_model=PurchaseVolumeResponse)
async def get_purchase_volume(tenant_id: str = Depends(get_tenant_id)):
    """Weekly purchase volume for the last 60 days (confirmed + completed invoices)."""
    try:
        async with AsyncSessionFactory() as session:
            sql = text("""
                SELECT
                    to_char(date_trunc('week', upload_timestamp), 'DD/MM') AS semana,
                    COALESCE(SUM(total_amount), 0)                          AS volumen,
                    COUNT(*)                                                 AS num_facturas
                FROM processed_invoices
                WHERE tenant_id = :tenant_id
                  AND status IN ('confirmed', 'completed')
                  AND upload_timestamp >= NOW() - INTERVAL '60 days'
                GROUP BY date_trunc('week', upload_timestamp)
                ORDER BY date_trunc('week', upload_timestamp)
            """)
            result = await session.execute(sql, {"tenant_id": tenant_id})
            rows = result.all()
            data = [
                PurchaseVolumePoint(
                    semana=row.semana,
                    volumen=float(row.volumen),
                    num_facturas=int(row.num_facturas),
                )
                for row in rows
            ]
            return PurchaseVolumeResponse(data=data)
    except Exception as e:
        logger.error(f"Error fetching purchase volume: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch purchase volume: {str(e)}")
