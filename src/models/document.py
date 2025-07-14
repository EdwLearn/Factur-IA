"""
Legacy document models - keeping for compatibility
"""
from .invoice import (
    ProcessedInvoice,
    InvoiceData, 
    InvoiceStatus,
    InvoiceType,
    Tenant,
    BillingRecord
)

# Re-export for backward compatibility
DocumentResponse = ProcessedInvoice
ProcessingStatus = InvoiceStatus

# Keep original models for any existing integrations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DocumentCreate(BaseModel):
    """Schema for creating a new document"""
    filename: str = Field(..., description="Original filename")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    content_type: str = Field(default="application/pdf")
    tenant_id: str = Field(..., description="Tenant identifier")
