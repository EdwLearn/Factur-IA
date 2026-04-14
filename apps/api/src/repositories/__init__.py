"""
Repository layer — encapsulates all database access.

Each repository receives an AsyncSession and exposes
named methods for every query pattern used in the app.
Repositories never raise HTTPException; that is the router's job.
"""
from .invoice_repository import InvoiceRepository
from .tenant_repository import TenantRepository

__all__ = ["InvoiceRepository", "TenantRepository"]
