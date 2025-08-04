from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ...database.models import Product, InvoiceLineItem
import re
import uuid
from datetime import datetime

class DuplicateDetector:
    def __init__(self, similarity_threshold: float = 0.6):
        self.similarity_threshold = similarity_threshold
    
    def clean_product_description(self, description: str) -> str:
        """Clean and normalize description for comparison"""
        if not description:
            return ""
        
        # Convert to lowercase
        clean_desc = description.lower()
        
        # Remove common reference patterns and special characters
        clean_desc = re.sub(r'\b(ref|codigo|cod|sku)\b\.?\s*\w*', '', clean_desc)
        clean_desc = re.sub(r'[^\w\s]', ' ', clean_desc)
        clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
        
        return clean_desc
    
    def calculate_similarity(self, desc1: str, desc2: str) -> float:
        """Calculate similarity between two descriptions"""
        clean_desc1 = self.clean_product_description(desc1)
        clean_desc2 = self.clean_product_description(desc2)
        
        if not clean_desc1 or not clean_desc2:
            return 0.0
        
        return SequenceMatcher(None, clean_desc1, clean_desc2).ratio()
    
    async def find_similar_products(
        self, 
        product_description: str, 
        product_code: Optional[str],
        tenant_id: str,
        db: AsyncSession
    ) -> List[Dict]:
        """Find similar products in the database"""
        
        # Get all products for this tenant
        query = select(Product).where(Product.tenant_id == tenant_id)
        result = await db.execute(query)
        existing_products = result.scalars().all()
        
        similar_products = []
        
        for existing_product in existing_products:
            # Check for exact code match
            code_match = False
            if product_code and existing_product.product_code:
                if product_code.strip().lower() == existing_product.product_code.strip().lower():
                    code_match = True
            
            # Calculate description similarity
            description_similarity = self.calculate_similarity(
                product_description, 
                existing_product.description or ""
            )
            
            # Add to results if exact code match or high similarity
            if code_match or description_similarity >= self.similarity_threshold:
                similar_products.append({
                    "product_id": str(existing_product.id),
                    "product_code": existing_product.product_code,
                    "description": existing_product.description,
                    "current_stock": float(existing_product.current_stock or 0),
                    "last_purchase_price": float(existing_product.last_purchase_price or 0),
                    "similarity_score": 1.0 if code_match else description_similarity,
                    "match_type": "code_exact" if code_match else "description_similar"
                })
        
        # Sort by similarity score (descending)
        similar_products.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Return top 5 most similar products
        return similar_products[:5]
    
    async def check_invoice_duplicates(
        self, 
        invoice_line_items: List[Dict], 
        tenant_id: str,
        db: AsyncSession
    ) -> Dict:
        """Check duplicates for all line items in an invoice"""
        
        duplicate_results = []
        
        for item in invoice_line_items:
            product_code = item.get('product_code')
            description = item.get('description', '')
            
            if description:  # Only check if we have a description
                similar_products = await self.find_similar_products(
                    product_description=description,
                    product_code=product_code,
                    tenant_id=tenant_id,
                    db=db
                )
                
                duplicate_results.append({
                    "line_item": item,
                    "similar_products": similar_products,
                    "has_duplicates": len(similar_products) > 0,
                    "highest_similarity": similar_products[0]["similarity_score"] if similar_products else 0.0
                })
        
        # Calculate summary statistics
        items_with_duplicates = len([r for r in duplicate_results if r["has_duplicates"]])
        total_items = len(duplicate_results)
        
        return {
            "duplicate_check_results": duplicate_results,
            "summary": {
                "total_items": total_items,
                "items_with_potential_duplicates": items_with_duplicates,
                "items_without_duplicates": total_items - items_with_duplicates,
                "duplicate_rate": items_with_duplicates / total_items if total_items > 0 else 0.0
            }
        }
        
    async def resolve_duplicates(
        self,
        resolutions: List[Dict],
        tenant_id: str,
        db: AsyncSession
    ) -> Dict:
        """
        Resolve duplicate conflicts based on user decisions
    
        Expected resolutions format:
        [
            {
                "line_item_id": "uuid",
                "action": "merge_with_existing" | "create_new_product",
                "existing_product_id": "uuid"  # only if merging
            }
        ]
        """
        from ...database.models import InvoiceLineItem, Product
        from sqlalchemy import update
        import uuid
        from datetime import datetime
    
        results = []
    
        for resolution in resolutions:
            try:
                line_item_id = resolution.get("line_item_id")
                action = resolution.get("action")
                existing_product_id = resolution.get("existing_product_id")
            
                if not line_item_id or not action:
                    results.append({
                        "line_item_id": line_item_id,
                        "success": False,
                        "error": "Missing line_item_id or action"
                    })
                    continue
            
                # Get the line item
                line_item_query = select(InvoiceLineItem).where(
                    InvoiceLineItem.id == uuid.UUID(line_item_id)
                )
                line_item_result = await db.execute(line_item_query)
                line_item = line_item_result.scalar_one_or_none()

                if not line_item:
                    results.append({
                        "line_item_id": line_item_id,
                        "success": False,
                        "error": "Line item not found"
                    })
                    continue
    
                if action == "merge_with_existing":
                    if not existing_product_id:
                        results.append({
                            "line_item_id": line_item_id,
                            "success": False,
                            "error": "existing_product_id required for merge action"
                        })
                        continue
                
                    # Get the existing product
                    product_query = select(Product).where(
                        Product.id == uuid.UUID(existing_product_id),
                        Product.tenant_id == tenant_id
                    )

                    product_result = await db.execute(product_query)
                    existing_product = product_result.scalar_one_or_none()

                    if not existing_product:
                        results.append({
                            "line_item_id": line_item_id,
                            "success": False,
                            "error": "Existing product not found"
                        })
                        continue
                
                    # Update existing product with new purchase data
                    existing_product.current_stock = (existing_product.current_stock or 0) + line_item.quantity
                    existing_product.total_purchased = (existing_product.total_purchased or 0) + line_item.quantity
                    existing_product.total_amount = (existing_product.total_amount or 0) + line_item.subtotal
                    existing_product.last_purchase_date = datetime.now().date()
                    existing_product.last_purchase_price = line_item.unit_price
                    existing_product.updated_at = datetime.now()
                
                    # Update line item to reference the existing product
                    line_item.product_code = existing_product.product_code
                
                    results.append({
                        "line_item_id": line_item_id,
                        "success": True,
                        "action": "merged_with_existing",
                        "product_id": str(existing_product.id),
                        "new_stock": float(existing_product.current_stock)
                    })
                
                elif action == "create_new_product":
                    # Create new product from line item
                    new_product = Product(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        product_code=line_item.product_code,
                        description=line_item.description,
                        reference=line_item.reference,
                        unit_measure=line_item.unit_measure,
                        current_stock=line_item.quantity,
                        min_stock=0,
                        max_stock=None,
                        total_purchased=line_item.quantity,
                        total_amount=line_item.subtotal,
                        last_purchase_date=datetime.now().date(),
                        last_purchase_price=line_item.unit_price,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                
                    db.add(new_product)
                
                    results.append({
                        "line_item_id": line_item_id,
                        "success": True,
                        "action": "created_new_product",
                        "product_id": str(new_product.id),
                        "new_stock": float(new_product.current_stock)
                    })
                
                else:
                    results.append({
                        "line_item_id": line_item_id,
                        "success": False,
                        "error": f"Unknown action: {action}"
                    })
                
            except Exception as e:
                results.append({
                    "line_item_id": resolution.get("line_item_id"),
                    "success": False,
                    "error": f"Error processing resolution: {str(e)}"
                })
    
    
    # Agregar este método al DuplicateDetector en: apps/api/src/services/duplicate_detection/duplicate_detector.py

    async def resolve_duplicates(
        self,
        resolutions: List[Dict],
        tenant_id: str,
        db: AsyncSession
    ) -> Dict:
        """
        Resolve duplicate conflicts based on user decisions
    
        Expected resolutions format:
        [
            {
                "line_item_id": "uuid",
                "action": "merge_with_existing" | "create_new_product",
                "existing_product_id": "uuid"  # only if merging
            }
        ]
        """
    
        results = []
    
        for resolution in resolutions:
            try:
                line_item_id = resolution.get("line_item_id")
                action = resolution.get("action")
                existing_product_id = resolution.get("existing_product_id")
            
                if not line_item_id or not action:
                    results.append({
                        "line_item_id": line_item_id,
                        "success": False,
                        "error": "Missing line_item_id or action"
                    })
                    continue
            
                # Get the line item
                line_item_query = select(InvoiceLineItem).where(
                    InvoiceLineItem.id == uuid.UUID(line_item_id)
                )
                line_item_result = await db.execute(line_item_query)
                line_item = line_item_result.scalar_one_or_none()
            
                if not line_item:
                    results.append({
                        "line_item_id": line_item_id,
                        "success": False,
                        "error": "Line item not found"
                    })
                    continue
            
                if action == "merge_with_existing":
                    if not existing_product_id:
                        results.append({
                            "line_item_id": line_item_id,
                            "success": False,
                            "error": "existing_product_id required for merge action"
                        })
                        continue
                
                    # Get the existing product
                    product_query = select(Product).where(
                        Product.id == uuid.UUID(existing_product_id),
                        Product.tenant_id == tenant_id
                    )
                    product_result = await db.execute(product_query)
                    existing_product = product_result.scalar_one_or_none()

                    if not existing_product:
                        results.append({
                            "line_item_id": line_item_id,
                            "success": False,
                            "error": "Existing product not found"
                        })
                        continue
                
                    # Update existing product with new purchase data
                    existing_product.current_stock = (existing_product.current_stock or 0) + line_item.quantity
                    existing_product.total_purchased = (existing_product.total_purchased or 0) + line_item.quantity
                    existing_product.total_amount = (existing_product.total_amount or 0) + line_item.subtotal
                    existing_product.last_purchase_date = datetime.now().date()
                    existing_product.last_purchase_price = line_item.unit_price
                    existing_product.updated_at = datetime.now()
                
                    # Update line item to reference the existing product
                    line_item.product_code = existing_product.product_code
                
                    results.append({
                        "line_item_id": line_item_id,
                        "success": True,
                        "action": "merged_with_existing",
                        "product_id": str(existing_product.id),
                        "new_stock": float(existing_product.current_stock)
                    })
                
                elif action == "create_new_product":
                    # Create new product from line item
                    new_product = Product(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        product_code=line_item.product_code,
                        description=line_item.description,
                        reference=line_item.reference,
                        unit_measure=line_item.unit_measure,
                        current_stock=line_item.quantity,
                        min_stock=0,
                        max_stock=None,
                        total_purchased=line_item.quantity,
                        total_amount=line_item.subtotal,
                        last_purchase_date=datetime.now().date(),
                        last_purchase_price=line_item.unit_price,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                
                    db.add(new_product)
                
                    results.append({
                        "line_item_id": line_item_id,
                        "success": True,
                        "action": "created_new_product",
                        "product_id": str(new_product.id),
                        "new_stock": float(new_product.current_stock)
                    })

                else:
                    results.append({
                        "line_item_id": line_item_id,
                        "success": False,
                        "error": f"Unknown action: {action}"
                    })
                
            except Exception as e:
                results.append({
                    "line_item_id": resolution.get("line_item_id"),
                    "success": False,
                    "error": f"Error processing resolution: {str(e)}"
                })
    
        # Commit all changes
        try:
            await db.commit()
            successful_resolutions = len([r for r in results if r["success"]])
        
            return {
                "message": f"Processed {len(resolutions)} resolutions",
                "successful": successful_resolutions,
                "failed": len(resolutions) - successful_resolutions,
                "results": results
            }
        
        except Exception as e:
            await db.rollback()
            return {
                "message": "Failed to commit changes",
                "error": str(e),
                "results": results
            }


