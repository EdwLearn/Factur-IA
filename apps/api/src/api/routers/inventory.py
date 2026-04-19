"""
Inventory management endpoints

Gestión completa de inventario incluyendo:
- Catálogo de productos
- Control de stock y movimientos
- Alertas de stock bajo
- Productos defectuosos
- Estadísticas e inventario
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import logging
import uuid

from ...database.connection import AsyncSessionFactory
from ...database.models import Product, InventoryMovement, DefectiveProduct, ProcessedInvoice
from ..deps import get_tenant_id

logger = logging.getLogger(__name__)
router = APIRouter(
    responses={
        401: {"description": "No autorizado - falta x-tenant-id"},
        403: {"description": "Prohibido - tenant no válido"},
        404: {"description": "Recurso no encontrado"},
        500: {"description": "Error interno del servidor"}
    }
)


# Pydantic models for requests and responses
class ProductBase(BaseModel):
    """Base product schema"""
    product_code: str = Field(..., description="Product code/SKU")
    description: str = Field(..., description="Product description")
    reference: Optional[str] = Field(None, description="Product reference")
    unit_measure: str = Field(default="UNIDAD", description="Unit of measure")
    category: Optional[str] = Field(None, description="Product category")
    supplier_name: Optional[str] = Field(None, description="Primary supplier name (denormalized)")
    supplier_id: Optional[str] = Field(None, description="FK to suppliers table")
    current_stock: float = Field(default=0, description="Current stock quantity")
    min_stock: float = Field(default=0, description="Minimum stock alert level")
    max_stock: Optional[float] = Field(None, description="Maximum stock level")
    sale_price: Optional[float] = Field(None, description="Current sale price")


class ProductCreate(ProductBase):
    """Schema for creating a new product"""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating a product (all fields optional)"""
    product_code: Optional[str] = None
    description: Optional[str] = None
    reference: Optional[str] = None
    unit_measure: Optional[str] = None
    category: Optional[str] = None
    supplier_name: Optional[str] = None
    current_stock: Optional[float] = None
    min_stock: Optional[float] = None
    max_stock: Optional[float] = None
    sale_price: Optional[float] = None
    last_purchase_price: Optional[float] = None


class ProductResponse(ProductBase):
    """Full product response"""
    id: str
    tenant_id: str
    quantity: int
    total_purchased: float
    total_amount: float
    last_purchase_date: Optional[date]
    last_purchase_price: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductListItem(BaseModel):
    """Product list item (simplified)"""
    id: str
    product_code: str
    description: str
    unit_measure: Optional[str]
    category: Optional[str]
    supplier_name: Optional[str]
    supplier_id: Optional[str]
    current_stock: float
    min_stock: float
    sale_price: Optional[float]
    last_purchase_price: Optional[float]
    last_purchase_date: Optional[date]
    stock_status: str  # 'ok', 'low', 'out'

    class Config:
        from_attributes = True


class InventoryMovementCreate(BaseModel):
    """Schema for creating an inventory movement"""
    product_id: str = Field(..., description="Product UUID")
    movement_type: str = Field(..., description="Movement type: purchase, sale, adjustment")
    quantity: float = Field(..., description="Quantity (positive for in, negative for out)")
    reference_price: Optional[float] = Field(None, description="Reference price for the movement")
    invoice_id: Optional[str] = Field(None, description="Related invoice UUID")
    notes: Optional[str] = Field(None, description="Additional notes")


class InventoryMovementResponse(BaseModel):
    """Inventory movement response"""
    id: str
    product_id: str
    movement_type: str
    quantity: float
    reference_price: Optional[float]
    movement_date: datetime
    invoice_id: Optional[str]
    notes: Optional[str]
    product_code: Optional[str]
    product_description: Optional[str]

    class Config:
        from_attributes = True


class DefectiveProductCreate(BaseModel):
    """Schema for reporting a defective product"""
    product_id: str = Field(..., description="Product UUID")
    quantity: float = Field(..., description="Quantity of defective items")
    reason: str = Field(..., description="Reason: damaged, returned, expired")
    notes: Optional[str] = Field(None, description="Additional notes")
    invoice_id: Optional[str] = Field(None, description="Related invoice UUID")


