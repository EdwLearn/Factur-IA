"""
Invoice processing service with REAL Textract - FIXED
"""
import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException

from ...core.config import settings
from ...database.connection import AsyncSessionFactory
from ...database.models import ProcessedInvoice, InvoiceLineItem, Tenant, BillingRecord, Supplier
from ...models.invoice import (
    InvoiceData, InvoiceStatus, InvoiceType,
    SupplierInfo, CustomerInfo, InvoiceLineItem as InvoiceLineItemModel, 
    InvoiceTotals, PaymentInfo, ProcessedInvoice as ProcessedInvoiceModel
)
from .textract import TextractService
from .digital_pdf_extractor import DigitalPDFExtractor
from .dian_xml_extractor import DianXMLExtractor

logger = logging.getLogger(__name__)

class InvoiceProcessorService:
    """Service for processing invoices with REAL Textract - FIXED"""
    
    def __init__(self):
        self.textract_service = TextractService()
        self.pdf_extractor = DigitalPDFExtractor()
        self.xml_extractor = DianXMLExtractor()
    
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
                # Verify tenant exists — never auto-create
                tenant_result = await session.execute(
                    select(Tenant).where(Tenant.tenant_id == tenant_id)
                )
                tenant = tenant_result.scalar_one_or_none()

                if not tenant:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Tenant '{tenant_id}' not found. Register first via /auth/register."
                    )
                
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
                
                # Detect file type once here while we still have file_content in memory.
                # Priority: XML > digital PDF > scanned/photo (Textract)
                is_xml     = DianXMLExtractor.is_dian_xml(file_content)
                is_digital = (not is_xml) and DigitalPDFExtractor.is_digital(file_content)

                # Upload to S3 with correct ContentType
                content_type = (
                    'application/xml' if is_xml
                    else 'application/pdf' if filename.lower().endswith('.pdf')
                    else 'image/jpeg'
                )

                # Rotar imagen antes de subir a S3 (solo path Textract — imágenes/fotos)
                if not is_xml and not is_digital:
                    file_content = self.textract_service._auto_rotate_image(file_content)

                self.textract_service.s3_client.put_object(
                    Bucket=settings.s3_document_bucket,
                    Key=s3_key,
                    Body=file_content,
                    ContentType=content_type
                )
                logger.info(f"File uploaded to S3: {s3_key}")

                if is_xml:
                    source = "dian_xml"
                elif is_digital:
                    source = "digital_pdf"
                else:
                    source = "textract"
                logger.info(f"Invoice {invoice_id} detected as: {source}")

                # Start background processing
                asyncio.create_task(
                    self._process_invoice_with_textract(invoice_id, s3_key, file_content, is_digital, is_xml)
                )
                
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
    
    async def _process_invoice_with_textract(
        self,
        invoice_id: str,
        s3_key: str,
        file_content: bytes = b"",
        is_digital: bool = False,
        is_xml: bool = False,
    ):
        """Process invoice — XML > digital PDF (pdfplumber) > scanned/photo (Textract)."""
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

                try:
                    if is_xml and file_content:
                        # --- Path A: DIAN XML → lxml parser (free, exact, no OCR) ---
                        logger.info(f"Extracting DIAN XML for {invoice_id}")
                        extracted_data = self.xml_extractor.extract_invoice_data(file_content)
                        confidence_score = 1.0  # Structured data — perfect accuracy
                        invoice.textract_raw_response = {"source": "dian_xml", "method": "ubl2.1"}
                        invoice.invoice_type = "factura_electronica_dian"
                        logger.info(f"DIAN XML extraction completed for {invoice_id}")

                    elif is_digital and file_content:
                        # --- Path B: digital PDF → pdfplumber (free, fast) ---
                        logger.info(f"Extracting digital PDF for {invoice_id}")
                        extracted_data = self.pdf_extractor.extract_invoice_data(file_content)
                        confidence_score = 0.97
                        invoice.textract_raw_response = {"source": "digital_pdf", "method": "pdfplumber"}
                        logger.info(f"Digital PDF extraction completed for {invoice_id}")

                    else:
                        # --- Path C: scanned / photo → Textract (OCR) ---
                        logger.info(f"Starting Textract OCR for {invoice_id}")
                        textract_result = await self.textract_service.analyze_invoice(
                            s3_bucket=settings.s3_document_bucket,
                            s3_key=s3_key,
                        )
                        extracted_data = textract_result["extracted_data"]
                        confidence_score = textract_result["confidence_score"]
                        invoice.textract_raw_response = textract_result.get("textract_response")
                        logger.info(f"Textract completed for {invoice_id}, confidence: {confidence_score}")

                except Exception as extraction_error:
                    logger.error(f"Extraction failed for {invoice_id}: {extraction_error}")
                    raise
                
                # Clasificar tipo de documento antes de persistir
                from .document_classifier import DocumentClassifier
                full_text = extracted_data.get("full_text", "")
                invoice.document_type = DocumentClassifier.classify_document(full_text)
                logger.info(f"Documento clasificado como: {invoice.document_type} ({invoice_id})")

                # Update invoice with extracted data
                invoice.status = "completed"
                invoice.completion_timestamp = datetime.utcnow()
                invoice.confidence_score = Decimal(str(confidence_score))
                
                # Update invoice fields with SAFE extraction
                invoice.invoice_number = self._safe_extract(extracted_data, "invoice_number")
                # Only overwrite invoice_type if not already set by the XML path
                if not invoice.invoice_type:
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

                # Upsert proveedor en tabla suppliers (clave: NIT + tenant)
                supplier_record = await self._upsert_supplier(
                    session=session,
                    tenant_id=invoice.tenant_id,
                    nit=invoice.supplier_nit,
                    name=invoice.supplier_name,
                    extra_data=supplier,
                )
                if supplier_record:
                    invoice.supplier_nit = supplier_record.nit
                    invoice.supplier_name = supplier_record.company_name
                
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
                # Retenciones DIAN
                invoice.rete_renta = self._safe_decimal(totals.get("rete_renta"))
                invoice.rete_iva = self._safe_decimal(totals.get("rete_iva"))
                invoice.rete_ica = self._safe_decimal(totals.get("rete_ica"))
                invoice.total_retenciones = self._safe_decimal(totals.get("total_retenciones"))
                invoice.total_amount = self._safe_decimal(totals.get("total"))
                # IVA desglosado por tarifa (solo XML lo provee, se guarda en JSONB)
                iva_breakdown = totals.get("iva_breakdown")
                if iva_breakdown:
                    existing = invoice.textract_raw_response or {}
                    invoice.textract_raw_response = {
                        **existing,
                        "iva_breakdown": [
                            {k: float(v) if isinstance(v, Decimal) else v for k, v in entry.items()}
                            for entry in iva_breakdown
                        ],
                    }
                
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
                            quantity   = self._safe_decimal(item_data.get("quantity"))
                            unit_price = self._safe_decimal(item_data.get("unit_price"))
                            subtotal   = self._safe_decimal(item_data.get("subtotal"))

                            # Fallback: derivar quantity desde subtotal/unit_price
                            if quantity is None:
                                if unit_price and subtotal and unit_price > 0:
                                    quantity = (subtotal / unit_price).quantize(Decimal("0.0001"))
                                else:
                                    quantity = Decimal("1")

                            line_item = InvoiceLineItem(
                                invoice_id=invoice.id,
                                line_number=self._safe_int(item_data.get("item_number")),
                                product_code=self._safe_extract(item_data, "product_code"),
                                description=self._safe_extract(item_data, "description"),
                                reference=self._safe_extract(item_data, "reference"),
                                quantity=quantity,
                                unit_price=unit_price,
                                subtotal=subtotal,
                                iva_rate=self._safe_decimal(item_data.get("iva_rate")),
                                unit_measure=self._safe_extract(item_data, "unit_measure"),
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
    
    async def _upsert_supplier(
        self,
        session: AsyncSession,
        tenant_id: str,
        nit: str,
        name: str,
        extra_data: dict = None
    ) -> Optional[object]:
        """Busca el proveedor por NIT + tenant_id. Si existe actualiza nombre si cambió. Si no existe crea nuevo."""
        if not nit:
            return None

        result = await session.execute(
            select(Supplier).where(
                Supplier.nit == nit,
                Supplier.tenant_id == tenant_id
            )
        )
        supplier = result.scalar_one_or_none()

        if supplier:
            if name and supplier.company_name != name:
                supplier.company_name = name
                session.add(supplier)
            return supplier

        supplier = Supplier(
            tenant_id=tenant_id,
            nit=nit,
            company_name=name or "",
            city=extra_data.get("city") if extra_data else None,
            phone=extra_data.get("phone") if extra_data else None,
            address=extra_data.get("address") if extra_data else None,
            department=extra_data.get("department") if extra_data else None,
        )
        session.add(supplier)
        await session.flush()
        logger.info(f"Nuevo proveedor creado: {nit} - {name}")
        return supplier

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

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_analytics_summary(self, tenant_id: str) -> Dict[str, Any]:
        """Return aggregated analytics for a tenant's invoices."""
        invoices = await self.list_tenant_invoices(tenant_id, limit=1000)

        total = len(invoices)
        completed = sum(1 for inv in invoices if inv.status == InvoiceStatus.COMPLETED)
        failed = sum(1 for inv in invoices if inv.status == InvoiceStatus.FAILED)
        total_amount = sum(
            inv.invoice_data.totals.total
            for inv in invoices
            if inv.invoice_data and inv.invoice_data.totals
        )

        return {
            "tenant_id": tenant_id,
            "total_invoices": total,
            "completed_invoices": completed,
            "failed_invoices": failed,
            "success_rate": completed / total if total > 0 else 0,
            "total_amount_processed": float(total_amount),
            "currency": "COP",
        }

    # ------------------------------------------------------------------
    # Pricing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def build_pricing_summary(updated_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a totals summary from the list returned by set_invoice_pricing."""
        total_cost = sum(
            item.get("cost_price", 0) * item.get("quantity", 0)
            for item in updated_items
        )
        total_sale_value = sum(item.get("total_sale_value", 0) for item in updated_items)
        total_profit = sum(item.get("total_profit", 0) for item in updated_items)
        avg_markup = (total_profit / total_cost * 100) if total_cost > 0 else 0

        return {
            "total_items": len(updated_items),
            "total_cost": round(total_cost, 2),
            "total_sale_value": round(total_sale_value, 2),
            "total_profit": round(total_profit, 2),
            "average_markup": round(avg_markup, 2),
        }
    
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
                    document_type=getattr(invoice, 'document_type', 'factura'),
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
                            iva_rate=getattr(item, 'iva_rate', None),
                            unit_measure=getattr(item, 'unit_measure', None),
                            box_number=getattr(item, 'box_number', None)
                        )
                        for item in (invoice.line_items or [])
                    ],
                    totals=InvoiceTotals(
                        subtotal=getattr(invoice, 'subtotal', None) or Decimal("0"),
                        iva_rate=getattr(invoice, 'iva_rate', None),
                        iva_amount=getattr(invoice, 'iva_amount', None),
                        rete_renta=getattr(invoice, 'rete_renta', None),
                        rete_iva=getattr(invoice, 'rete_iva', None),
                        rete_ica=getattr(invoice, 'rete_ica', None),
                        total_retenciones=getattr(invoice, 'total_retenciones', None),
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
        status: Optional[InvoiceStatus] = None,
        since: Optional[datetime] = None,
    ) -> List[ProcessedInvoiceModel]:
        async with AsyncSessionFactory() as session:
            try:
                query = (
                    select(ProcessedInvoice)
                    .options(selectinload(ProcessedInvoice.line_items))
                    .where(ProcessedInvoice.tenant_id == tenant_id)
                    .order_by(ProcessedInvoice.upload_timestamp.desc())
                    .offset(offset)
                    .limit(limit)
                )

                if status:
                    query = query.where(ProcessedInvoice.status == status.value)

                if since:
                    query = query.where(ProcessedInvoice.upload_timestamp >= since)
                
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
    
    def _resolve_total(self, invoice: ProcessedInvoice) -> Optional[float]:
        """Return total_amount from DB when valid; otherwise compute from line items."""
        stored = float(invoice.total_amount) if invoice.total_amount is not None else None
        if stored and stored > 0:
            return stored
        # Fallback: sum subtotals from line items (mirrors what the detail page does)
        if invoice.line_items:
            computed = sum(float(item.subtotal or 0) for item in invoice.line_items)
            if computed > 0:
                return computed
        return stored  # return 0.0 or None as-is if no line items either

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
            textract_job_id=invoice.textract_job_id,
            invoice_number=invoice.invoice_number,
            supplier_name=invoice.supplier_name,
            supplier_nit=invoice.supplier_nit,
            total_amount=self._resolve_total(invoice),
            issue_date=invoice.issue_date,
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
                # Verify tenant exists — never auto-create
                tenant_result = await session.execute(
                    select(Tenant).where(Tenant.tenant_id == tenant_id)
                )
                tenant = tenant_result.scalar_one_or_none()

                if not tenant:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Tenant '{tenant_id}' not found. Register first via /auth/register."
                    )
                
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
                    original_filename=filename,  # Keep original image filename
                    file_size=len(pdf_content),
                    s3_key=s3_key,
                    status="uploaded",
                    upload_timestamp=datetime.utcnow()
                )
                
                session.add(invoice)
                await session.commit()
                
                # Step 4: Upload PDF to S3 for Textract
                self.textract_service.s3_client.put_object(
                    Bucket=settings.s3_document_bucket,
                    Key=s3_key,
                    Body=pdf_content,
                    ContentType='application/pdf'
                )
                logger.info(f"Enhanced PDF uploaded to S3: {s3_key}")
                
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
                        "id": str(uuid.uuid4()),
                        "line_item_id": str(item.id),
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

    async def set_invoice_pricing(self, invoice_id: str, tenant_id: str, pricing_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Set manual pricing for line items - IMPLEMENTACIÓN REAL"""
        async with AsyncSessionFactory() as session:
            try:
                line_items_data = pricing_data.get('line_items', [])

                if not line_items_data:
                    raise Exception("No line items provided for pricing")
            
                updated_items = []
            
                for item_data in line_items_data:
                    line_item_id = item_data.get('line_item_id')
                    sale_price = item_data.get('sale_price')
                
                    if not line_item_id or not sale_price:
                        logger.warning(f"Skipping incomplete item: {item_data}")
                        continue
                
                    try:
                        # 1. Obtener el line item de la base de datos
                        result = await session.execute(
                            select(InvoiceLineItem)
                            .where(InvoiceLineItem.id == uuid.UUID(line_item_id))
                        )
                        line_item = result.scalar_one_or_none()
                    
                        if not line_item:
                            logger.warning(f"Line item not found: {line_item_id}")
                            continue

                        # 2. Calcular márgenes automáticamente
                        cost_per_unit = line_item.unit_price
                        sale_price_decimal = Decimal(str(sale_price))
                    
                        if cost_per_unit > 0:
                            markup_percentage = ((sale_price_decimal - cost_per_unit) / cost_per_unit) * 100
                            profit_margin = ((sale_price_decimal - cost_per_unit) / sale_price_decimal) * 100
                        else:
                            markup_percentage = Decimal('0')
                            profit_margin = Decimal('0')
                    
                        # 3. Actualizar en la base de datos - REAL DATA
                        await session.execute(
                            update(InvoiceLineItem)
                            .where(InvoiceLineItem.id == line_item.id)
                            .values(
                                sale_price=sale_price_decimal,
                                markup_percentage=markup_percentage,
                                is_priced=True
                            )
                        )
                    
                        # 4. Preparar respuesta
                        updated_items.append({
                            "line_item_id": str(line_item_id),
                            "product_code": line_item.product_code,
                            "description": line_item.description,
                            "quantity": float(line_item.quantity),
                            "cost_price": float(cost_per_unit),
                            "sale_price": float(sale_price_decimal),
                            "markup_percentage": float(markup_percentage),
                            "profit_margin": float(profit_margin),
                            "is_priced": True,
                            "total_sale_value": float(sale_price_decimal * line_item.quantity),
                            "total_profit": float((sale_price_decimal - cost_per_unit) * line_item.quantity)
                        })
                    
                        logger.info(f"✅ Updated pricing for {line_item.product_code}: ${cost_per_unit} → ${sale_price_decimal} ({markup_percentage:.1f}% markup)")
                    
                    except Exception as item_error:
                        logger.error(f"Error updating line item {line_item_id}: {str(item_error)}")
                        continue
            
                # 5. Commit todas las actualizaciones
                await session.commit()
            
                # 6. Actualizar el status de la factura si todos los items están pricing
                if updated_items:
                    await self._update_invoice_pricing_status(invoice_id, session)
            
                logger.info(f"💾 PRICING SAVED: Updated {len(updated_items)} items for invoice {invoice_id}")
                return updated_items
            
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Error setting invoice pricing: {str(e)}")
                raise
    async def _update_invoice_pricing_status(self, invoice_id: str, session: AsyncSession):
        """Update invoice pricing status based on priced items"""
        try:
            # Contar items totales vs items con precio
            total_items_result = await session.execute(
                select(func.count(InvoiceLineItem.id))
                .where(InvoiceLineItem.invoice_id == uuid.UUID(invoice_id))
            )
            total_items = total_items_result.scalar() or 0
        
            priced_items_result = await session.execute(
                select(func.count(InvoiceLineItem.id))
                .where(InvoiceLineItem.invoice_id == uuid.UUID(invoice_id))
                .where(InvoiceLineItem.is_priced == True)
            )
            priced_items = priced_items_result.scalar() or 0
        
            # Determinar status
            if priced_items == 0:
                status = "pending"
            elif priced_items < total_items:
                status = "partial"
            else:
                status = "completed"
        
            # Actualizar invoice
            await session.execute(
                update(ProcessedInvoice)
                .where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                .values(pricing_status=status)
            )
        
            logger.info(f"📊 Updated pricing status to '{status}' ({priced_items}/{total_items} items priced)")
        
        except Exception as e:
            logger.warning(f"Could not update pricing status: {str(e)}")
            

    async def confirm_invoice_pricing(self, invoice_id: str, tenant_id: str) -> Dict[str, Any]:
        """Confirm pricing: update inventory + POST /bills to Alegra (if configured)."""
        async with AsyncSessionFactory() as session:
            try:
                from ...database.models import Product, Supplier, Tenant
                from sqlalchemy import select, update
                from datetime import datetime

                # ── 1. Get priced line items ──────────────────────────────
                result = await session.execute(
                    select(InvoiceLineItem)
                    .where(InvoiceLineItem.invoice_id == uuid.UUID(invoice_id))
                    .where(InvoiceLineItem.is_priced == True)
                )
                priced_items = result.scalars().all()

                if not priced_items:
                    raise Exception("No hay items con precio para confirmar")

                # ── 2. Get invoice header (for Alegra bill payload) ───────
                inv_result = await session.execute(
                    select(ProcessedInvoice)
                    .where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                )
                invoice_record = inv_result.scalar_one_or_none()

                # ── 3. Update inventory ───────────────────────────────────
                inventory_updates = []
                for item in priced_items:
                    if not item.product_code:
                        logger.warning(
                            f"Skipping inventory update for item without product_code: "
                            f"description='{item.description}', invoice={invoice_id}"
                        )
                        inventory_updates.append({
                            "action": "skipped_no_code",
                            "description": item.description,
                            "reason": "product_code is null",
                        })
                        continue

                    product_result = await session.execute(
                        select(Product)
                        .where(Product.product_code == item.product_code)
                        .where(Product.tenant_id == tenant_id)
                    )
                    existing_product = product_result.scalar_one_or_none()

                    if existing_product:
                        new_stock = (existing_product.current_stock or 0) + item.quantity
                        update_values = {
                            "current_stock": new_stock,
                            "last_purchase_price": item.unit_price,
                            "last_purchase_date": datetime.utcnow().date(),
                            "updated_at": datetime.utcnow(),
                        }
                        if item.sale_price:
                            update_values["sale_price"] = item.sale_price
                        await session.execute(
                            update(Product)
                            .where(Product.id == existing_product.id)
                            .values(**update_values)
                        )
                        inventory_updates.append({
                            "action": "updated_existing",
                            "product_code": item.product_code,
                            "quantity_added": float(item.quantity),
                            "new_stock": float(new_stock)
                        })
                    else:
                        new_product = Product(
                            tenant_id=tenant_id,
                            product_code=item.product_code,
                            description=item.description,
                            current_stock=item.quantity,
                            last_purchase_price=item.unit_price,
                            sale_price=item.sale_price if item.sale_price else None,
                            last_purchase_date=datetime.utcnow().date()
                        )
                        session.add(new_product)
                        inventory_updates.append({
                            "action": "created_new",
                            "product_code": item.product_code,
                            "quantity_added": float(item.quantity),
                            "new_stock": float(item.quantity)
                        })

                # ── 4. Mark invoice as confirmed ──────────────────────────
                await session.execute(
                    update(ProcessedInvoice)
                    .where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                    .values(pricing_status="confirmed")
                )
                await session.commit()

                # ── 5a. Guard: remisiones no generan bill en Alegra ──────
                if getattr(invoice_record, 'document_type', None) == "remision":
                    await session.execute(
                        update(ProcessedInvoice)
                        .where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                        .values(alegra_sync_status="skipped_remision")
                    )
                    await session.commit()
                    return {
                        "status": "confirmed",
                        "document_type": "remision",
                        "message": "Entrada de inventario registrada. No se creó factura en Alegra.",
                        "inventory_updated": True,
                        "total_items": len(priced_items),
                        "inventory_updates": inventory_updates,
                        "alegra_bill": None,
                        "alegra_synced": False,
                    }

                # ── 5. Try Alegra POST /bills (non-blocking) ─────────────
                alegra_bill = None
                try:
                    tenant_result = await session.execute(
                        select(Tenant).where(Tenant.tenant_id == tenant_id)
                    )
                    tenant = tenant_result.scalar_one_or_none()

                    if tenant and tenant.integration_config:
                        from ...services.integrations.alegra_integration import get_client_from_config
                        client = get_client_from_config(tenant.integration_config)

                        bill_date = (
                            invoice_record.issue_date.strftime("%Y-%m-%d")
                            if invoice_record and invoice_record.issue_date
                            else datetime.utcnow().strftime("%Y-%m-%d")
                        )
                        # ── MAPPING 1: supplier_nit → alegra_contact_id ───
                        from ...services.integrations.alegra_integration import IVA_RATE_TO_ALEGRA_ID, _DEFAULT_TAX_ID
                        supplier_row = None
                        supplier_nit = invoice_record.supplier_nit if invoice_record else None
                        supplier_name = (invoice_record.supplier_name or "Proveedor") if invoice_record else "Proveedor"

                        if supplier_nit:
                            supplier_result = await session.execute(
                                select(Supplier)
                                .where(Supplier.nit == supplier_nit)
                                .where(Supplier.tenant_id == tenant_id)
                            )
                            supplier_row = supplier_result.scalar_one_or_none()

                        logger.info(f"SUPPLIER NIT: {supplier_nit}")
                        logger.info(f"SUPPLIER NAME: {supplier_name}")

                        # Usar alegra_contact_id ya guardado, o buscar/crear por NIT
                        if supplier_row and supplier_row.alegra_contact_id:
                            contact_id = str(supplier_row.alegra_contact_id)
                            logger.info(f"Contact en caché (BD): {contact_id}")
                        elif supplier_nit:
                            contact_id = await client.get_or_create_contact(
                                nit=supplier_nit,
                                name=supplier_name,
                            )
                            if supplier_row:
                                supplier_row.alegra_contact_id = contact_id
                                session.add(supplier_row)
                        else:
                            # Sin NIT no podemos buscar/crear contacto confiablemente
                            raise ValueError(f"Factura sin NIT de proveedor — no se puede crear bill en Alegra")

                        logger.info(f"PROVIDER ID enviado a Alegra: {contact_id}")
                        provider_payload: Dict[str, Any] = {"id": contact_id}

                        # ── MAPPING 2: bill items — requiere id de catálogo Alegra ──
                        bill_items = []
                        for item in priced_items:
                            iva_rate = item.iva_rate or (invoice_record.iva_rate if invoice_record else None)
                            rate_key = int(float(iva_rate)) if iva_rate is not None else None
                            tax_payload = [{"id": IVA_RATE_TO_ALEGRA_ID.get(rate_key, _DEFAULT_TAX_ID)}]

                            # Buscar producto en BD para obtener alegra_item_id
                            alegra_item_id = None
                            if item.product_code:
                                product_result = await session.execute(
                                    select(Product)
                                    .where(Product.product_code == item.product_code)
                                    .where(Product.tenant_id == tenant_id)
                                )
                                product_row = product_result.scalar_one_or_none()
                                if product_row:
                                    alegra_item_id = product_row.alegra_item_id

                            # Si no tiene id en Alegra, crear o recuperar por referencia
                            if not alegra_item_id and item.product_code:
                                sale_price = float(item.sale_price) if item.sale_price else float(item.unit_price)
                                try:
                                    new_item = await client.create_item({
                                        "name": (item.description or item.product_code)[:255],
                                        "reference": item.product_code,
                                        "type": "product",
                                        "price": [{"idPriceList": 1, "price": sale_price}],
                                    })
                                    alegra_item_id = str(new_item.get("id"))
                                    logger.info(f"Alegra item creado: {alegra_item_id} para {item.product_code}")
                                except Exception as create_exc:
                                    # code 1009 = referencia duplicada → buscar el ítem existente
                                    logger.warning(f"create_item falló para {item.product_code}: {create_exc} — buscando por referencia")
                                    try:
                                        existing = await client.find_item_by_reference(item.product_code)
                                        if existing:
                                            alegra_item_id = str(existing["id"])
                                            logger.info(f"Ítem encontrado por referencia: {alegra_item_id} para {item.product_code}")
                                    except Exception as find_exc:
                                        logger.warning(f"No se encontró ítem en Alegra para {item.product_code}: {find_exc}")

                            if not alegra_item_id:
                                logger.warning(f"Skipping ítem sin alegra_item_id: {item.product_code}")
                                continue

                            # Persistir el id para futuros bills
                            if item.product_code and alegra_item_id:
                                await session.execute(
                                    update(Product)
                                    .where(Product.product_code == item.product_code)
                                    .where(Product.tenant_id == tenant_id)
                                    .values(alegra_item_id=alegra_item_id)
                                )

                            # Cuando el ítem tiene id del catálogo, Alegra
                            # no acepta name ni tax — vienen del ítem registrado
                            bill_items.append({
                                "id": str(alegra_item_id),
                                "quantity": float(item.quantity),
                                "price": float(item.unit_price),
                            })

                        due_date = (date.today() + timedelta(days=30)).isoformat()
                        bill_payload: Dict[str, Any] = {
                            "date": bill_date,
                            "dueDate": due_date,
                            "provider": provider_payload,
                            "purchases": {
                                "items": bill_items,
                            },
                        }

                        logger.info(f"ALEGRA POST /bills payload: {json.dumps(bill_payload, default=str, indent=2)}")
                        alegra_bill = await client.post_bill(bill_payload)
                        logger.info(f"Alegra bill created: {alegra_bill.get('id')} for invoice {invoice_id}")

                except ValueError:
                    # Alegra not configured for this tenant — skip silently
                    pass
                except Exception as e:
                    logger.warning(f"Alegra POST /bills failed: {e}")
                    await session.execute(
                        update(ProcessedInvoice)
                        .where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                        .values(
                            alegra_sync_status="failed",
                            alegra_error=str(e)[:500],
                        )
                    )
                    await session.commit()

                return {
                    "status": "confirmed",
                    "inventory_updated": True,
                    "total_items": len(priced_items),
                    "inventory_updates": inventory_updates,
                    "alegra_bill": alegra_bill,
                    "alegra_synced": alegra_bill is not None,
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

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_analytics_summary(self, tenant_id: str) -> Dict[str, Any]:
        """Return aggregated analytics for a tenant's invoices."""
        invoices = await self.list_tenant_invoices(tenant_id, limit=1000)

        total = len(invoices)
        completed = sum(1 for inv in invoices if inv.status == InvoiceStatus.COMPLETED)
        failed = sum(1 for inv in invoices if inv.status == InvoiceStatus.FAILED)
        total_amount = sum(
            inv.invoice_data.totals.total
            for inv in invoices
            if inv.invoice_data and inv.invoice_data.totals
        )

        return {
            "tenant_id": tenant_id,
            "total_invoices": total,
            "completed_invoices": completed,
            "failed_invoices": failed,
            "success_rate": completed / total if total > 0 else 0,
            "total_amount_processed": float(total_amount),
            "currency": "COP",
        }

    # ------------------------------------------------------------------
    # Pricing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def build_pricing_summary(updated_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a totals summary from the list returned by set_invoice_pricing."""
        total_cost = sum(
            item.get("cost_price", 0) * item.get("quantity", 0)
            for item in updated_items
        )
        total_sale_value = sum(item.get("total_sale_value", 0) for item in updated_items)
        total_profit = sum(item.get("total_profit", 0) for item in updated_items)
        avg_markup = (total_profit / total_cost * 100) if total_cost > 0 else 0

        return {
            "total_items": len(updated_items),
            "total_cost": round(total_cost, 2),
            "total_sale_value": round(total_sale_value, 2),
            "total_profit": round(total_profit, 2),
            "average_markup": round(avg_markup, 2),
        }
