"""
SQLAlchemy models for Invoice SaaS
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Numeric, Date, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime

Base = declarative_base()

class Tenant(Base):
    """Multi-tenant companies"""
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(100), unique=True, nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    nit = Column(String(50))
    email = Column(String(255), nullable=False)
    phone = Column(String(50))
    plan = Column(String(50), default="freemium")  # freemium, basic, premium
    invoices_processed_month = Column(Integer, default=0)
    max_invoices_month = Column(Integer, default=10)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    invoices = relationship("ProcessedInvoice", back_populates="tenant", cascade="all, delete-orphan")
    billing_records = relationship("BillingRecord", back_populates="tenant")

class ProcessedInvoice(Base):
    """Processed invoices with multi-tenant support"""
    __tablename__ = "processed_invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    
    # File info
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer)
    s3_key = Column(Text)
    
    # Processing info
    status = Column(String(50), nullable=False, default="uploaded", index=True)
    confidence_score = Column(Numeric(5, 4))
    processing_time_seconds = Column(Numeric(10, 3))
    error_message = Column(Text)
    
    # Timestamps
    upload_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    processing_timestamp = Column(DateTime)
    completion_timestamp = Column(DateTime)
    
    # AWS Textract info
    textract_job_id = Column(String(255))
    textract_raw_response = Column(JSONB)  # Raw Textract response
    
    # Extracted invoice data (structured)
    invoice_number = Column(String(100), index=True)
    invoice_type = Column(String(50))
    issue_date = Column(Date, index=True)
    due_date = Column(Date)
    
    # Supplier info
    supplier_name = Column(String(255))
    supplier_nit = Column(String(50), index=True)
    supplier_address = Column(Text)
    supplier_city = Column(String(100))
    supplier_department = Column(String(100))
    supplier_phone = Column(String(50))
    
    # Customer info  
    customer_name = Column(String(255), index=True)
    customer_id = Column(String(50))
    customer_address = Column(Text)
    customer_city = Column(String(100))
    customer_department = Column(String(100))
    customer_phone = Column(String(50))
    
    # Sales info
    salesperson = Column(String(255))
    elaborated_by = Column(String(255))
    
    # Totals
    subtotal = Column(Numeric(15, 2))
    iva_rate = Column(Numeric(5, 2))
    iva_amount = Column(Numeric(15, 2))
    retenciones = Column(Numeric(15, 2))
    total_amount = Column(Numeric(15, 2), index=True)
    total_items = Column(Integer)
    
    # Payment info
    payment_method = Column(String(100))
    credit_days = Column(Integer)
    discount_percentage = Column(Numeric(5, 2))
    
    # Additional fields
    observations = Column(Text)
    authorization = Column(Text)
    cufe = Column(String(255))
    
    # Relationships
    tenant = relationship("Tenant", back_populates="invoices")
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")
    
    pricing_status = Column(String(50), default="not_required", nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_tenant_status', 'tenant_id', 'status'),
        Index('idx_tenant_date', 'tenant_id', 'issue_date'),
        Index('idx_supplier_tenant', 'supplier_nit', 'tenant_id'),
    )

class InvoiceLineItem(Base):
    """Individual line items/products in invoices"""
    __tablename__ = "invoice_line_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("processed_invoices.id"), nullable=False, index=True)
    
    # Product info
    line_number = Column(Integer)
    product_code = Column(String(100), index=True)
    description = Column(Text, nullable=False)
    reference = Column(String(255))
    unit_measure = Column(String(50), default="UNIDAD")
    box_number = Column(String(50))
    
    # Quantities and prices
    quantity = Column(Numeric(15, 4), nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False)
    subtotal = Column(Numeric(15, 2), nullable=False)
    
    # Relationships
    invoice = relationship("ProcessedInvoice", back_populates="line_items")
    
    sale_price = Column(Numeric(15, 2), nullable=True)
    markup_percentage = Column(Numeric(5, 2), nullable=True)  
    is_priced = Column(Boolean, default=False, nullable=False)
    
    original_quantity = Column(Numeric(15, 4), nullable=True)
    original_unit = Column(String(20), nullable=True)
    unit_multiplier = Column(Numeric(10, 2), nullable=True, default=1)
    item_number = Column(Integer, nullable=True)
    enhancement_applied = Column(String(100), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_product_code_invoice', 'product_code', 'invoice_id'),
    )

class BillingRecord(Base):
    """Billing records for SaaS usage"""
    __tablename__ = "billing_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("processed_invoices.id"))
    
    processing_date = Column(DateTime, default=datetime.utcnow, index=True)
    cost_cop = Column(Numeric(10, 2), nullable=False)  # Cost in Colombian pesos
    invoice_type = Column(String(50))
    pages_processed = Column(Integer)
    confidence_score = Column(Numeric(5, 4))
    
    # Relationships
    tenant = relationship("Tenant", back_populates="billing_records")
    invoice = relationship("ProcessedInvoice")

class Supplier(Base):
    """Supplier directory for analytics"""
    __tablename__ = "suppliers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    
    nit = Column(String(50), nullable=False)
    company_name = Column(String(255), nullable=False)
    address = Column(Text)
    city = Column(String(100))
    department = Column(String(100))
    phone = Column(String(50))
    email = Column(String(255))
    
    # Analytics
    total_invoices = Column(Integer, default=0)
    total_amount = Column(Numeric(15, 2), default=0)
    last_invoice_date = Column(Date)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_supplier_nit_tenant', 'nit', 'tenant_id'),
    )

class Product(Base):
    """Product catalog for inventory management"""
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    
    product_code = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    reference = Column(String(255))
    unit_measure = Column(String(50), default="UNIDAD")
    
    # Inventory
    current_stock = Column(Numeric(15, 4), default=0)
    min_stock = Column(Numeric(15, 4), default=0)
    max_stock = Column(Numeric(15, 4))
    
    # Analytics
    total_purchased = Column(Numeric(15, 4), default=0)
    total_amount = Column(Numeric(15, 2), default=0)
    last_purchase_date = Column(Date)
    last_purchase_price = Column(Numeric(15, 2))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_product_code_tenant', 'product_code', 'tenant_id'),
    )
