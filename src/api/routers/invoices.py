"""
Invoice processing endpoints with multi-tenant support - FIXED
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from typing import List, Optional
import uuid
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

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

@router.get("/{invoice_id}/pricing", response_model=PricingDataResponse)
async def get_invoice_pricing_data(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get invoice data ready for manual pricing"""
    try:
        # Validate UUID format
        invoice_uuid = validate_uuid(invoice_id)
        
        # TODO: Replace with real database query
        # For now, return comprehensive mock data
        
        # Create mock line items with realistic data
        mock_line_items = [
            InvoiceLineItemPricing(
                id=uuid.uuid4(),
                line_item_id=uuid.uuid4(),
                product_code="MED-320",
                description="Medias Deportivas REF 320",
                quantity=Decimal('24'),
                unit_price=Decimal('6200'),
                subtotal=Decimal('148800'),
                sale_price=None,
                markup_percentage=None,
                profit_margin=None,
                is_priced=False
            ),
            InvoiceLineItemPricing(
                id=uuid.uuid4(),
                line_item_id=uuid.uuid4(),
                product_code="ZAP-DEP-45",
                description="Zapatos Deportivos Talla 45",
                quantity=Decimal('12'),
                unit_price=Decimal('28000'),
                subtotal=Decimal('336000'),
                sale_price=None,
                markup_percentage=None,
                profit_margin=None,
                is_priced=False
            ),
            InvoiceLineItemPricing(
                id=uuid.uuid4(),
                line_item_id=uuid.uuid4(),
                product_code="CAM-COT-M",
                description="Camiseta Algodón Talla M",
                quantity=Decimal('36'),
                unit_price=Decimal('12500'),
                subtotal=Decimal('450000'),
                sale_price=None,
                markup_percentage=None,
                profit_margin=None,
                is_priced=False
            )
        ]
        
        # Calculate summary
        summary = calculate_pricing_summary(mock_line_items)
        
        response = PricingDataResponse(
            invoice_id=invoice_uuid,
            invoice_number="INV-2024-001",
            supplier_name="Importadora El Éxito S.A.S",
            issue_date="2024-07-20",
            total_amount=summary.total_cost,
            pricing_status=PricingStatus.PENDING,
            line_items=mock_line_items,
            summary=summary
        )
        
        return response
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting pricing data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pricing data: {str(e)}"
        )

@router.post("/{invoice_id}/pricing")
async def set_invoice_pricing(
    invoice_id: str,
    pricing_data: PricingUpdateRequest,
    tenant_id: str = Depends(get_tenant_id)
):
    """Set manual pricing for invoice line items"""
    try:
        # Validate UUID format
        invoice_uuid = validate_uuid(invoice_id)
        
        # Process each pricing update
        pricing_updates = []
        for item_update in pricing_data.line_items:
            # Mock: Get current item data (in real implementation, get from DB)
            mock_cost_price = Decimal('6200')  # This would come from DB
            
            # Calculate metrics
            markup = calculate_markup_percentage(mock_cost_price, item_update.sale_price)
            profit_margin = calculate_profit_margin(mock_cost_price, item_update.sale_price)
            
            pricing_update = {
                "line_item_id": str(item_update.line_item_id),
                "sale_price": float(item_update.sale_price),
                "markup_percentage": float(markup),
                "profit_margin": float(profit_margin),
                "is_priced": True,
                "cost_price": float(mock_cost_price)
            }
            pricing_updates.append(pricing_update)
        
        # Mock summary calculation
        total_cost = Decimal('6200') * len(pricing_data.line_items)
        total_sale_value = sum(item.sale_price for item in pricing_data.line_items)
        total_profit = total_sale_value - total_cost
        avg_markup = (total_profit / total_cost * 100) if total_cost > 0 else Decimal('0')
        
        summary = PricingSummary(
            total_items=len(pricing_data.line_items),
            priced_items=len(pricing_data.line_items),
            pending_items=0,
            total_cost=total_cost,
            total_sale_value=total_sale_value,
            total_profit=total_profit,
            average_markup=round(avg_markup, 2)
        )
        
        return {
            "message": "Pricing updated successfully",
            "invoice_id": str(invoice_uuid),
            "updates": pricing_updates,
            "summary": summary.dict()
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Error setting pricing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set pricing: {str(e)}"
        )

@router.post("/{invoice_id}/confirm-pricing", response_model=Dict[str, Any])
async def confirm_invoice_pricing(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Confirm pricing and update inventory"""
    try:
        # Validate UUID format
        invoice_uuid = validate_uuid(invoice_id)
        
        # Mock inventory updates
        inventory_updates = [
            {
                "product_code": "MED-320",
                "description": "Medias Deportivas REF 320",
                "quantity_added": 24,
                "cost_price": 6200,
                "sale_price": 12000,
                "total_value_added": 148800,
                "location": "warehouse_a"
            },
            {
                "product_code": "ZAP-DEP-45", 
                "description": "Zapatos Deportivos Talla 45",
                "quantity_added": 12,
                "cost_price": 28000,
                "sale_price": 55000,
                "total_value_added": 336000,
                "location": "warehouse_a"
            }
        ]
        
        # Mock summary
        summary = PricingSummary(
            total_items=2,
            priced_items=2,
            pending_items=0,
            total_cost=Decimal('484800'),
            total_sale_value=Decimal('948000'),
            total_profit=Decimal('463200'),
            average_markup=Decimal('95.53')
        )
        
        response = PricingConfirmationResponse(
            invoice_id=invoice_uuid,
            pricing_status=PricingStatus.CONFIRMED,
            total_items_priced=2,
            inventory_updates=inventory_updates,
            summary=summary
        )
        
        return {
            "message": "Pricing confirmed and inventory updated successfully",
            "invoice_id": str(invoice_uuid),
            "result": response.dict()
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
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

# Agrega esto a tu invoices.py

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
