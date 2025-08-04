"""
Invoice processing endpoints with multi-tenant support - FIXED
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from fastapi.responses import Response
import uuid
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from ...database.connection import AsyncSessionFactory
from ...database.models import InvoiceLineItem, Product, Tenant
from ...services.integrations.integration_factory import IntegrationFactory
from sqlalchemy import select, update

from pydantic import UUID4, ValidationError
from decimal import Decimal

# Agregar estos imports después de los existentes
from ...models.invoice import (
    PricingDataResponse,
    PricingUpdateRequest, 
    PricingConfirmationResponse,
    PricingSummary,
    InvoiceLineItemPricing,
    LineItemPricingUpdate,
    PricingStatus,
    calculate_pricing_summary
)

from ...config.settings import settings
from ...services.document_processing import InvoiceProcessorService
from ...models.invoice import ProcessedInvoice, InvoiceData, InvoiceStatus
from ...services.duplicate_detection.duplicate_detector import DuplicateDetector
from ...database.connection import AsyncSessionFactory
from ...services.integrations.mayasis_integration import MayasisIntegration



duplicate_detector = DuplicateDetector()
mayasis_integration = MayasisIntegration()

logger = logging.getLogger(__name__)

def validate_uuid(uuid_string: str) -> UUID4:
    """Validate and convert string to UUID"""
    try:
        return uuid.UUID(uuid_string)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid UUID format: {uuid_string}"
        )

def calculate_markup_percentage(cost_price: Decimal, sale_price: Decimal) -> Decimal:
    """Calculate markup percentage"""
    if cost_price <= 0:
        return Decimal('0')
    return round(((sale_price - cost_price) / cost_price) * 100, 2)

def calculate_profit_margin(cost_price: Decimal, sale_price: Decimal) -> Decimal:
    """Calculate profit margin"""
    if sale_price <= 0:
        return Decimal('0')
    return round(((sale_price - cost_price) / sale_price) * 100, 2)

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



@router.post("/upload-photo", response_model=ProcessedInvoice)
async def upload_photo(
    file: UploadFile = File(..., description="Photo of invoice from mobile device"),
    tenant_id: str = Depends(get_tenant_id)
):
    """Upload a photo of an invoice for processing with image enhancement"""
    try:
        # Validate file type (accept common image formats)
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        file_extension = '.' + file.filename.lower().split('.')[-1]
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Only image files are supported: {', '.join(allowed_extensions)}"
            )
        
        # Validate file size (10MB limit for photos)
        if file.size and file.size > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Photo size must be less than 10MB"
            )
        
        # Generate unique invoice ID
        invoice_id = str(uuid.uuid4())
        
        # Read file content
        photo_content = await file.read()
        
        # Process photo and convert to PDF
        result = await invoice_service.upload_and_process_photo(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            filename=file.filename,
            photo_content=photo_content
        )
        
        # Return the processed invoice
        processed_invoice = await invoice_service.get_invoice_status(invoice_id, tenant_id)
        
        logger.info(f"Photo uploaded and processed: {invoice_id} for tenant {tenant_id}")
        return processed_invoice
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading photo: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload photo: {str(e)}"
        )

@router.get("/{invoice_id}/pricing")
async def get_invoice_pricing_data(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get invoice data ready for manual pricing"""
    try:
        # Validate UUID format
        invoice_uuid = validate_uuid(invoice_id)
        
        pricing_data = await invoice_service.get_pricing_data(invoice_id, tenant_id)
        
        if not pricing_data:
            raise HTTPException(status_code=404, detail="Invoice not found or no line items")
        
        return pricing_data
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting pricing data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pricing data: {str(e)}"
        )

# Actualizar en: apps/api/src/api/routers/invoices.py
# Reemplazar el método set_invoice_pricing existente

