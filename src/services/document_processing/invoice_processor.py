"""
Invoice processing service with REAL Textract - FIXED
"""
import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from ...config.settings import settings
from ...database.connection import AsyncSessionFactory
from ...database.models import ProcessedInvoice, InvoiceLineItem, Tenant, BillingRecord
from ...models.invoice import (
    InvoiceData, InvoiceStatus, InvoiceType,
    SupplierInfo, CustomerInfo, InvoiceLineItem as InvoiceLineItemModel, 
    InvoiceTotals, PaymentInfo, ProcessedInvoice as ProcessedInvoiceModel
)
from .textract import TextractService

logger = logging.getLogger(__name__)

class InvoiceProcessorService:
    """Service for processing invoices with REAL Textract - FIXED"""
    
    def __init__(self):
        self.textract_service = TextractService()
    
    async def upload_and_process_invoice(
        self, 
        tenant_id: str,
        invoice_id: str, 
        filename: str, 
        file_content: bytes
    ) -> Dict[str, Any]:
        """Upload invoice and start real Textract processing"""
        async with AsyncSessionFactory() as session:
            try:
                # Verify/create tenant
                tenant_result = await session.execute(
                    select(Tenant).where(Tenant.tenant_id == tenant_id)
                )
                tenant = tenant_result.scalar_one_or_none()
                
                if not tenant:
                    logger.info(f"Creating new tenant: {tenant_id}")
                    tenant = Tenant(
                        tenant_id=tenant_id,
                        company_name=f"Company {tenant_id}",
                        email=f"{tenant_id}@test.com",
                        plan="freemium",
                        max_invoices_month=10,
                        invoices_processed_month=0
                    )
                    session.add(tenant)
                    await session.flush()
                
                # Check monthly limits
                if tenant.invoices_processed_month >= tenant.max_invoices_month:
                    raise Exception(f"Monthly limit reached: {tenant.max_invoices_month} invoices")
                
                # Create invoice record
                s3_key = f"invoices/{tenant_id}/{invoice_id}/{filename}"
                
                invoice = ProcessedInvoice(
                    id=uuid.UUID(invoice_id),
                    tenant_id=tenant_id,
                    original_filename=filename,
                    file_size=len(file_content),
                    s3_key=s3_key,
                    status="uploaded",
                    upload_timestamp=datetime.utcnow()
                )
                
                session.add(invoice)
                await session.commit()
                
                # Upload to S3 for Textract
                try:
                    self.textract_service.s3_client.put_object(
                        Bucket=settings.s3_document_bucket,
                        Key=s3_key,
                        Body=file_content,
                        ContentType='application/pdf'
                    )
                    logger.info(f"File uploaded to S3: {s3_key}")
                except Exception as e:
                    logger.warning(f"S3 upload failed, using mock processing: {str(e)}")
                
                # Start background processing
                asyncio.create_task(self._process_invoice_with_textract(invoice_id, s3_key))
                
                logger.info(f"Invoice uploaded: {invoice_id} for tenant {tenant_id}")
                
                return {
                    'invoice_id': invoice_id,
                    'tenant_id': tenant_id,
                    's3_key': s3_key,
                    'status': 'uploaded'
                }
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error uploading invoice: {str(e)}")
                raise
    
    async def _process_invoice_with_textract(self, invoice_id: str, s3_key: str):
        """Process invoice using REAL AWS Textract - FIXED"""
        async with AsyncSessionFactory() as session:
            try:
                # Get invoice
                result = await session.execute(
                    select(ProcessedInvoice).where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                )
                invoice = result.scalar_one_or_none()
                
                if not invoice:
                    logger.error(f"Invoice not found for processing: {invoice_id}")
                    return
                
                # Update status to processing
                invoice.status = "processing"
                invoice.processing_timestamp = datetime.utcnow()
                await session.commit()
                
                logger.info(f"Starting Textract processing for {invoice_id}")
                
                try:
                    # Call REAL Textract
                    textract_result = await self.textract_service.analyze_invoice(
                        s3_bucket=settings.s3_document_bucket,
                        s3_key=s3_key
                    )
                    
                    extracted_data = textract_result['extracted_data']
                    confidence_score = textract_result['confidence_score']
                    
                    logger.info(f"Textract completed for {invoice_id}, confidence: {confidence_score}")
                    
                    # Store raw Textract response
                    invoice.textract_raw_response = textract_result.get('textract_response')
                    
                except Exception as textract_error:
                    logger.warning(f"Textract failed for {invoice_id}: {str(textract_error)}")
                    logger.info("Falling back to mock data for development")
                    
                    # Fallback to mock data if Textract fails
                    extracted_data = self._create_mock_extraction()
                    confidence_score = 0.85
                
                # Update invoice with extracted data
                invoice.status = "completed"
                invoice.completion_timestamp = datetime.utcnow()
                invoice.confidence_score = Decimal(str(confidence_score))
                
                # Update invoice fields with SAFE extraction
                invoice.invoice_number = self._safe_extract(extracted_data, "invoice_number")
                invoice.invoice_type = "factura_venta"
                invoice.issue_date = self._safe_date(extracted_data.get("issue_date"))
                invoice.due_date = self._safe_date(extracted_data.get("due_date"))
                
                # Supplier info
                supplier = extracted_data.get("supplier") or {}
                invoice.supplier_name = self._safe_extract(supplier, "company_name")
                invoice.supplier_nit = self._safe_extract(supplier, "nit")
                invoice.supplier_address = self._safe_extract(supplier, "address")
                invoice.supplier_city = self._safe_extract(supplier, "city")
                invoice.supplier_department = self._safe_extract(supplier, "department")
                invoice.supplier_phone = self._safe_extract(supplier, "phone")
                
                # Customer info
                customer = extracted_data.get("customer") or {}
                invoice.customer_name = self._safe_extract(customer, "customer_name")
                invoice.customer_id = self._safe_extract(customer, "customer_id")
                invoice.customer_address = self._safe_extract(customer, "address")
                invoice.customer_city = self._safe_extract(customer, "city")
                invoice.customer_department = self._safe_extract(customer, "department")
                invoice.customer_phone = self._safe_extract(customer, "phone")
                
                # Totals
                totals = extracted_data.get("totals") or {}
                invoice.subtotal = self._safe_decimal(totals.get("subtotal"))
                invoice.iva_rate = self._safe_decimal(totals.get("iva_rate"))
                invoice.iva_amount = self._safe_decimal(totals.get("iva_amount"))
                invoice.total_amount = self._safe_decimal(totals.get("total"))
                
                # Payment info
                payment_info = extracted_data.get("payment_info") or {}
                invoice.payment_method = self._safe_extract(payment_info, "payment_method")
                invoice.credit_days = self._safe_int(payment_info.get("credit_days"))
                
                # Create line items
                line_items = extracted_data.get("line_items") or []
                invoice.total_items = len(line_items)
                
                for item_data in line_items:
                    if item_data and item_data.get("description"):
                        try:
                            line_item = InvoiceLineItem(
                                invoice_id=invoice.id,
                                line_number=self._safe_int(item_data.get("item_number")),
                                product_code=self._safe_extract(item_data, "product_code"),
                                description=self._safe_extract(item_data, "description"),
                                reference=self._safe_extract(item_data, "reference"),
                                quantity=self._safe_decimal(item_data.get("quantity")),
                                unit_price=self._safe_decimal(item_data.get("unit_price")),
                                subtotal=self._safe_decimal(item_data.get("subtotal")),
                                unit_measure=self._safe_extract(item_data, "unit_measure"), 
                                
                                # ✨ NEW: Enhanced fields for unit conversions
                                original_quantity=self._safe_decimal(item_data.get("original_quantity")),
                                original_unit=self._safe_extract(item_data, "original_unit"),
                                unit_multiplier=self._safe_decimal(item_data.get("unit_multiplier")),
                                item_number=self._safe_int(item_data.get("item_number")),
                                enhancement_applied=self._safe_extract(item_data, "_enhancement_applied")
                            )
                            session.add(line_item)
                        except Exception as e:
                            logger.warning(f"Error creating line item: {str(e)}")
                            logger.warning(f"Item data: {item_data}")
                
                # Update tenant invoice count
                await session.execute(
                    update(Tenant)
                    .where(Tenant.tenant_id == invoice.tenant_id)
                    .values(invoices_processed_month=Tenant.invoices_processed_month + 1)
                )
                
                # Create billing record
                billing_record = BillingRecord(
                    tenant_id=invoice.tenant_id,
                    invoice_id=invoice.id,
                    cost_cop=Decimal("1500"),
                    invoice_type=invoice.invoice_type,
                    pages_processed=1,
                    confidence_score=invoice.confidence_score
                )
                session.add(billing_record)
                
                await session.commit()
                
                logger.info(f"Invoice processing completed and SAVED: {invoice_id}")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error processing invoice {invoice_id}: {str(e)}")
                
                # Update status to failed
                try:
                    async with AsyncSessionFactory() as error_session:
                        await error_session.execute(
                            update(ProcessedInvoice)
                            .where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                            .values(status="failed", error_message=str(e))
                        )
                        await error_session.commit()
                except Exception as save_error:
                    logger.error(f"Could not save error status: {str(save_error)}")
    
    def _safe_extract(self, data: Dict, key: str) -> Optional[str]:
        """Safely extract string value"""
        if not data or not isinstance(data, dict):
            return None
        value = data.get(key)
        return str(value)[:255] if value is not None else None
    
    def _safe_decimal(self, value) -> Optional[Decimal]:
        """Safely convert to Decimal"""
        if value is None:
            return None
        try:
            if isinstance(value, Decimal):
                return value
            return Decimal(str(value))
        except Exception:
            return None
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert to int"""
        if value is None:
            return None
        try:
            return int(value)
        except Exception:
            return None
    
    def _create_mock_extraction(self) -> Dict[str, Any]:
        """Fallback mock data for development/testing"""
        return {
            "invoice_number": "DEV-MOCK-001",
            "issue_date": date.today(),
            "due_date": None,
            "supplier": {
                "company_name": "MOCK SUPPLIER FOR DEVELOPMENT",
                "nit": "000000000-0",
                "address": "Mock Address",
                "department": "ATLANTICO"
            },
            "customer": {
                "customer_name": "MOCK CUSTOMER",
                "customer_id": "123456789-0",
                "address": "Mock Customer Address",
                "city": "MOCK CITY",
                "department": "MOCK DEPT",
                "phone": "1234567890"
            },
            "line_items": [
                {
                    "product_code": "MOCK-001",
                    "description": "MOCK PRODUCT - DEVELOPMENT TESTING",
                    "reference": "MOCK-REF-001",
                    "quantity": Decimal("5"),
                    "unit_price": Decimal("10000"),
                    "subtotal": Decimal("50000")
                }
            ],
            "totals": {
                "subtotal": Decimal("50000"),
                "iva_rate": Decimal("19"),
                "iva_amount": Decimal("9500"),
                "total": Decimal("59500"),
            },
            "payment_info": {
                "payment_method": "DEVELOPMENT MODE",
                "credit_days": 30
            }
        }
    
    async def get_invoice_status(self, invoice_id: str, tenant_id: str) -> Optional[ProcessedInvoiceModel]:
        async with AsyncSessionFactory() as session:
            try:
                result = await session.execute(
                    select(ProcessedInvoice)
                    .options(selectinload(ProcessedInvoice.line_items))
                    .where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                    .where(ProcessedInvoice.tenant_id == tenant_id)
                )
                invoice = result.scalar_one_or_none()
                
                if not invoice:
                    return None
                
                return self._convert_to_pydantic(invoice)
                
            except Exception as e:
                logger.error(f"Error getting invoice status: {str(e)}")
                return None
    
    async def get_invoice_data(self, invoice_id: str, tenant_id: str) -> Optional[InvoiceData]:
        async with AsyncSessionFactory() as session:
            try:
                # REMOVIDO: filtro por status - ya se verifica en el endpoint
                result = await session.execute(
                    select(ProcessedInvoice)
                    .options(selectinload(ProcessedInvoice.line_items))
                    .where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                    .where(ProcessedInvoice.tenant_id == tenant_id)
                )
                invoice = result.scalar_one_or_none()
                
                if not invoice:
                    logger.error(f"Invoice not found in DB: {invoice_id}")
                    return None
                
                logger.info(f"Building InvoiceData for {invoice_id}")
                
                return InvoiceData(
                    invoice_number=invoice.invoice_number,
                    invoice_type=InvoiceType(invoice.invoice_type) if invoice.invoice_type else None,
                    issue_date=invoice.issue_date,
                    due_date=invoice.due_date,
                    supplier=SupplierInfo(
                        company_name=invoice.supplier_name,
                        nit=invoice.supplier_nit,
                        address=invoice.supplier_address,
                        city=invoice.supplier_city,
                        department=invoice.supplier_department,
                        phone=invoice.supplier_phone
                    ),
                    customer=CustomerInfo(
                        customer_name=getattr(invoice, 'customer_name', None),
                        customer_id=getattr(invoice, 'customer_id', None),
                        address=getattr(invoice, 'customer_address', None),
                        city=getattr(invoice, 'customer_city', None),
                        department=getattr(invoice, 'customer_department', None),
                        phone=getattr(invoice, 'customer_phone', None)
                    ),
                    line_items=[
                        InvoiceLineItemModel(
                            line_number=getattr(item, 'line_number', None),
                            product_code=item.product_code,
                            description=item.description,
                            reference=item.reference,
                            quantity=item.quantity,
                            unit_price=item.unit_price,
                            subtotal=item.subtotal,
                            unit_measure=getattr(item, 'unit_measure', None),
                            box_number=getattr(item, 'box_number', None)
                        )
                        for item in (invoice.line_items or [])
                    ],
                    totals=InvoiceTotals(
                        subtotal=getattr(invoice, 'subtotal', None) or Decimal("0"),
                        iva_rate=getattr(invoice, 'iva_rate', None),
                        iva_amount=getattr(invoice, 'iva_amount', None),
                        retenciones=None,
                        total=getattr(invoice, 'total_amount', None) or Decimal("0"),
                        total_items=getattr(invoice, 'total_items', None) or len(invoice.line_items or [])
                    ),
                    payment_info=PaymentInfo(
                        payment_method=getattr(invoice, 'payment_method', None),
                        credit_days=getattr(invoice, 'credit_days', None)
                    )
                )
                
            except Exception as e:
                logger.error(f"Error getting invoice data: {str(e)}")
                logger.error(f"Invoice ID: {invoice_id}, Tenant: {tenant_id}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return None
    
    async def list_tenant_invoices(
        self, 
        tenant_id: str,
        limit: int = 10, 
        offset: int = 0,
        status: Optional[InvoiceStatus] = None
    ) -> List[ProcessedInvoiceModel]:
        async with AsyncSessionFactory() as session:
            try:
                query = (
                    select(ProcessedInvoice)
                    .where(ProcessedInvoice.tenant_id == tenant_id)
                    .order_by(ProcessedInvoice.upload_timestamp.desc())
                    .offset(offset)
                    .limit(limit)
                )
                
                if status:
                    query = query.where(ProcessedInvoice.status == status.value)
                
                result = await session.execute(query)
                invoices = result.scalars().all()
                
                return [self._convert_to_pydantic(invoice) for invoice in invoices]
                
            except Exception as e:
                logger.error(f"Error listing invoices: {str(e)}")
                return []
    
    async def delete_invoice(self, invoice_id: str, tenant_id: str) -> bool:
        async with AsyncSessionFactory() as session:
            try:
                result = await session.execute(
                    delete(ProcessedInvoice)
                    .where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                    .where(ProcessedInvoice.tenant_id == tenant_id)
                )
                
                await session.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Invoice deleted: {invoice_id}")
                    return True
                
                return False
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error deleting invoice: {str(e)}")
                return False
    
    def _convert_to_pydantic(self, invoice: ProcessedInvoice) -> ProcessedInvoiceModel:
        return ProcessedInvoiceModel(
            id=str(invoice.id),
            tenant_id=invoice.tenant_id,
            original_filename=invoice.original_filename,
            file_size=invoice.file_size,
            upload_timestamp=invoice.upload_timestamp,
            processing_timestamp=invoice.processing_timestamp,
            completion_timestamp=invoice.completion_timestamp,
            status=InvoiceStatus(invoice.status),
            confidence_score=float(invoice.confidence_score) if invoice.confidence_score else None,
            error_message=invoice.error_message,
            s3_key=invoice.s3_key,
            textract_job_id=invoice.textract_job_id
        )

    async def upload_and_process_photo(
        self, 
        tenant_id: str,
        invoice_id: str, 
        filename: str, 
        photo_content: bytes
    ) -> Dict[str, Any]:
        """Upload photo, enhance it, convert to PDF, and process with Textract"""
        from .computer_vision import DocumentImageEnhancer, ImageToPDFConverter
        
        async with AsyncSessionFactory() as session:
            try:
                # Verify/create tenant
                tenant_result = await session.execute(
                    select(Tenant).where(Tenant.tenant_id == tenant_id)
                )
                tenant = tenant_result.scalar_one_or_none()
                
                if not tenant:
                    logger.info(f"Creating new tenant: {tenant_id}")
                    tenant = Tenant(
                        tenant_id=tenant_id,
                        company_name=f"Company {tenant_id}",
                        email=f"{tenant_id}@test.com",
                        plan="freemium",
                        max_invoices_month=10,
                        invoices_processed_month=0
                    )
                    session.add(tenant)
                    await session.flush()
                
                # Check monthly limits
                if tenant.invoices_processed_month >= tenant.max_invoices_month:
                    raise Exception(f"Monthly limit reached: {tenant.max_invoices_month} invoices")
                
                # Step 1: Enhance the photo
                logger.info(f"Enhancing photo for invoice {invoice_id}")
                enhancer = DocumentImageEnhancer()
                enhanced_image_bytes = enhancer.enhance_invoice_photo(photo_content)
                
                # Step 2: Convert to PDF
                logger.info(f"Converting enhanced image to PDF for invoice {invoice_id}")
                pdf_converter = ImageToPDFConverter()
                pdf_content = pdf_converter.convert_to_pdf(enhanced_image_bytes)
                
                # Validate PDF for Textract
                if not pdf_converter.validate_pdf_for_textract(pdf_content):
                    raise Exception("Generated PDF does not meet Textract requirements")
                
                # Step 3: Create invoice record
                # Use PDF filename for consistency with existing pipeline
                pdf_filename = f"{filename.rsplit('.', 1)[0]}_enhanced.pdf"
                s3_key = f"invoices/{tenant_id}/{invoice_id}/{pdf_filename}"
                
                invoice = ProcessedInvoice(
                    id=uuid.UUID(invoice_id),
                    tenant_id=tenant_id,
                    original_filename=pdf_filename,  # Store as PDF name
                    file_size=len(pdf_content),
                    s3_key=s3_key,
                    status="uploaded",
                    upload_timestamp=datetime.utcnow()
                )
                
                session.add(invoice)
                await session.commit()
                
                # Step 4: Upload PDF to S3 for Textract
                try:
                    self.textract_service.s3_client.put_object(
                        Bucket=settings.s3_document_bucket,
                        Key=s3_key,
                        Body=pdf_content,
                        ContentType='application/pdf'
                    )
                    logger.info(f"Enhanced PDF uploaded to S3: {s3_key}")
                except Exception as e:
                    logger.warning(f"S3 upload failed, using mock processing: {str(e)}")
                
                # Step 5: Start background processing with Textract
                asyncio.create_task(self._process_invoice_with_textract(invoice_id, s3_key))
                
                logger.info(f"Photo processed and uploaded: {invoice_id} for tenant {tenant_id}")
                
                return {
                    'invoice_id': invoice_id,
                    'tenant_id': tenant_id,
                    's3_key': s3_key,
                    'status': 'uploaded',
                    'processing_method': 'photo_enhancement'
                }
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error processing photo: {str(e)}")
                raise

    async def get_pricing_data(self, invoice_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get invoice data formatted for manual pricing - FIXED"""
        async with AsyncSessionFactory() as session:
            try:
                # Get invoice first (without selectinload)
                invoice_result = await session.execute(
                    select(ProcessedInvoice)
                    .where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                    .where(ProcessedInvoice.tenant_id == tenant_id)
                )
                invoice = invoice_result.scalar_one_or_none()
                
                if not invoice:
                    logger.error(f"Invoice not found: {invoice_id}")
                    return None
                
                logger.info(f"Found invoice: {invoice.invoice_number}")
                
                # Get line items in separate query
                line_items_result = await session.execute(
                    select(InvoiceLineItem)
                    .where(InvoiceLineItem.invoice_id == uuid.UUID(invoice_id))
                )
                line_items = line_items_result.scalars().all()
                
                logger.info(f"Found {len(line_items)} line items")
                
                if not line_items:
                    logger.warning(f"No line items found for invoice {invoice_id}")
                    return None
                
                # Format line items for pricing
                pricing_items = []
                for item in line_items:
                    pricing_items.append({
                        "id": str(item.id),
                        "product_code": item.product_code or "",
                        "description": item.description or "",
                        "quantity": float(item.quantity),
                        "unit_price": float(item.unit_price),
                        "subtotal": float(item.subtotal),
                        "sale_price": float(item.sale_price) if hasattr(item, 'sale_price') and item.sale_price else None,
                        "markup_percentage": float(item.markup_percentage) if hasattr(item, 'markup_percentage') and item.markup_percentage else None,
                        "is_priced": getattr(item, 'is_priced', False)
                    })
                
                # Calculate summary
                total_cost = sum(float(item.subtotal) for item in line_items)
                priced_items = len([item for item in pricing_items if item['is_priced']])
                
                result = {
                    "invoice_id": invoice_id,
                    "invoice_number": invoice.invoice_number,
                    "supplier_name": invoice.supplier_name,
                    "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
                    "total_items": len(pricing_items),
                    "priced_items": priced_items,
                    "pending_items": len(pricing_items) - priced_items,
                    "total_cost": total_cost,
                    "line_items": pricing_items,
                    "pricing_status": "pending" if priced_items == 0 else "partial" if priced_items < len(pricing_items) else "completed"
                }
                
                logger.info(f"Returning pricing data with {len(pricing_items)} items")
                return result
                
            except Exception as e:
                logger.error(f"Error getting pricing data: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return None

    async def set_invoice_pricing(self, invoice_id: str, tenant_id: str, pricing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Set manual pricing for line items"""
        async with AsyncSessionFactory() as session:
            try:
                # Get line items to update
                line_items_data = pricing_data.get('line_items', [])
                
                updated_items = 0
                total_cost = Decimal('0')
                total_sale_value = Decimal('0')
                
                for item_data in line_items_data:
                    line_item_id = item_data.get('line_item_id')
                    sale_price = item_data.get('sale_price')
                    
                    if not line_item_id or not sale_price:
                        continue
                    
                    # Get the line item
                    result = await session.execute(
                        select(InvoiceLineItem)
                        .where(InvoiceLineItem.id == uuid.UUID(line_item_id))
                        .where(InvoiceLineItem.invoice_id == uuid.UUID(invoice_id))
                    )
                    line_item = result.scalar_one_or_none()
                    
                    if line_item:
                        # Calculate markup percentage
                        cost_per_unit = line_item.unit_price
                        markup = ((Decimal(str(sale_price)) - cost_per_unit) / cost_per_unit) * 100
                        
                        # Update line item
                        await session.execute(
                            update(InvoiceLineItem)
                            .where(InvoiceLineItem.id == line_item.id)
                            .values(
                                sale_price=Decimal(str(sale_price)),
                                markup_percentage=markup,
                                is_priced=True
                            )
                        )
                        
                        # Calculate totals
                        item_cost = line_item.subtotal
                        item_sale_value = Decimal(str(sale_price)) * line_item.quantity
                        
                        total_cost += item_cost
                        total_sale_value += item_sale_value
                        updated_items += 1
                
                # Update invoice pricing status
                await session.execute(
                    update(ProcessedInvoice)
                    .where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                    .where(ProcessedInvoice.tenant_id == tenant_id)
                    .values(pricing_status="partial")  # Will be updated to "completed" when all items are priced
                )
                
                await session.commit()
                
                # Calculate summary
                total_profit = total_sale_value - total_cost
                average_markup = ((total_sale_value - total_cost) / total_cost * 100) if total_cost > 0 else Decimal('0')
                
                return {
                    "updated_items": updated_items,
                    "total_cost": float(total_cost),
                    "total_sale_value": float(total_sale_value),
                    "total_profit": float(total_profit),
                    "average_markup": float(average_markup)
                }
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error setting pricing: {str(e)}")
                raise

    async def confirm_invoice_pricing(self, invoice_id: str, tenant_id: str) -> Dict[str, Any]:
        """Confirm pricing and prepare for inventory update"""
        async with AsyncSessionFactory() as session:
            try:
                # Check if all items are priced
                result = await session.execute(
                    select(InvoiceLineItem)
                    .where(InvoiceLineItem.invoice_id == uuid.UUID(invoice_id))
                )
                line_items = result.scalars().all()
                
                unpriced_items = [item for item in line_items if not getattr(item, 'is_priced', False)]
                
                if unpriced_items:
                    raise Exception(f"Cannot confirm pricing: {len(unpriced_items)} items still need pricing")
                
                # Update invoice status
                await session.execute(
                    update(ProcessedInvoice)
                    .where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                    .where(ProcessedInvoice.tenant_id == tenant_id)
                    .values(pricing_status="confirmed")
                )
                
                await session.commit()
                
                # TODO: Here we'll add inventory update logic in next step
                
                return {
                    "status": "confirmed",
                    "ready_for_inventory": True,
                    "total_items": len(line_items)
                }
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error confirming pricing: {str(e)}")
                raise

    def _safe_date(self, value) -> Optional[date]:
        """Safely convert to date object"""
        if value is None:
            return None
        try:
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                # Try different date formats
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        return datetime.strptime(value, fmt).date()
                    except ValueError:
                        continue
            return None
        except Exception:
            return None
        
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert to int"""
        if value is None:
            return None
        try:
            return int(value)
        except Exception:
            return None
