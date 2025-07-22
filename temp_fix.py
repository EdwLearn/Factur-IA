    async def get_pricing_data(self, invoice_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get invoice data formatted for manual pricing - SIMPLIFIED"""
        async with AsyncSessionFactory() as session:
            try:
                # Get invoice
                invoice_result = await session.execute(
                    select(ProcessedInvoice)
                    .where(ProcessedInvoice.id == uuid.UUID(invoice_id))
                    .where(ProcessedInvoice.tenant_id == tenant_id)
                )
                invoice = invoice_result.scalar_one_or_none()
                
                if not invoice:
                    logger.error(f"Invoice not found: {invoice_id}")
                    return None
                
                # Get line items separately
                line_items_result = await session.execute(
                    select(InvoiceLineItem)
                    .where(InvoiceLineItem.invoice_id == uuid.UUID(invoice_id))
                )
                line_items = line_items_result.scalars().all()
                
                logger.info(f"Found {len(line_items)} line items for invoice {invoice_id}")
                
                # Format line items for pricing
                pricing_items = []
                for item in line_items:
                    pricing_items.append({
                        "id": str(item.id),
                        "product_code": item.product_code,
                        "description": item.description,
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
                
                return {
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
                
            except Exception as e:
                logger.error(f"Error getting pricing data: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return None
