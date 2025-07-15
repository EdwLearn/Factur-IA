"""
Invoice-specific data models for Colombian retail invoices
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
from decimal import Decimal

class InvoiceStatus(str, Enum):
    """Invoice processing status"""
    UPLOADED = "uploaded"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATED = "validated"

class InvoiceType(str, Enum):
    """Type of invoice document"""
    FACTURA_VENTA = "factura_venta"
    REMISION = "remision"
    ORDEN_PEDIDO = "orden_pedido"
    COTIZACION = "cotizacion"

# Supplier/Company Info
class SupplierInfo(BaseModel):
    """Supplier/company information"""
    company_name: Optional[str] = None
    nit: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None

# Customer Info  
class CustomerInfo(BaseModel):
    """Customer information"""
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None  # NIT/CC
    address: Optional[str] = None
    city: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None

# Individual line item
class InvoiceLineItem(BaseModel):
    """Individual product line in invoice"""
    line_number: Optional[int] = None
    product_code: Optional[str] = None
    description: str = Field(..., description="Product description")
    reference: Optional[str] = None
    quantity: Decimal = Field(..., description="Quantity ordered")
    unit_price: Decimal = Field(..., description="Price per unit")
    subtotal: Decimal = Field(..., description="Line total")
    unit_measure: Optional[str] = "UNIDAD"
    box_number: Optional[str] = None  # For organization
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
    
class InvoiceTotals(BaseModel):
    """Invoice totals and taxes"""
    subtotal: Decimal = Field(default=Decimal("0"), description="Subtotal before taxes")
    iva_rate: Optional[Decimal] = Field(None, description="IVA rate %")
    iva_amount: Optional[Decimal] = Field(None, description="IVA amount")
    retenciones: Optional[Decimal] = Field(None, description="Retenciones amount")
    total: Decimal = Field(default=Decimal("0"), description="Final total")
    total_items: Optional[int] = Field(None, description="Total number of items")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class PaymentInfo(BaseModel):
    """Payment terms and info"""
    payment_method: Optional[str] = None
    credit_days: Optional[int] = None
    due_date: Optional[date] = None
    discount_percentage: Optional[Decimal] = None
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat() if v else None
        }

# Main Invoice Model
class InvoiceData(BaseModel):
    """Complete extracted invoice data"""
    # Document info
    invoice_number: Optional[str] = None
    invoice_type: Optional[InvoiceType] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    
    # Company info
    supplier: SupplierInfo = Field(default_factory=SupplierInfo)
    customer: CustomerInfo = Field(default_factory=CustomerInfo)
    
    # Sales info
    salesperson: Optional[str] = None
    elaborated_by: Optional[str] = None
    
    # Items
    line_items: List[InvoiceLineItem] = Field(default_factory=list)
    
    # Totals
    totals: InvoiceTotals = Field(default_factory=InvoiceTotals)
    
    # Payment
    payment_info: PaymentInfo = Field(default_factory=PaymentInfo)
    
    # Additional info
    observations: Optional[str] = None
    authorization: Optional[str] = None
    cufe: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
            Decimal: lambda v: float(v)
        }

class ProcessedInvoice(BaseModel):
    """Processed invoice with metadata"""
    id: str = Field(..., description="Unique invoice ID")
    tenant_id: str = Field(..., description="Tenant identifier")
    original_filename: str
    file_size: Optional[int] = None
    upload_timestamp: datetime
    processing_timestamp: Optional[datetime] = None
    completion_timestamp: Optional[datetime] = None
    
    # Processing info
    status: InvoiceStatus = InvoiceStatus.UPLOADED
    confidence_score: Optional[float] = None
    processing_time_seconds: Optional[float] = None
    error_message: Optional[str] = None
    
    # Extracted data (opcional - solo se incluye cuando se solicita)
    invoice_data: Optional[InvoiceData] = None
    
    # Storage info
    s3_key: Optional[str] = None
    textract_job_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
            Decimal: lambda v: float(v)
        }

# Tenant Management
class Tenant(BaseModel):
    """Multi-tenant support"""
    tenant_id: str = Field(..., description="Unique tenant identifier")
    company_name: str
    nit: Optional[str] = None
    email: str
    phone: Optional[str] = None
    plan: str = "freemium"  # freemium, basic, premium
    invoices_processed_month: int = 0
    max_invoices_month: int = 10
    created_at: datetime
    is_active: bool = True
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class BillingRecord(BaseModel):
    """Billing record for invoice processing"""
    id: str
    tenant_id: str
    invoice_id: str
    processing_date: datetime
    cost_cop: Decimal  # Cost in Colombian pesos
    invoice_type: InvoiceType
    pages_processed: int
    confidence_score: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            Decimal: lambda v: float(v)
        }
