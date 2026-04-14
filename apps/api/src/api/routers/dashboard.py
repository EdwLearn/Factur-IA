"""
Dashboard analytics and metrics endpoints

Proporciona métricas agregadas y análisis para el dashboard principal:
- KPIs del negocio
- Facturas recientes
- Análisis de tendencias
- Comparaciones período sobre período
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, desc, text
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

            return DashboardMetrics(
                total_invoices_month=total_invoices_month,
                total_inventory_value=total_inventory_value,
                pending_alerts=pending_alerts,
                total_suppliers=total_suppliers,
                month_over_month_invoices=round(mom_invoices, 1),
                month_over_month_inventory=8.0  # TODO: Calculate real MoM inventory growth
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
