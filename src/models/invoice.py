"""
Invoice-specific data models for Colombian retail invoices
"""
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, Field, UUID4, validator
from typing import Optional, List, Dict, Any
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

class PricingStatus(str, Enum):
    """Pricing status for invoices"""
    NOT_REQUIRED = "not_required"      # For non-purchase invoices
    PENDING = "pending"                 # Waiting for manual pricing
    PARTIAL = "partial"                 # Some items priced
    COMPLETED = "completed"             # All items priced
    CONFIRMED = "confirmed"             # Pricing confirmed, ready for inventory

class InvoiceLineItemWithPricing(InvoiceLineItem):
    """Line item with pricing information"""
    sale_price: Optional[Decimal] = None
    markup_percentage: Optional[Decimal] = None
    is_priced: bool = False
    
    # Calculated fields
    total_cost: Optional[Decimal] = None
    total_sale_value: Optional[Decimal] = None
    total_profit: Optional[Decimal] = None
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v else None
        }

class PricingRequest(BaseModel):
    """Request to set pricing for line items"""
    line_items: List[Dict[str, Any]] = Field(..., description="Line items with pricing")
    
    class Config:
        json_schema_extra = {
            "example": {
                "line_items": [
                    {
                        "line_item_id": "abc123",
                        "sale_price": 12000.00
                    }
                ]
            }
        }

class PricingSummary(BaseModel):
    """Summary of pricing for an invoice"""
    total_items: int
    priced_items: int
    pending_items: int
    total_cost: Decimal
    total_sale_value: Decimal
    total_profit: Decimal
    average_markup: Decimal
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


# Modelos adicionales que necesitamos para el sistema de pricing

class LineItemPricingUpdate(BaseModel):
    """Individual line item pricing update"""
    line_item_id: UUID4
    sale_price: Decimal = Field(..., gt=0, description="Sale price must be greater than 0")
    
    @validator('sale_price')
    def validate_sale_price(cls, v):
        if v <= 0:
            raise ValueError('Sale price must be greater than 0')
        return round(v, 2)

class PricingUpdateRequest(BaseModel):
    """Request model for POST /pricing endpoint"""
    line_items: List[LineItemPricingUpdate]
    
    @validator('line_items')
    def validate_line_items(cls, v):
        if not v:
            raise ValueError('At least one line item must be provided')
        return v

class InvoiceLineItemPricing(BaseModel):
    """Line item for pricing display"""
    id: UUID4
    line_item_id: UUID4
    product_code: Optional[str]
    description: str
    quantity: Decimal
    unit_price: Decimal  # Precio de compra
    subtotal: Decimal
    sale_price: Optional[Decimal] = None  # Precio de venta manual
    markup_percentage: Optional[Decimal] = None  # Margen calculado
    profit_margin: Optional[Decimal] = None  # Margen de ganancia
    is_priced: bool = False
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v else None
        }

class PricingDataResponse(BaseModel):
    """Response model for GET /pricing endpoint"""
    invoice_id: UUID4
    invoice_number: Optional[str]
    supplier_name: Optional[str] 
    issue_date: Optional[str]
    total_amount: Decimal
    pricing_status: PricingStatus
    line_items: List[InvoiceLineItemPricing]
    summary: Optional[PricingSummary] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v else None
        }

class PricingConfirmationResponse(BaseModel):
    """Response for pricing confirmation"""
    invoice_id: UUID4
    pricing_status: PricingStatus
    total_items_priced: int
    inventory_updates: List[Dict[str, Any]] = Field(default_factory=list)
    summary: PricingSummary
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v else None
        }

# Utility functions for pricing calculations
def calculate_markup_percentage(cost_price: Decimal, sale_price: Decimal) -> Decimal:
    """Calculate markup percentage: ((sale_price - cost_price) / cost_price) * 100"""
    if cost_price <= 0:
        return Decimal('0')
    return round(((sale_price - cost_price) / cost_price) * 100, 2)

def calculate_profit_margin(cost_price: Decimal, sale_price: Decimal) -> Decimal:
    """Calculate profit margin: ((sale_price - cost_price) / sale_price) * 100"""
    if sale_price <= 0:
        return Decimal('0')
    return round(((sale_price - cost_price) / sale_price) * 100, 2)

def calculate_pricing_summary(line_items: List[InvoiceLineItemPricing]) -> PricingSummary:
    """Calculate pricing summary for invoice"""
    total_items = len(line_items)
    priced_items = sum(1 for item in line_items if item.is_priced)
    pending_items = total_items - priced_items
    
    total_cost = sum(item.subtotal for item in line_items)
    total_sale_value = sum(
        (item.sale_price or Decimal('0')) * item.quantity 
        for item in line_items if item.sale_price
    )
    total_profit = total_sale_value - total_cost
    
    average_markup = Decimal('0')
    if priced_items > 0 and total_cost > 0:
        average_markup = (total_profit / total_cost) * 100
    
    return PricingSummary(
        total_items=total_items,
        priced_items=priced_items,
        pending_items=pending_items,
        total_cost=total_cost,
        total_sale_value=total_sale_value,
        total_profit=total_profit,
        average_markup=round(average_markup, 2)
    )