@router.post("/{invoice_id}/pricing")
async def set_invoice_pricing(
    invoice_id: str,
    pricing_data: Dict[str, Any],
    tenant_id: str = Depends(get_tenant_id)
):
    """Set manual pricing for invoice line items - DATOS REALES"""
    try:
        # Validar UUID format
        invoice_uuid = validate_uuid(invoice_id)
        
        # Validar que tenemos line_items
        line_items = pricing_data.get('line_items')
        if not line_items:
            raise HTTPException(
                status_code=400,
                detail="Missing 'line_items' in request body"
            )
        
        # Validar formato de line_items
        for item in line_items:
            if not item.get('line_item_id'):
                raise HTTPException(
                    status_code=400,
                    detail="Missing 'line_item_id' in line item"
                )
            if not item.get('sale_price') or float(item.get('sale_price', 0)) <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid 'sale_price' for item {item.get('line_item_id')}"
                )
        
        logger.info(f"💰 Setting pricing for invoice {invoice_id}: {len(line_items)} items")
        
        # Llamar al service REAL
        updated_items = await invoice_service.set_invoice_pricing(
            invoice_id, tenant_id, pricing_data
        )
        
        if not updated_items:
            raise HTTPException(
                status_code=400,
                detail="No items were updated. Check line_item_ids and sale_prices."
            )
        
        # Calcular summary
        total_cost = sum(item.get('cost_price', 0) * item.get('quantity', 0) for item in updated_items)
        total_sale_value = sum(item.get('total_sale_value', 0) for item in updated_items)
        total_profit = sum(item.get('total_profit', 0) for item in updated_items)
        avg_markup = (total_profit / total_cost * 100) if total_cost > 0 else 0
        
        response = {
            "message": "Pricing updated successfully with REAL data",
            "invoice_id": invoice_id,
            "updated_items": len(updated_items),
            "items": updated_items,
            "summary": {
                "total_items": len(updated_items),
                "total_cost": round(total_cost, 2),
                "total_sale_value": round(total_sale_value, 2),
                "total_profit": round(total_profit, 2),
                "average_markup": round(avg_markup, 2),
                "status": "✅ Data saved to database"
            }
        }
        
        logger.info(f"✅ PRICING SUCCESS: {len(updated_items)} items updated for invoice {invoice_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error setting pricing for invoice {invoice_id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

# Add a endpoint to verify save data
@router.get("/{invoice_id}/pricing-verification")
async def verify_pricing_data(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Verify that pricing data was saved correctly"""
    try:
        async with AsyncSessionFactory() as session:
            # Get line items with pricing
            result = await session.execute(
                select(InvoiceLineItem)
                .where(InvoiceLineItem.invoice_id == uuid.UUID(invoice_id))
            )
            line_items = result.scalars().all()
            
            verification_data = []
            for item in line_items:
                verification_data.append({
                    "line_item_id": str(item.id),
                    "product_code": item.product_code,
                    "description": item.description[:50] + "..." if len(item.description or "") > 50 else item.description,
                    "cost_price": float(item.unit_price) if item.unit_price else 0,
                    "sale_price": float(item.sale_price) if item.sale_price else None,
                    "markup_percentage": float(item.markup_percentage) if item.markup_percentage else None,
                    "is_priced": item.is_priced,
                    "database_status": "✅ Saved" if item.sale_price else "⚠️ Not priced"
                })
            
            priced_count = sum(1 for item in verification_data if item["sale_price"])
            
            return {
                "invoice_id": invoice_id,
                "verification_timestamp": datetime.utcnow().isoformat(),
                "total_items": len(verification_data),
                "priced_items": priced_count,
                "pending_items": len(verification_data) - priced_count,
                "database_verification": "✅ Connected and readable",
                "items": verification_data
            }
            
    except Exception as e:
        logger.error(f"Error verifying pricing data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")



@router.post("/{invoice_id}/confirm-pricing")
async def confirm_invoice_pricing(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Confirm pricing and update inventory with REAL data"""
    try:
        # Use REAL service method
        result = await invoice_service.confirm_invoice_pricing(invoice_id, tenant_id)
        
        return {
            "message": "Pricing confirmed and inventory updated successfully",
            "invoice_id": invoice_id,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error confirming pricing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to confirm pricing: {str(e)}"
        )

@router.get("/{invoice_id}/debug-pricing")
async def debug_pricing_data(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Debug endpoint to isolate pricing issues"""
    try:
        from ...database.connection import AsyncSessionFactory
        from ...database.models import ProcessedInvoice, InvoiceLineItem
        from sqlalchemy import select
        import uuid
        
        async with AsyncSessionFactory() as session:
            # Test 1: Get invoice
            print(f"Looking for invoice: {invoice_id}")
            invoice_result = await session.execute(
                select(ProcessedInvoice)
                .where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                .where(ProcessedInvoice.tenant_id == tenant_id)
            )
            invoice = invoice_result.scalar_one_or_none()
            
            if not invoice:
                return {"error": "Invoice not found", "step": "1"}
            
            # Test 2: Get line items
            print(f"Looking for line items...")
            line_items_result = await session.execute(
                select(InvoiceLineItem)
                .where(InvoiceLineItem.invoice_id == uuid.UUID(invoice_id))
            )
            line_items = line_items_result.scalars().all()
            
            return {
                "invoice_found": True,
                "invoice_number": invoice.invoice_number,
                "line_items_count": len(line_items),
                "step": "completed"
            }
            
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "step": "exception"
        }

@router.post("/test-price-rounding")
async def test_price_rounding(
    test_prices: List[float],
    tenant_id: str = Depends(get_tenant_id)
):
    """Test price rounding with Colombian retail conventions"""
    from ...services.ml_services.price_utils import (
        round_price_colombian, 
        format_colombian_price,
        test_price_rounding
    )
    
    results = []
    
    # Test user-provided prices
    for price in test_prices:
        rounded = round_price_colombian(price)
        results.append({
            "original": price,
            "rounded": float(rounded),
            "formatted": format_colombian_price(rounded),
            "difference": float(rounded) - price
        })
    
    # Run built-in tests
    test_results = test_price_rounding()
    
    return {
        "user_tests": results,
        "built_in_tests": test_results,
        "rounding_rules": {
            ">=10000": "Round to nearest 1,000 (always up)",
            ">=1000": "Round to nearest 500", 
            ">=100": "Round to nearest 100",
            "<100": "Round to nearest 50"
        }
    }

@router.get("/{invoice_id}/pricing-with-ml")
async def get_ml_pricing_recommendations(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get ML-powered pricing recommendations for invoice"""
    from ...services.ml_services.pricing_engine import get_pricing_engine
    
    try:
        # Get real invoice data
        pricing_data = await invoice_service.get_pricing_data(invoice_id, tenant_id)
        
        if not pricing_data:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        pricing_engine = get_pricing_engine()
        
        # Generate ML recommendations for each line item
        ml_recommendations = []
        
        for item in pricing_data['line_items']:
            recommendation = await pricing_engine.recommend_sale_price(
                product_code=item['product_code'],
                description=item['description'],
                cost_price=Decimal(str(item['unit_price'])),
                quantity=Decimal(str(item['quantity'])),
                supplier=pricing_data.get('supplier_name')
            )
            
            ml_recommendations.append({
                'line_item_id': item['id'],
                'product_info': {
                    'code': item['product_code'],
                    'description': item['description'],
                    'cost_price': item['unit_price'],
                    'quantity': item['quantity']
                },
                'ml_recommendation': recommendation
            })
        
        return {
            'invoice_id': invoice_id,
            'invoice_info': {
                'number': pricing_data['invoice_number'],
                'supplier': pricing_data['supplier_name'],
                'total_items': len(ml_recommendations)
            },
            'ml_recommendations': ml_recommendations
        }
        
    except Exception as e:
        logger.error(f"Error getting ML pricing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get ML pricing: {str(e)}")        
        
@router.post("/test-ml-classification")
async def test_ml_classification(
    descriptions: List[str],
    tenant_id: str = Depends(get_tenant_id)
):
    """Test ML classification on product descriptions"""
    from ...services.ml_services.category_classifier import get_category_classifier
    from ...services.ml_services.pricing_engine import get_pricing_engine
    
    classifier = get_category_classifier()
    pricing_engine = get_pricing_engine()
    
    results = []
    
    for desc in descriptions:
        # Test classification
        category_result = classifier.classify_product(desc)
        
        # Test pricing recommendation
        pricing_result = await pricing_engine.recommend_sale_price(
            product_code=f"TEST-{hash(desc) % 1000}",
            description=desc,
            cost_price=Decimal("10000"),  # Test cost
            quantity=Decimal("12")        # Test quantity
        )
        
        results.append({
            "description": desc,
            "classification": category_result,
            "pricing_recommendation": pricing_result
        })
    
    return {
        "test_results": results,
        "ml_status": "active" if classifier.classifier else "fallback_mode"
    }

@router.get("/mock-casoli")
async def get_mock_casoli_data(tenant_id: str = Depends(get_tenant_id)):
    """Mock data de factura Casoli para testing rápido"""
    from ...services.document_processing.textract.textract_service import TextractService
    
    textract = TextractService()
    mock_items = textract._get_casoli_mock_items()
    
    return {
        "message": "Mock Casoli data",
        "line_items": mock_items,
        "enhancer_test": "ready"
    }
    

# ---------------

@router.get("/test")
async def test_endpoint(tenant_id: str = Depends(get_tenant_id)):
    """Test endpoint to verify API is working"""
    return {
        "message": "Invoice API is working perfectly!",
        "tenant_id": tenant_id,
        "pricing_endpoints": {
            "get_pricing": "GET /api/v1/invoices/{id}/pricing",
            "set_pricing": "POST /api/v1/invoices/{id}/pricing", 
            "confirm_pricing": "POST /api/v1/invoices/{id}/confirm-pricing"
        },
        "status": "All systems operational",
        "pricing_system": "Manual pricing with automatic margin calculation",
        "ready_for_ml": "Product matching and pricing recommendations coming next"
    }
    
@router.post("/{invoice_id}/check-duplicates")
async def check_invoice_duplicates(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Check for duplicate products in invoice line items"""
    try:
        # Validate UUID format
        invoice_uuid = validate_uuid(invoice_id)
        
        async with AsyncSessionFactory() as session:
            from ...database.models import InvoiceLineItem
            from sqlalchemy import select
            
            # Get invoice line items
            result = await session.execute(
                select(InvoiceLineItem)
                .where(InvoiceLineItem.invoice_id == invoice_uuid)
            )
            line_items = result.scalars().all()
            
            if not line_items:
                raise HTTPException(
                    status_code=404, 
                    detail="No line items found for this invoice"
                )
            
            # Convert to dict format for duplicate checker
            items_data = []
            for item in line_items:
                items_data.append({
                    "id": str(item.id),
                    "product_code": item.product_code,
                    "description": item.description,
                    "quantity": float(item.quantity),
                    "unit_price": float(item.unit_price),
                    "subtotal": float(item.subtotal)
                })
            
            # Check for duplicates
            duplicate_results = await duplicate_detector.check_invoice_duplicates(
                invoice_line_items=items_data,
                tenant_id=tenant_id,
                db=session
            )
            
            return {
                "invoice_id": invoice_id,
                "duplicate_check_completed": True,
                "results": duplicate_results
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking duplicates: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check duplicates: {str(e)}"
        )

@router.post("/{invoice_id}/resolve-duplicates")
async def resolve_invoice_duplicates(
    invoice_id: str,
    resolution_data: Dict[str, Any],
    tenant_id: str = Depends(get_tenant_id)
):
    """Resolve duplicate conflicts by linking to existing products or creating new ones"""
    try:
        # Validate UUID format
        invoice_uuid = validate_uuid(invoice_id)

        # Expected format for resolution_data:
        # {
        #   "resolutions": [
        #     {
        #       "line_item_id": "abc-123",
        #       "action": "merge_with_existing", # or "create_new_product"
        #       "existing_product_id": "def-456" # only if action is "merge_with_existing"
        #     }
        #   ]
        # }

        resolutions = resolution_data.get("resolutions", [])

        if not resolutions:
            raise HTTPException(
                status_code=400,
                detail="No resolutions provided"
            )

        async with AsyncSessionFactory() as session:
            # Initialize duplicate detector
            from ...services.duplicate_detection.duplicate_detector import DuplicateDetector
            duplicate_detector = DuplicateDetector()
            
            # Process resolutions
            result = await duplicate_detector.resolve_duplicates(
                resolutions=resolutions,
                tenant_id=tenant_id,
                db=session
            )
            
            # If all resolutions were successful, update invoice status
            if result.get("failed", 0) == 0:
                # Update invoice pricing status to indicate duplicates resolved
                invoice_query = select(ProcessedInvoice).where(
                    ProcessedInvoice.id == invoice_uuid,
                    ProcessedInvoice.tenant_id == tenant_id
                )
                invoice_result = await session.execute(invoice_query)
                invoice = invoice_result.scalar_one_or_none()
                
                if invoice:
                    if invoice.pricing_status == "pending_duplicates":
                        invoice.pricing_status = "duplicates_resolved"
                        await session.commit()
            
            return {
                "duplicate_resolution_completed": True,
                "invoice_id": invoice_id,
                **result
            }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error resolving duplicates for invoice {invoice_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during duplicate resolution"
        )

@router.get("/{invoice_id}/duplicate-suggestions/{line_item_id}")
async def get_duplicate_suggestions(
    invoice_id: str,
    line_item_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get specific duplicate suggestions for a line item"""
    try:
        # Validate UUIDs
        invoice_uuid = validate_uuid(invoice_id)
        line_item_uuid = validate_uuid(line_item_id)
        
        async with AsyncSessionFactory() as session:
            from ...database.models import InvoiceLineItem
            from sqlalchemy import select
            
            # Get the specific line item
            result = await session.execute(
                select(InvoiceLineItem)
                .where(InvoiceLineItem.id == line_item_uuid)
                .where(InvoiceLineItem.invoice_id == invoice_uuid)
            )
            line_item = result.scalar_one_or_none()
            
            if not line_item:
                raise HTTPException(
                    status_code=404,
                    detail="Line item not found"
                )
            
            # Find similar products
            similar_products = await duplicate_detector.find_similar_products(
                product_description=line_item.description,
                product_code=line_item.product_code,
                tenant_id=tenant_id,
                db=session
            )
            
            return {
                "invoice_id": invoice_id,
                "line_item_id": line_item_id,
                "line_item_info": {
                    "product_code": line_item.product_code,
                    "description": line_item.description,
                    "quantity": float(line_item.quantity),
                    "unit_price": float(line_item.unit_price)
                },
                "similar_products": similar_products,
                "suggestions_count": len(similar_products)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting duplicate suggestions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get suggestions: {str(e)}"
        )
        
        
@router.get("/{invoice_id}/export-mayasis")
async def export_to_mayasis(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Export confirmed invoice to Mayasis CSV format"""
    try:
        # Get invoice pricing data
        pricing_data = await invoice_service.get_pricing_data(invoice_id, tenant_id)
        
        if not pricing_data:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Generate CSV
        csv_content = await mayasis_integration.prepare_invoice_for_mayasis(pricing_data)
        
        # Return as downloadable file
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=mayasis_import_{invoice_id}.csv"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting to Mayasis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/test-duplicates")
async def test_duplicate_system(tenant_id: str = Depends(get_tenant_id)):
    """Test endpoint to verify duplicate detection system is working"""
    try:
        # Test the duplicate detector with sample data
        test_description = "Nike Air Max zapatos deportivos"
        
        async with AsyncSessionFactory() as session:
            similar_products = await duplicate_detector.find_similar_products(
                product_description=test_description,
                product_code="NIKE-001",
                tenant_id=tenant_id,
                db=session
            )
            
            return {
                "message": "Duplicate detection system is working!",
                "test_description": test_description,
                "similar_products_found": len(similar_products),
                "similarity_threshold": duplicate_detector.similarity_threshold,
                "status": "✅ Ready for use"
            }
            
    except Exception as e:
        logger.error(f"Error testing duplicate system: {str(e)}")
        return {
            "message": "Duplicate detection system error",
            "error": str(e),
            "status": "❌ Needs attention"
        }
        
@router.post("/{invoice_id}/export-to-pos")
async def export_invoice_to_pos(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Export invoice products to POS using configured integration"""
    try:
        invoice_uuid = validate_uuid(invoice_id)
        
        async with AsyncSessionFactory() as session:
            # Get tenant configuration
            tenant_query = select(Tenant).where(Tenant.tenant_id == tenant_id)
            tenant_result = await session.execute(tenant_query)
            tenant = tenant_result.scalar_one_or_none()
            
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")
            
            # Get products from confirmed invoice
            products_query = select(Product).where(Product.tenant_id == tenant_id)
            products_result = await session.execute(products_query)
            products = products_result.scalars().all()
            
            # Convert to dict format
            products_data = []
            for product in products:
                products_data.append({
                    "product_code": product.product_code,
                    "description": product.description,
                    "current_stock": float(product.current_stock or 0),
                    "last_purchase_price": float(product.last_purchase_price or 0),
                    "sale_price": 0,  # TODO: get from pricing
                    "category": "GENERAL"
                })
            
            # Create integration using factory
            integration_config = tenant.integration_config or {}
            integration = IntegrationFactory.create_integration(integration_config)
            
            # Export to POS
            result = await integration.export_inventory(products_data)
            
            return {
                "invoice_id": invoice_id,
                "pos_system": integration_config.get("pos_system", "generic"),
                "integration_type": integration_config.get("integration_type", "csv_manual"),
                "products_count": len(products_data),
                "export_result": result
            }
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error exporting to POS: {str(e)}")
        raise HTTPException(status_code=500, detail="Error exporting to POS")

@router.get("/integration-status")
async def get_integration_status(
    tenant_id: str = Depends(get_tenant_id)
):
    """Get current integration configuration and status"""
    try:
        async with AsyncSessionFactory() as session:
            # Get tenant
            tenant_query = select(Tenant).where(Tenant.tenant_id == tenant_id)
            tenant_result = await session.execute(tenant_query)
            tenant = tenant_result.scalar_one_or_none()
            
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")
            
            integration_config = tenant.integration_config or {}
            
            # Create integration to get status
            integration = IntegrationFactory.create_integration(integration_config)
            status = integration.get_status()
            
            return {
                "tenant_id": tenant_id,
                "current_config": integration_config,
                "status": status,
                "supported_systems": IntegrationFactory.get_supported_systems()
            }
            
    except Exception as e:
        logger.error(f"Error getting integration status: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting integration status")

@router.post("/configure-integration")
async def configure_integration(
    config_data: Dict[str, Any],
    tenant_id: str = Depends(get_tenant_id)
):
    """Configure POS integration for tenant"""
    try:
        # Validate configuration
        validation = IntegrationFactory.validate_config(config_data)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=validation["error"])
        
        async with AsyncSessionFactory() as session:
            # Get tenant
            tenant_query = select(Tenant).where(Tenant.tenant_id == tenant_id)
            tenant_result = await session.execute(tenant_query)
            tenant = tenant_result.scalar_one_or_none()
            
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")
            
            # Update configuration
            tenant.integration_config = config_data
            await session.commit()
            
            return {
                "message": "Integration configuration updated successfully",
                "config": config_data
            }
            
    except Exception as e:
        logger.error(f"Error configuring integration: {str(e)}")
        raise HTTPException(status_code=500, detail="Error configuring integration")
    
# Agregar este endpoint simple al final de apps/api/src/api/routers/invoices.py

@router.get("/test-factory")
async def test_factory(tenant_id: str = Depends(get_tenant_id)):
    """Test endpoint para verificar factory functionality"""
    try:
        async with AsyncSessionFactory() as session:
            # Get tenant with error handling
            tenant_query = select(Tenant).where(Tenant.tenant_id == tenant_id)
            tenant_result = await session.execute(tenant_query)
            tenant = tenant_result.scalar_one_or_none()
            
            if not tenant:
                return {"error": f"Tenant {tenant_id} not found"}
            
            # Get products with error handling
            products_query = select(Product).where(Product.tenant_id == tenant_id)
            products_result = await session.execute(products_query)
            products = products_result.scalars().all()
            
            # Convert products to dict
            products_data = []
            for product in products:
                try:
                    products_data.append({
                        "product_code": str(product.product_code or ""),
                        "description": str(product.description or ""),
                        "current_stock": float(product.current_stock or 0),
                        "last_purchase_price": float(product.last_purchase_price or 0),
                        "sale_price": 0,
                        "category": "GENERAL"
                    })
                except Exception as product_error:
                    return {"error": f"Product conversion error: {str(product_error)}"}
            
            # Test integration config
            integration_config = tenant.integration_config or {}
            
            # Create integration
            try:
                integration = IntegrationFactory.create_integration(integration_config)
            except Exception as factory_error:
                return {"error": f"Factory error: {str(factory_error)}"}
            
            # Test export
            try:
                result = await integration.export_inventory(products_data)
                
                return {
                    "success": True,
                    "tenant_id": tenant_id,
                    "products_count": len(products_data),
                    "integration_config": integration_config,
                    "export_result": result
                }
            except Exception as export_error:
                return {"error": f"Export error: {str(export_error)}"}
            
    except Exception as e:
        import traceback
        return {
            "error": f"General error: {str(e)}",
            "traceback": traceback.format_exc()
        }