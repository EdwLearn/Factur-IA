"""
Invoice processing service - Development mode without S3
"""
import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from decimal import Decimal

from ..config.settings import settings
from ..models.invoice import (
    ProcessedInvoice, InvoiceData, InvoiceStatus, InvoiceType,
    SupplierInfo, CustomerInfo, InvoiceLineItem, InvoiceTotals, PaymentInfo
)

logger = logging.getLogger(__name__)

class InvoiceProcessorService:
    """Service for processing invoices - DEV MODE"""
    
    def __init__(self):
        # In-memory storage for development
        self.processed_invoices: Dict[str, ProcessedInvoice] = {}
    
    async def upload_and_process_invoice(
        self, 
        tenant_id: str,
        invoice_id: str, 
        filename: str, 
        file_content: bytes
    ) -> Dict[str, Any]:
        """Upload and process invoice - DEV MODE"""
        try:
            # Simulate S3 key
            s3_key = f"invoices/{tenant_id}/{invoice_id}/{filename}"
            
            # Create processed invoice record
            processed_invoice = ProcessedInvoice(
                id=invoice_id,
                tenant_id=tenant_id,
                original_filename=filename,
                file_size=len(file_content),
                upload_timestamp=datetime.utcnow(),
                status=InvoiceStatus.UPLOADED,
                s3_key=s3_key
            )
            
            # Store in memory
            self.processed_invoices[invoice_id] = processed_invoice
            
            # Start processing
            await self._start_invoice_processing(invoice_id)
            
            logger.info(f"Invoice uploaded: {invoice_id} for tenant {tenant_id}")
            
            return {
                'invoice_id': invoice_id,
                'tenant_id': tenant_id,
                's3_key': s3_key,
                'status': 'uploaded'
            }
            
        except Exception as e:
            logger.error(f"Error uploading invoice: {str(e)}")
            raise
    
    async def _start_invoice_processing(self, invoice_id: str):
        """Process invoice - simulate Textract"""
        try:
            # Update status
            if invoice_id in self.processed_invoices:
                self.processed_invoices[invoice_id].status = InvoiceStatus.PROCESSING
                self.processed_invoices[invoice_id].processing_timestamp = datetime.utcnow()
            
            # Simulate processing time
            await asyncio.sleep(2)
            
            # Mock extracted data
            extracted_data = self._create_mock_invoice_data()
            
            # Update with results
            if invoice_id in self.processed_invoices:
                self.processed_invoices[invoice_id].status = InvoiceStatus.COMPLETED
                self.processed_invoices[invoice_id].completion_timestamp = datetime.utcnow()
                self.processed_invoices[invoice_id].invoice_data = extracted_data
                self.processed_invoices[invoice_id].confidence_score = 0.95
                
            logger.info(f"Invoice processing completed: {invoice_id}")
            
        except Exception as e:
            logger.error(f"Error processing invoice {invoice_id}: {str(e)}")
            if invoice_id in self.processed_invoices:
                self.processed_invoices[invoice_id].status = InvoiceStatus.FAILED
                self.processed_invoices[invoice_id].error_message = str(e)
    
    def _create_mock_invoice_data(self) -> InvoiceData:
        """Create detailed mock with MANY products like real invoices"""
        return InvoiceData(
            invoice_number="PMB2207",
            invoice_type=InvoiceType.FACTURA_VENTA,
            issue_date=date(2025, 6, 26),
            due_date=date(2025, 8, 25),
            
            supplier=SupplierInfo(
                company_name="PUNTO MODA BODEGA",
                nit="70000000-5",
                address="BARRANQUILLA",
                department="ATLANTICO"
            ),
            
            customer=CustomerInfo(
                customer_name="HENRRI GIRALDO",
                customer_id="70353036-0",
                address="CRA 6 N#5 120",
                city="PAILITAS",
                department="CESAR",
                phone="3113053740"
            ),
            
            line_items=[
                InvoiceLineItem(
                    product_code="5428",
                    description="BERMUDA HYPER DENIM H REF: JJ-FF-238",
                    reference="JJ-FF-238",
                    quantity=Decimal("12"),
                    unit_price=Decimal("35000"),
                    subtotal=Decimal("420000")
                ),
                InvoiceLineItem(
                    product_code="7598", 
                    description="PANTALONETA H AMERICAN REF: F24-FPF345",
                    reference="F24-FPF345",
                    quantity=Decimal("12"),
                    unit_price=Decimal("25000"),
                    subtotal=Decimal("300000")
                ),
                InvoiceLineItem(
                    product_code="8297",
                    description="SUETER H SOUTHLAN REF: SOT-0782",
                    reference="SOT-0782", 
                    quantity=Decimal("12"),
                    unit_price=Decimal("30000"),
                    subtotal=Decimal("360000")
                ),
                InvoiceLineItem(
                    product_code="1387",
                    description="PANTY MAJA REF: 03223",
                    reference="03223",
                    quantity=Decimal("12"),
                    unit_price=Decimal("5000"),
                    subtotal=Decimal("60000")
                ),
                InvoiceLineItem(
                    product_code="8028",
                    description="MEDIA H RUNNING X3 REF: HFP40141",
                    reference="HFP40141",
                    quantity=Decimal("120"),
                    unit_price=Decimal("1800"),
                    subtotal=Decimal("216000")
                )
            ],
            
            totals=InvoiceTotals(
                subtotal=Decimal("1356000"),
                iva_rate=Decimal("19"),
                iva_amount=Decimal("257640"),
                total=Decimal("1613640"),
                total_items=5
            ),
            
            payment_info=PaymentInfo(
                payment_method="CREDITO 60 DIAS",
                credit_days=60
            )
        )
    
    async def get_invoice_status(self, invoice_id: str, tenant_id: str) -> Optional[ProcessedInvoice]:
        """Get invoice status"""
        invoice = self.processed_invoices.get(invoice_id)
        if invoice and invoice.tenant_id == tenant_id:
            return invoice
        return None
    
    async def get_invoice_data(self, invoice_id: str, tenant_id: str) -> Optional[InvoiceData]:
        """Get extracted invoice data"""
        invoice = await self.get_invoice_status(invoice_id, tenant_id)
        if invoice and invoice.status == InvoiceStatus.COMPLETED:
            return invoice.invoice_data
        return None
    
    async def list_tenant_invoices(
        self, 
        tenant_id: str,
        limit: int = 10, 
        offset: int = 0,
        status: Optional[InvoiceStatus] = None
    ) -> List[ProcessedInvoice]:
        """List tenant invoices"""
        tenant_invoices = [
            invoice for invoice in self.processed_invoices.values()
            if invoice.tenant_id == tenant_id
        ]
        
        if status:
            tenant_invoices = [inv for inv in tenant_invoices if inv.status == status]
        
        tenant_invoices.sort(key=lambda x: x.upload_timestamp, reverse=True)
        return tenant_invoices[offset:offset + limit]
    
    async def delete_invoice(self, invoice_id: str, tenant_id: str) -> bool:
        """Delete invoice"""
        invoice = self.processed_invoices.get(invoice_id)
        if not invoice or invoice.tenant_id != tenant_id:
            return False
        
        del self.processed_invoices[invoice_id]
        return True
