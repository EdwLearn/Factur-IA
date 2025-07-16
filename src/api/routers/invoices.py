"""
Invoice processing endpoints with multi-tenant support - FIXED
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from typing import List, Optional
import uuid
import logging
from datetime import datetime

from ...config.settings import settings
from ...services.document_processing import InvoiceProcessorService
from ...models.invoice import ProcessedInvoice, InvoiceData, InvoiceStatus

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize service
invoice_service = InvoiceProcessorService()

async def get_tenant_id(x_tenant_id: str = Header(...)) -> str:
    """Extract tenant ID from header"""
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID header required")
    return x_tenant_id

@router.post("/upload", response_model=ProcessedInvoice)
async def upload_invoice(
    file: UploadFile = File(..., description="PDF invoice to process"),
    tenant_id: str = Depends(get_tenant_id)
):
    """Upload a PDF invoice for processing"""
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )
        
        # Validate file size (15MB limit for invoices)
        if file.size and file.size > 15 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File size must be less than 15MB"
            )
        
        # Generate unique invoice ID
        invoice_id = str(uuid.uuid4())
        
        # Read file content
        file_content = await file.read()
        
        # Upload and process
        result = await invoice_service.upload_and_process_invoice(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            filename=file.filename,
            file_content=file_content
        )
        
        # Return the processed invoice
        processed_invoice = await invoice_service.get_invoice_status(invoice_id, tenant_id)
        
        logger.info(f"Invoice uploaded: {invoice_id} for tenant {tenant_id}")
        return processed_invoice
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading invoice: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload invoice: {str(e)}"
        )

@router.get("/analytics/summary")
async def get_tenant_analytics(
    tenant_id: str = Depends(get_tenant_id)
):
    """Get analytics summary for tenant"""
    try:
        invoices = await invoice_service.list_tenant_invoices(tenant_id, limit=1000)
        
        total_invoices = len(invoices)
        completed_invoices = len([inv for inv in invoices if inv.status == InvoiceStatus.COMPLETED])
        failed_invoices = len([inv for inv in invoices if inv.status == InvoiceStatus.FAILED])
        
        # Calculate total extracted amounts
        total_amount = sum(
            inv.invoice_data.totals.total 
            for inv in invoices 
            if inv.invoice_data and inv.invoice_data.totals
        )
        
        return {
            "tenant_id": tenant_id,
            "total_invoices": total_invoices,
            "completed_invoices": completed_invoices,
            "failed_invoices": failed_invoices,
            "success_rate": completed_invoices / total_invoices if total_invoices > 0 else 0,
            "total_amount_processed": float(total_amount),
            "currency": "COP"
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analytics: {str(e)}"
        )

@router.get("/", response_model=List[ProcessedInvoice])
async def list_invoices(
    tenant_id: str = Depends(get_tenant_id),
    limit: int = 10,
    offset: int = 0,
    status: Optional[InvoiceStatus] = None
):
    """List invoices for the tenant"""
    try:
        invoices = await invoice_service.list_tenant_invoices(
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
            status=status
        )
        
        return invoices
        
    except Exception as e:
        logger.error(f"Error listing invoices: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list invoices: {str(e)}"
        )

@router.get("/{invoice_id}/status", response_model=ProcessedInvoice)
async def get_invoice_status(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get processing status of an invoice"""
    try:
        invoice = await invoice_service.get_invoice_status(invoice_id, tenant_id)
        
        if not invoice:
            raise HTTPException(
                status_code=404,
                detail="Invoice not found"
            )
        
        return invoice
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invoice status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get invoice status: {str(e)}"
        )

@router.get("/{invoice_id}/data", response_model=InvoiceData)
async def get_invoice_data(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get extracted invoice data - FIXED to not require 'completed' status"""
    try:
        # First check if invoice exists
        invoice_status = await invoice_service.get_invoice_status(invoice_id, tenant_id)
        
        if not invoice_status:
            raise HTTPException(
                status_code=404,
                detail="Invoice not found"
            )
        
        # Check if processing is complete (allow 'completed' or 'failed' with data)
        if invoice_status.status not in [InvoiceStatus.COMPLETED, InvoiceStatus.FAILED]:
            raise HTTPException(
                status_code=409,  # Conflict
                detail=f"Invoice is still {invoice_status.status}. Please wait for processing to complete."
            )
        
        # Get the data (remove status filter)
        invoice_data = await invoice_service.get_invoice_data(invoice_id, tenant_id)
        
        if not invoice_data:
            raise HTTPException(
                status_code=404,
                detail="Invoice data not available - processing may have failed"
            )
        
        return invoice_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invoice data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get invoice data: {str(e)}"
        )


@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Delete an invoice"""
    try:
        success = await invoice_service.delete_invoice(invoice_id, tenant_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Invoice not found"
            )
        
        return {
            "message": "Invoice deleted successfully",
            "invoice_id": invoice_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting invoice: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete invoice: {str(e)}"
        )


