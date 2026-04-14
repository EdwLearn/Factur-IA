"""
Suppliers router.

GET  /api/v1/suppliers                      – lista con métricas
GET  /api/v1/suppliers/{nit}/invoices       – facturas de un proveedor
PUT  /api/v1/suppliers/{nit}                – actualiza datos de contacto
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, desc, func, select

from ...database.connection import AsyncSessionFactory
from ...database.models import ProcessedInvoice, Supplier
from ..deps import get_tenant_id

logger = logging.getLogger(__name__)
router = APIRouter()

_ACTIVE_DAYS = 90   # sin factura en 90 días → inactivo
_NEW_DAYS = 30      # primera factura en los últimos 30 días → nuevo este mes


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SupplierOut(BaseModel):
    id: str
    name: str
    vatNumber: str
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    status: str                        # "active" | "inactive"
    totalInvoices: int
    totalAmount: float
    lastInvoiceDate: Optional[str] = None   # ISO date string
    joinDate: str                            # ISO date string (first invoice)


class SupplierMetrics(BaseModel):
    total_suppliers: int
    active_suppliers: int
    new_this_month: int


class SuppliersListResponse(BaseModel):
    suppliers: list[SupplierOut]
    total: int
    metrics: SupplierMetrics


class SupplierUpdate(BaseModel):
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    department: Optional[str] = None


class SupplierInvoiceOut(BaseModel):
    id: str
    invoice_number: Optional[str] = None
    issue_date: Optional[str] = None
    total_amount: float
    status: str
    upload_timestamp: str
    original_filename: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("", response_model=SuppliersListResponse)
async def list_suppliers(
    tenant_id: str = Depends(get_tenant_id),
    search: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = None,
):
    """
    Lista proveedores del tenant con métricas derivadas de processed_invoices.
    """
    now_utc = datetime.now(tz=timezone.utc)
    active_cutoff = now_utc - timedelta(days=_ACTIVE_DAYS)
    new_cutoff = now_utc - timedelta(days=_NEW_DAYS)

    async with AsyncSessionFactory() as session:
        # ── 1. Aggregate stats per (supplier_nit, name, city, address, phone) ──
        agg = (
            select(
                ProcessedInvoice.supplier_nit.label("nit"),
                ProcessedInvoice.supplier_name.label("company_name"),
                ProcessedInvoice.supplier_city.label("city"),
                ProcessedInvoice.supplier_address.label("address"),
                ProcessedInvoice.supplier_phone.label("phone"),
                func.count(ProcessedInvoice.id).label("total_invoices"),
                func.coalesce(func.sum(ProcessedInvoice.total_amount), 0).label("total_amount"),
                func.max(ProcessedInvoice.upload_timestamp).label("last_invoice_date"),
                func.min(ProcessedInvoice.upload_timestamp).label("first_invoice_date"),
            )
            .where(
                and_(
                    ProcessedInvoice.tenant_id == tenant_id,
                    ProcessedInvoice.supplier_nit.isnot(None),
                    ProcessedInvoice.supplier_nit != "",
                )
            )
            .group_by(
                ProcessedInvoice.supplier_nit,
                ProcessedInvoice.supplier_name,
                ProcessedInvoice.supplier_city,
                ProcessedInvoice.supplier_address,
                ProcessedInvoice.supplier_phone,
            )
        )
        rows = (await session.execute(agg)).all()

        # ── 2. Fetch emails from suppliers table ──
        nits = [r.nit for r in rows if r.nit]
        email_map: dict[str, str] = {}
        if nits:
            sup_q = await session.execute(
                select(Supplier.nit, Supplier.email)
                .where(Supplier.tenant_id == tenant_id)
                .where(Supplier.nit.in_(nits))
            )
            email_map = {r.nit: r.email for r in sup_q.all() if r.email}

    # ── 3. Build full supplier list with derived status ──
    def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    full: list[SupplierOut] = []
    for row in rows:
        last_dt = _to_utc(row.last_invoice_date)
        first_dt = _to_utc(row.first_invoice_date)
        derived_status = "active" if (last_dt and last_dt >= active_cutoff) else "inactive"

        full.append(SupplierOut(
            id=row.nit,
            name=row.company_name or row.nit,
            vatNumber=row.nit,
            email=email_map.get(row.nit),
            phone=row.phone,
            city=row.city,
            address=row.address,
            status=derived_status,
            totalInvoices=int(row.total_invoices),
            totalAmount=float(row.total_amount),
            lastInvoiceDate=last_dt.date().isoformat() if last_dt else None,
            joinDate=first_dt.date().isoformat() if first_dt else now_utc.date().isoformat(),
        ))

    # ── 4. Compute metrics on the FULL list (before any filter) ──
    metrics = SupplierMetrics(
        total_suppliers=len(full),
        active_suppliers=sum(1 for s in full if s.status == "active"),
        new_this_month=sum(
            1 for s in full
            if s.joinDate >= new_cutoff.date().isoformat()
        ),
    )

    # ── 5. Apply optional filters ──
    if search:
        q = search.lower()
        full = [s for s in full if q in s.name.lower() or q in s.vatNumber.lower()]
    if city and city != "all":
        full = [s for s in full if s.city == city]
    if status and status not in ("all", ""):
        full = [s for s in full if s.status == status]

    return SuppliersListResponse(suppliers=full, total=len(full), metrics=metrics)


# ---------------------------------------------------------------------------
# GET /suppliers/{nit}/invoices
# ---------------------------------------------------------------------------

@router.get("/{nit}/invoices", response_model=List[SupplierInvoiceOut])
async def get_supplier_invoices(
    nit: str,
    tenant_id: str = Depends(get_tenant_id),
    limit: int = 100,
):
    """Lista todas las facturas vinculadas a un proveedor por NIT."""
    async with AsyncSessionFactory() as session:
        q = (
            select(ProcessedInvoice)
            .where(
                and_(
                    ProcessedInvoice.tenant_id == tenant_id,
                    ProcessedInvoice.supplier_nit == nit,
                )
            )
            .order_by(desc(ProcessedInvoice.upload_timestamp))
            .limit(limit)
        )
        rows = (await session.execute(q)).scalars().all()

    result = []
    for inv in rows:
        result.append(SupplierInvoiceOut(
            id=str(inv.id),
            invoice_number=inv.invoice_number,
            issue_date=inv.issue_date.isoformat() if inv.issue_date else None,
            total_amount=float(inv.total_amount) if inv.total_amount else 0.0,
            status=inv.status,
            upload_timestamp=inv.upload_timestamp.isoformat() if inv.upload_timestamp else "",
            original_filename=inv.original_filename,
        ))
    return result


# ---------------------------------------------------------------------------
# PUT /suppliers/{nit}
# ---------------------------------------------------------------------------

@router.put("/{nit}", response_model=SupplierOut)
async def update_supplier(
    nit: str,
    data: SupplierUpdate,
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Actualiza los datos de contacto de un proveedor.
    Hace upsert en la tabla suppliers; los campos derivados de facturas
    (totalInvoices, totalAmount, etc.) se recalculan en el GET de lista.
    """
    now_utc = datetime.now(tz=timezone.utc)

    async with AsyncSessionFactory() as session:
        # Buscar registro existente
        existing = (await session.execute(
            select(Supplier).where(
                and_(Supplier.tenant_id == tenant_id, Supplier.nit == nit)
            )
        )).scalar_one_or_none()

        if existing:
            if data.company_name is not None:
                existing.company_name = data.company_name
            if data.email is not None:
                existing.email = data.email
            if data.phone is not None:
                existing.phone = data.phone
            if data.address is not None:
                existing.address = data.address
            if data.city is not None:
                existing.city = data.city
            if data.department is not None:
                existing.department = data.department
            existing.updated_at = now_utc
        else:
            # Obtener nombre desde la última factura si no se envía
            inv_row = (await session.execute(
                select(ProcessedInvoice.supplier_name)
                .where(
                    and_(
                        ProcessedInvoice.tenant_id == tenant_id,
                        ProcessedInvoice.supplier_nit == nit,
                    )
                )
                .order_by(desc(ProcessedInvoice.upload_timestamp))
                .limit(1)
            )).scalar_one_or_none()

            existing = Supplier(
                tenant_id=tenant_id,
                nit=nit,
                company_name=data.company_name or inv_row or nit,
                email=data.email,
                phone=data.phone,
                address=data.address,
                city=data.city,
                department=data.department,
            )
            session.add(existing)

        await session.commit()
        await session.refresh(existing)

    # Reconstruir SupplierOut desde la BD agregada
    async with AsyncSessionFactory() as session:
        agg = (
            select(
                func.count(ProcessedInvoice.id).label("total_invoices"),
                func.coalesce(func.sum(ProcessedInvoice.total_amount), 0).label("total_amount"),
                func.max(ProcessedInvoice.upload_timestamp).label("last_invoice_date"),
                func.min(ProcessedInvoice.upload_timestamp).label("first_invoice_date"),
            )
            .where(
                and_(
                    ProcessedInvoice.tenant_id == tenant_id,
                    ProcessedInvoice.supplier_nit == nit,
                )
            )
        )
        stats = (await session.execute(agg)).one()

    active_cutoff = now_utc - timedelta(days=_ACTIVE_DAYS)

    def _to_utc(dt):
        if dt is None:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    last_dt = _to_utc(stats.last_invoice_date)
    first_dt = _to_utc(stats.first_invoice_date)

    return SupplierOut(
        id=nit,
        name=existing.company_name,
        vatNumber=nit,
        email=existing.email,
        phone=existing.phone,
        city=existing.city,
        address=existing.address,
        status="active" if (last_dt and last_dt >= active_cutoff) else "inactive",
        totalInvoices=int(stats.total_invoices),
        totalAmount=float(stats.total_amount),
        lastInvoiceDate=last_dt.date().isoformat() if last_dt else None,
        joinDate=first_dt.date().isoformat() if first_dt else now_utc.date().isoformat(),
    )
