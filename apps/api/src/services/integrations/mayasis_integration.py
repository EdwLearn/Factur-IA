"""
Basic Mayasis integration for CSV export
"""
import csv
import io
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class MayasisIntegration:
    """Basic Mayasis integration via CSV export"""
    
    def __init__(self):
        self.csv_headers = [
            'codigo_producto',
            'descripcion',
            'cantidad',
            'precio_costo',
            'precio_venta',
            'fecha_actualizacion'
        ]
    
    def generate_mayasis_csv(self, products_data: List[Dict]) -> str:
        """Generate CSV format compatible with Mayasis"""
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(self.csv_headers)
        
        # Write product data
        for product in products_data:
            row = [
                product.get('product_code', ''),
                product.get('description', ''),
                product.get('quantity', 0),
                product.get('cost_price', 0),
                product.get('sale_price', 0),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
            writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        logger.info(f"Generated Mayasis CSV with {len(products_data)} products")
        return csv_content
    
    async def prepare_invoice_for_mayasis(self, invoice_data: Dict) -> str:
        """Prepare confirmed invoice data for Mayasis export"""
        
        products_data = []
        
        for item in invoice_data.get('line_items', []):
            if item.get('is_priced') and item.get('sale_price'):
                products_data.append({
                    'product_code': item.get('product_code', ''),
                    'description': item.get('description', ''),
                    'quantity': item.get('quantity', 0),
                    'cost_price': item.get('unit_price', 0),
                    'sale_price': item.get('sale_price', 0)
                })
        
        return self.generate_mayasis_csv(products_data)