class DefectiveProductResponse(BaseModel):
    """Defective product response"""
    id: str
    product_id: str
    quantity: float
    reason: str
    notes: Optional[str]
    created_date: datetime
    invoice_id: Optional[str]
    product_code: Optional[str]
    product_description: Optional[str]

    class Config:
        from_attributes = True


class LowStockAlert(BaseModel):
    """Low stock alert"""
    id: str
    product_code: str
    description: str
    current_stock: float
    min_stock: float
    stock_percentage: float
    last_purchase_date: Optional[date]
    last_purchase_price: Optional[float]


class InventoryStats(BaseModel):
    """Inventory statistics"""
    total_products: int
    total_inventory_value: float
    low_stock_count: int
    out_of_stock_count: int
    total_movements_today: int
    total_defective_items: int


# Helper function to get database session
async def get_db() -> AsyncSession:
    """Get async database session"""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()


# Helper function to calculate stock status
def calculate_stock_status(current_stock: float, min_stock: float) -> str:
    """Calculate stock status based on current and minimum stock"""
    if current_stock <= 0:
        return "out"
    elif current_stock <= min_stock:
        return "low"
    else:
        return "ok"


# Endpoints
@router.get(
    "/products",
    response_model=List[ProductListItem],
    summary="📦 Listar Productos",
    description="Obtiene la lista de productos del catálogo con filtros y paginación",
    response_description="Lista de productos con información de stock"
)
async def list_products(
    x_tenant_id: str = Depends(get_tenant_id),
    limit: int = Query(default=100, le=500, description="Maximum number of products to return"),
    offset: int = Query(default=0, ge=0, description="Number of products to skip"),
    search: Optional[str] = Query(None, description="Search by code or description"),
    stock_status: Optional[str] = Query(None, description="Filter by stock status: ok, low, out"),
    db: AsyncSession = Depends(get_db)
):
    """
    Listar todos los productos del inventario

    Retorna una lista paginada de productos con información de stock.

    **Filtros disponibles:**
    - `search`: Buscar por código o descripción
    - `stock_status`: Filtrar por estado (ok, low, out)

    **Paginación:**
    - `limit`: Máximo de productos a retornar (default: 100, max: 500)
    - `offset`: Número de productos a saltar

    **Estados de stock:**
    - `ok`: Stock por encima del mínimo
    - `low`: Stock en o por debajo del mínimo
    - `out`: Sin stock (0 unidades)
    """
    try:
        # Build query
        query = select(Product).where(Product.tenant_id == x_tenant_id)

        # Apply search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Product.product_code.ilike(search_pattern),
                    Product.description.ilike(search_pattern)
                )
            )

        # Apply stock status filter
        if stock_status == "out":
            query = query.where(Product.current_stock <= 0)
        elif stock_status == "low":
            query = query.where(
                and_(
                    Product.current_stock > 0,
                    Product.current_stock <= Product.min_stock
                )
            )
        elif stock_status == "ok":
            query = query.where(Product.current_stock > Product.min_stock)

        # Order by product code
        query = query.order_by(Product.product_code).offset(offset).limit(limit)

        result = await db.execute(query)
        products = result.scalars().all()

        # Build response with calculated stock status
        response = []
        for product in products:
            response.append(ProductListItem(
                id=str(product.id),
                product_code=product.product_code,
                description=product.description,
                unit_measure=product.unit_measure,
                category=product.category,
                supplier_name=product.supplier_name,
                supplier_id=str(product.supplier_id) if product.supplier_id else None,
                current_stock=float(product.current_stock),
                min_stock=float(product.min_stock),
                sale_price=float(product.sale_price) if product.sale_price else None,
                last_purchase_price=float(product.last_purchase_price) if product.last_purchase_price else None,
                last_purchase_date=product.last_purchase_date,
                stock_status=calculate_stock_status(
                    float(product.current_stock),
                    float(product.min_stock)
                )
            ))

        return response

    except Exception as e:
        logger.error(f"Error listing products for tenant {x_tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing products: {str(e)}")


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    x_tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific product
    """
    try:
        query = select(Product).where(
            and_(
                Product.id == uuid.UUID(product_id),
                Product.tenant_id == x_tenant_id
            )
        )

        result = await db.execute(query)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        return ProductResponse(
            id=str(product.id),
            tenant_id=product.tenant_id,
            product_code=product.product_code,
            description=product.description,
            reference=product.reference,
            unit_measure=product.unit_measure,
            current_stock=float(product.current_stock),
            min_stock=float(product.min_stock),
            max_stock=float(product.max_stock) if product.max_stock else None,
            quantity=product.quantity,
            sale_price=float(product.sale_price) if product.sale_price else None,
            total_purchased=float(product.total_purchased),
            total_amount=float(product.total_amount),
            last_purchase_date=product.last_purchase_date,
            last_purchase_price=float(product.last_purchase_price) if product.last_purchase_price else None,
            created_at=product.created_at,
            updated_at=product.updated_at
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting product: {str(e)}")


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=201,
    summary="➕ Crear Producto",
    description="Crea un nuevo producto en el catálogo de inventario",
    response_description="Producto creado exitosamente"
)
async def create_product(
    product: ProductCreate,
    x_tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Crear un nuevo producto en el inventario

    Crea un producto con la información proporcionada. El código del producto
    debe ser único dentro del tenant.

    **Campos requeridos:**
    - `product_code`: Código único del producto (SKU)
    - `description`: Descripción del producto

    **Campos opcionales:**
    - `reference`: Referencia del producto
    - `unit_measure`: Unidad de medida (default: UNIDAD)
    - `current_stock`: Stock actual (default: 0)
    - `min_stock`: Stock mínimo para alertas (default: 0)
    - `max_stock`: Stock máximo
    - `sale_price`: Precio de venta

    **Validaciones:**
    - El código del producto debe ser único por tenant
    - Los valores numéricos deben ser >= 0

    **Ejemplo:**
    ```json
    {
      "product_code": "PROD001",
      "description": "Laptop HP ProBook 450",
      "current_stock": 10,
      "min_stock": 5,
      "sale_price": 2500000
    }
    ```
    """
    try:
        # Check if product code already exists for this tenant
        existing_query = select(Product).where(
            and_(
                Product.tenant_id == x_tenant_id,
                Product.product_code == product.product_code
            )
        )
        result = await db.execute(existing_query)
        existing_product = result.scalar_one_or_none()

        if existing_product:
            raise HTTPException(
                status_code=400,
                detail=f"Product with code {product.product_code} already exists"
            )

        # Create new product
        new_product = Product(
            id=uuid.uuid4(),
            tenant_id=x_tenant_id,
            product_code=product.product_code,
            description=product.description,
            reference=product.reference,
            unit_measure=product.unit_measure,
            current_stock=Decimal(str(product.current_stock)),
            min_stock=Decimal(str(product.min_stock)),
            max_stock=Decimal(str(product.max_stock)) if product.max_stock else None,
            sale_price=Decimal(str(product.sale_price)) if product.sale_price else None,
            quantity=int(product.current_stock),
            total_purchased=Decimal("0"),
            total_amount=Decimal("0"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(new_product)
        await db.commit()
        await db.refresh(new_product)

        return ProductResponse(
            id=str(new_product.id),
            tenant_id=new_product.tenant_id,
            product_code=new_product.product_code,
            description=new_product.description,
            reference=new_product.reference,
            unit_measure=new_product.unit_measure,
            current_stock=float(new_product.current_stock),
            min_stock=float(new_product.min_stock),
            max_stock=float(new_product.max_stock) if new_product.max_stock else None,
            quantity=new_product.quantity,
            sale_price=float(new_product.sale_price) if new_product.sale_price else None,
            total_purchased=float(new_product.total_purchased),
            total_amount=float(new_product.total_amount),
            last_purchase_date=new_product.last_purchase_date,
            last_purchase_price=float(new_product.last_purchase_price) if new_product.last_purchase_price else None,
            created_at=new_product.created_at,
            updated_at=new_product.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating product: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating product: {str(e)}")


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_update: ProductUpdate,
    x_tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing product
    """
    try:
        # Get existing product
        query = select(Product).where(
            and_(
                Product.id == uuid.UUID(product_id),
                Product.tenant_id == x_tenant_id
            )
        )

        result = await db.execute(query)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Update fields if provided
        if product_update.product_code is not None:
            # Check if new code conflicts with existing product
            existing_query = select(Product).where(
                and_(
                    Product.tenant_id == x_tenant_id,
                    Product.product_code == product_update.product_code,
                    Product.id != uuid.UUID(product_id)
                )
            )
            result = await db.execute(existing_query)
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail=f"Product with code {product_update.product_code} already exists"
                )
            product.product_code = product_update.product_code

        if product_update.description is not None:
            product.description = product_update.description
        if product_update.reference is not None:
            product.reference = product_update.reference
        if product_update.unit_measure is not None:
            product.unit_measure = product_update.unit_measure
        if product_update.current_stock is not None:
            product.current_stock = Decimal(str(product_update.current_stock))
            product.quantity = int(product_update.current_stock)
        if product_update.min_stock is not None:
            product.min_stock = Decimal(str(product_update.min_stock))
        if product_update.max_stock is not None:
            product.max_stock = Decimal(str(product_update.max_stock))
        if product_update.sale_price is not None:
            product.sale_price = Decimal(str(product_update.sale_price))
        if product_update.category is not None:
            product.category = product_update.category
        if product_update.supplier_name is not None:
            product.supplier_name = product_update.supplier_name
        if product_update.last_purchase_price is not None:
            product.last_purchase_price = Decimal(str(product_update.last_purchase_price))

        product.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(product)

        return ProductResponse(
            id=str(product.id),
            tenant_id=product.tenant_id,
            product_code=product.product_code,
            description=product.description,
            reference=product.reference,
            unit_measure=product.unit_measure,
            current_stock=float(product.current_stock),
            min_stock=float(product.min_stock),
            max_stock=float(product.max_stock) if product.max_stock else None,
            quantity=product.quantity,
            sale_price=float(product.sale_price) if product.sale_price else None,
            total_purchased=float(product.total_purchased),
            total_amount=float(product.total_amount),
            last_purchase_date=product.last_purchase_date,
            last_purchase_price=float(product.last_purchase_price) if product.last_purchase_price else None,
            created_at=product.created_at,
            updated_at=product.updated_at
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating product {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating product: {str(e)}")


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    x_tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a product from inventory
    """
    try:
        # Get product
        query = select(Product).where(
            and_(
                Product.id == uuid.UUID(product_id),
                Product.tenant_id == x_tenant_id
            )
        )

        result = await db.execute(query)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        await db.delete(product)
        await db.commit()

        return {"message": "Product deleted successfully", "product_id": product_id}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting product {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting product: {str(e)}")


@router.get("/movements", response_model=List[InventoryMovementResponse])
async def list_movements(
    x_tenant_id: str = Depends(get_tenant_id),
    limit: int = Query(default=100, le=500, description="Maximum number of movements to return"),
    offset: int = Query(default=0, ge=0, description="Number of movements to skip"),
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    movement_type: Optional[str] = Query(None, description="Filter by movement type"),
    db: AsyncSession = Depends(get_db)
):
    """
    List inventory movements with filters
    """
    try:
        # Build query - join with Product to verify tenant
        query = (
            select(InventoryMovement, Product)
            .join(Product, InventoryMovement.product_id == Product.id)
            .where(Product.tenant_id == x_tenant_id)
        )

        # Apply filters
        if product_id:
            query = query.where(InventoryMovement.product_id == uuid.UUID(product_id))
        if movement_type:
            query = query.where(InventoryMovement.movement_type == movement_type)

        # Order by date descending
        query = query.order_by(desc(InventoryMovement.movement_date)).offset(offset).limit(limit)

        result = await db.execute(query)
        movements_with_products = result.all()

        # Build response
        response = []
        for movement, product in movements_with_products:
            response.append(InventoryMovementResponse(
                id=str(movement.id),
                product_id=str(movement.product_id),
                movement_type=movement.movement_type,
                quantity=float(movement.quantity),
                reference_price=float(movement.reference_price) if movement.reference_price else None,
                movement_date=movement.movement_date,
                invoice_id=str(movement.invoice_id) if movement.invoice_id else None,
                notes=movement.notes,
                product_code=product.product_code,
                product_description=product.description
            ))

        return response

    except Exception as e:
        logger.error(f"Error listing movements: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing movements: {str(e)}")


@router.post(
    "/movements",
    response_model=InventoryMovementResponse,
    status_code=201,
    summary="📝 Registrar Movimiento",
    description="Crea un movimiento de inventario y actualiza el stock del producto",
    response_description="Movimiento registrado y stock actualizado"
)
async def create_movement(
    movement: InventoryMovementCreate,
    x_tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Registrar un movimiento de inventario

    Crea un nuevo movimiento y actualiza automáticamente el stock del producto.

    **Tipos de movimiento:**
    - `purchase`: Compra/entrada de mercancía (suma al stock)
    - `sale`: Venta/salida de mercancía (resta del stock)
    - `adjustment`: Ajuste de inventario (puede sumar o restar)

    **Campos requeridos:**
    - `product_id`: UUID del producto
    - `movement_type`: Tipo de movimiento (purchase, sale, adjustment)
    - `quantity`: Cantidad (positiva para entrada, negativa para salida)

    **Campos opcionales:**
    - `reference_price`: Precio de referencia de la transacción
    - `invoice_id`: UUID de la factura relacionada
    - `notes`: Notas adicionales

    **Ejemplo:**
    ```json
    {
      "product_id": "123e4567-e89b-12d3-a456-426614174000",
      "movement_type": "purchase",
      "quantity": 20,
      "reference_price": 120000,
      "notes": "Reabastecimiento de stock"
    }
    ```

    **Nota:** El stock del producto se actualiza automáticamente.
    """
    try:
        # Verify product exists and belongs to tenant
        product_query = select(Product).where(
            and_(
                Product.id == uuid.UUID(movement.product_id),
                Product.tenant_id == x_tenant_id
            )
        )
        result = await db.execute(product_query)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Validate movement type
        if movement.movement_type not in ['purchase', 'sale', 'adjustment']:
            raise HTTPException(
                status_code=400,
                detail="Invalid movement type. Must be: purchase, sale, or adjustment"
            )

        # Create movement
        new_movement = InventoryMovement(
            id=uuid.uuid4(),
            product_id=uuid.UUID(movement.product_id),
            movement_type=movement.movement_type,
            quantity=Decimal(str(movement.quantity)),
            reference_price=Decimal(str(movement.reference_price)) if movement.reference_price else None,
            movement_date=datetime.utcnow(),
            invoice_id=uuid.UUID(movement.invoice_id) if movement.invoice_id else None,
            notes=movement.notes
        )

        # Update product stock
        product.current_stock += Decimal(str(movement.quantity))
        product.quantity = int(product.current_stock)
        product.updated_at = datetime.utcnow()

        db.add(new_movement)
        await db.commit()
        await db.refresh(new_movement)

        return InventoryMovementResponse(
            id=str(new_movement.id),
            product_id=str(new_movement.product_id),
            movement_type=new_movement.movement_type,
            quantity=float(new_movement.quantity),
            reference_price=float(new_movement.reference_price) if new_movement.reference_price else None,
            movement_date=new_movement.movement_date,
            invoice_id=str(new_movement.invoice_id) if new_movement.invoice_id else None,
            notes=new_movement.notes,
            product_code=product.product_code,
            product_description=product.description
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating movement: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating movement: {str(e)}")


@router.get(
    "/low-stock",
    response_model=List[LowStockAlert],
    summary="⚠️ Alertas de Stock Bajo",
    description="Obtiene productos con stock por debajo del nivel mínimo",
    response_description="Lista de productos con stock bajo"
)
async def get_low_stock_alerts(
    x_tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener alertas de stock bajo

    Retorna todos los productos donde el stock actual está en o por debajo
    del nivel mínimo configurado (pero mayor a 0).

    **Criterio de alerta:**
    - `current_stock <= min_stock` AND `current_stock > 0`

    **Información retornada:**
    - Código y descripción del producto
    - Stock actual vs stock mínimo
    - Porcentaje de stock (actual/mínimo * 100)
    - Última fecha y precio de compra

    **Ordenamiento:**
    - De menor a mayor stock actual

    Útil para:
    - Reabastecimiento proactivo
    - Evitar quiebres de stock
    - Planning de compras
    """
    try:
        query = select(Product).where(
            and_(
                Product.tenant_id == x_tenant_id,
                Product.current_stock <= Product.min_stock,
                Product.current_stock > 0
            )
        ).order_by(Product.current_stock)

        result = await db.execute(query)
        products = result.scalars().all()

        response = []
        for product in products:
            stock_percentage = (float(product.current_stock) / float(product.min_stock) * 100) if float(product.min_stock) > 0 else 0
            response.append(LowStockAlert(
                id=str(product.id),
                product_code=product.product_code,
                description=product.description,
                current_stock=float(product.current_stock),
                min_stock=float(product.min_stock),
                stock_percentage=round(stock_percentage, 2),
                last_purchase_date=product.last_purchase_date,
                last_purchase_price=float(product.last_purchase_price) if product.last_purchase_price else None
            ))

        return response

    except Exception as e:
        logger.error(f"Error getting low stock alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting low stock alerts: {str(e)}")


@router.get("/defective", response_model=List[DefectiveProductResponse])
async def list_defective_products(
    x_tenant_id: str = Depends(get_tenant_id),
    limit: int = Query(default=100, le=500, description="Maximum number to return"),
    offset: int = Query(default=0, ge=0, description="Number to skip"),
    db: AsyncSession = Depends(get_db)
):
    """
    List defective products
    """
    try:
        query = (
            select(DefectiveProduct, Product)
            .join(Product, DefectiveProduct.product_id == Product.id)
            .where(Product.tenant_id == x_tenant_id)
            .order_by(desc(DefectiveProduct.created_date))
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(query)
        defective_with_products = result.all()

        response = []
        for defective, product in defective_with_products:
            response.append(DefectiveProductResponse(
                id=str(defective.id),
                product_id=str(defective.product_id),
                quantity=float(defective.quantity),
                reason=defective.reason,
                notes=defective.notes,
                created_date=defective.created_date,
                invoice_id=str(defective.invoice_id) if defective.invoice_id else None,
                product_code=product.product_code,
                product_description=product.description
            ))

        return response

    except Exception as e:
        logger.error(f"Error listing defective products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing defective products: {str(e)}")


@router.post("/defective", response_model=DefectiveProductResponse)
async def report_defective_product(
    defective: DefectiveProductCreate,
    x_tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Report a defective product
    """
    try:
        # Verify product exists and belongs to tenant
        product_query = select(Product).where(
            and_(
                Product.id == uuid.UUID(defective.product_id),
                Product.tenant_id == x_tenant_id
            )
        )
        result = await db.execute(product_query)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Validate reason
        if defective.reason not in ['damaged', 'returned', 'expired']:
            raise HTTPException(
                status_code=400,
                detail="Invalid reason. Must be: damaged, returned, or expired"
            )

        # Create defective record
        new_defective = DefectiveProduct(
            id=uuid.uuid4(),
            product_id=uuid.UUID(defective.product_id),
            quantity=Decimal(str(defective.quantity)),
            reason=defective.reason,
            notes=defective.notes,
            created_date=datetime.utcnow(),
            invoice_id=uuid.UUID(defective.invoice_id) if defective.invoice_id else None
        )

        db.add(new_defective)
        await db.commit()
        await db.refresh(new_defective)

        return DefectiveProductResponse(
            id=str(new_defective.id),
            product_id=str(new_defective.product_id),
            quantity=float(new_defective.quantity),
            reason=new_defective.reason,
            notes=new_defective.notes,
            created_date=new_defective.created_date,
            invoice_id=str(new_defective.invoice_id) if new_defective.invoice_id else None,
            product_code=product.product_code,
            product_description=product.description
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error reporting defective product: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reporting defective product: {str(e)}")


@router.get(
    "/stats",
    response_model=InventoryStats,
    summary="📊 Estadísticas de Inventario",
    description="Obtiene métricas y estadísticas generales del inventario",
    response_description="Estadísticas agregadas del inventario"
)
async def get_inventory_stats(
    x_tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener estadísticas del inventario

    Retorna métricas agregadas del inventario del tenant.

    **Métricas incluidas:**
    - `total_products`: Cantidad total de productos en el catálogo
    - `total_inventory_value`: Valor total del inventario (stock × precio_venta)
    - `low_stock_count`: Cantidad de productos con stock bajo
    - `out_of_stock_count`: Cantidad de productos sin stock
    - `total_movements_today`: Movimientos registrados hoy
    - `total_defective_items`: Total de productos defectuosos reportados

    **Cálculos:**
    - Valor de inventario solo considera productos con precio de venta
    - Stock bajo: current_stock <= min_stock AND > 0
    - Sin stock: current_stock <= 0

    Útil para:
    - Dashboard principal
    - KPIs de inventario
    - Resumen ejecutivo
    """
    try:
        # Total products
        total_query = select(func.count(Product.id)).where(Product.tenant_id == x_tenant_id)
        total_result = await db.execute(total_query)
        total_products = total_result.scalar() or 0

        # Total inventory value
        value_query = select(
            func.sum(Product.current_stock * Product.sale_price)
        ).where(
            and_(
                Product.tenant_id == x_tenant_id,
                Product.sale_price.isnot(None)
            )
        )
        value_result = await db.execute(value_query)
        total_value = float(value_result.scalar() or 0)

        # Low stock count
        low_stock_query = select(func.count(Product.id)).where(
            and_(
                Product.tenant_id == x_tenant_id,
                Product.current_stock <= Product.min_stock,
                Product.current_stock > 0
            )
        )
        low_stock_result = await db.execute(low_stock_query)
        low_stock_count = low_stock_result.scalar() or 0

        # Out of stock count
        out_stock_query = select(func.count(Product.id)).where(
            and_(
                Product.tenant_id == x_tenant_id,
                Product.current_stock <= 0
            )
        )
        out_stock_result = await db.execute(out_stock_query)
        out_stock_count = out_stock_result.scalar() or 0

        # Movements today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        movements_query = (
            select(func.count(InventoryMovement.id))
            .join(Product, InventoryMovement.product_id == Product.id)
            .where(
                and_(
                    Product.tenant_id == x_tenant_id,
                    InventoryMovement.movement_date >= today_start
                )
            )
        )
        movements_result = await db.execute(movements_query)
        movements_today = movements_result.scalar() or 0

        # Defective items count
        defective_query = (
            select(func.count(DefectiveProduct.id))
            .join(Product, DefectiveProduct.product_id == Product.id)
            .where(Product.tenant_id == x_tenant_id)
        )
        defective_result = await db.execute(defective_query)
        defective_count = defective_result.scalar() or 0

        return InventoryStats(
            total_products=total_products,
            total_inventory_value=total_value,
            low_stock_count=low_stock_count,
            out_of_stock_count=out_stock_count,
            total_movements_today=movements_today,
            total_defective_items=defective_count
        )

    except Exception as e:
        logger.error(f"Error getting inventory stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting inventory stats: {str(e)}")
