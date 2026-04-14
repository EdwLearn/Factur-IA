"""
InvoiceRepository — all database access for ProcessedInvoice and InvoiceLineItem.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import InvoiceLineItem, ProcessedInvoice


class InvoiceRepository:
    """Encapsulates every query that touches processed_invoices and invoice_line_items."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # ProcessedInvoice queries
    # ------------------------------------------------------------------

    async def get_by_id(
        self, invoice_id: uuid.UUID, tenant_id: str
    ) -> Optional[ProcessedInvoice]:
        """Return invoice owned by tenant, or None if not found."""
        result = await self._session.execute(
            select(ProcessedInvoice)
            .where(ProcessedInvoice.id == invoice_id)
            .where(ProcessedInvoice.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self, tenant_id: str, limit: int = 10, offset: int = 0
    ) -> List[ProcessedInvoice]:
        """Return paginated invoices for a tenant, newest first."""
        result = await self._session.execute(
            select(ProcessedInvoice)
            .where(ProcessedInvoice.tenant_id == tenant_id)
            .order_by(ProcessedInvoice.upload_timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_pricing_status(
        self, invoice: ProcessedInvoice, status: str
    ) -> None:
        """Persist a pricing_status change on an already-loaded invoice object."""
        invoice.pricing_status = status
        await self._session.commit()

    # ------------------------------------------------------------------
    # InvoiceLineItem queries
    # ------------------------------------------------------------------

    async def get_line_items(
        self, invoice_id: uuid.UUID
    ) -> List[InvoiceLineItem]:
        """Return all line items for an invoice."""
        result = await self._session.execute(
            select(InvoiceLineItem)
            .where(InvoiceLineItem.invoice_id == invoice_id)
            .order_by(InvoiceLineItem.line_number)
        )
        return list(result.scalars().all())

    async def get_line_item(
        self, line_item_id: uuid.UUID, invoice_id: uuid.UUID
    ) -> Optional[InvoiceLineItem]:
        """Return a single line item that belongs to the given invoice, or None."""
        result = await self._session.execute(
            select(InvoiceLineItem)
            .where(InvoiceLineItem.id == line_item_id)
            .where(InvoiceLineItem.invoice_id == invoice_id)
        )
        return result.scalar_one_or_none()
