"""
AWS Textract service for Colombian invoice processing
"""
import boto3
import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, date

from ..config.settings import settings

logger = logging.getLogger(__name__)

class TextractService:
    """Service for AWS Textract document analysis"""
    
    def __init__(self):
        self.textract_client = boto3.client('textract', region_name=settings.aws_region)
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)
    
    async def analyze_invoice(self, s3_bucket: str, s3_key: str) -> Dict[str, Any]:
        """
        Analyze invoice using AWS Textract
        
        Args:
            s3_bucket: S3 bucket name
            s3_key: S3 object key
            
        Returns:
            Structured invoice data
        """
        try:
            logger.info(f"Starting Textract analysis for {s3_key}")
            
            # Call Textract
            response = self.textract_client.analyze_document(
                Document={
                    'S3Object': {
                        'Bucket': s3_bucket,
                        'Name': s3_key
                    }
                },
                FeatureTypes=['TABLES', 'FORMS']  # Extract tables and key-value pairs
            )
            
            logger.info(f"Textract analysis completed for {s3_key}")
            
            # Extract structured data
            extracted_data = self._extract_invoice_data(response)
            
            return {
                'textract_response': response,
                'extracted_data': extracted_data,
                'confidence_score': self._calculate_confidence(response)
            }
            
        except Exception as e:
            logger.error(f"Textract analysis failed for {s3_key}: {str(e)}")
            raise
    
    def _extract_invoice_data(self, textract_response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured data from Textract response"""
        blocks = textract_response.get('Blocks', [])
        
        # Get all text lines
        lines = self._get_text_lines(blocks)
        full_text = '\n'.join(lines)
        
        # Extract key-value pairs
        key_values = self._extract_key_values(blocks)
        
        # Extract tables
        tables = self._extract_tables(blocks)
        
        # Parse Colombian invoice fields
        invoice_data = {
            'invoice_number': self._extract_invoice_number(lines, key_values),
            'issue_date': self._extract_date(lines, key_values, 'fecha'),
            'due_date': self._extract_date(lines, key_values, 'vencimiento'),
            'supplier': self._extract_supplier_info(lines, key_values),
            'customer': self._extract_customer_info(lines, key_values),
            'line_items': self._extract_line_items(tables, lines),
            'totals': self._extract_totals(lines, key_values),
            'payment_info': self._extract_payment_info(lines, key_values),
            'full_text': full_text,
            'raw_tables': tables,
            'raw_key_values': key_values
        }
        
        return invoice_data
    
    def _get_text_lines(self, blocks: List[Dict]) -> List[str]:
        """Extract all text lines from blocks"""
        lines = []
        for block in blocks:
            if block.get('BlockType') == 'LINE':
                text = block.get('Text', '').strip()
                if text:
                    lines.append(text)
        return lines
    
    def _extract_key_values(self, blocks: List[Dict]) -> Dict[str, str]:
        """Extract key-value pairs from forms"""
        key_values = {}
        
        # Map block IDs to blocks for relationship lookup
        block_map = {block['Id']: block for block in blocks}
        
        for block in blocks:
            if block.get('BlockType') == 'KEY_VALUE_SET':
                entity_types = block.get('EntityTypes', [])
                
                if 'KEY' in entity_types:
                    # Find the corresponding VALUE
                    relationships = block.get('Relationships', [])
                    key_text = self._get_text_from_block(block, block_map)
                    
                    for relationship in relationships:
                        if relationship.get('Type') == 'VALUE':
                            value_ids = relationship.get('Ids', [])
                            for value_id in value_ids:
                                value_block = block_map.get(value_id)
                                if value_block:
                                    value_text = self._get_text_from_block(value_block, block_map)
                                    if key_text and value_text:
                                        key_values[key_text.lower()] = value_text
        
        return key_values
    
    def _get_text_from_block(self, block: Dict, block_map: Dict) -> str:
        """Get text content from a block"""
        text_parts = []
        relationships = block.get('Relationships', [])
        
        for relationship in relationships:
            if relationship.get('Type') == 'CHILD':
                child_ids = relationship.get('Ids', [])
                for child_id in child_ids:
                    child_block = block_map.get(child_id)
                    if child_block and child_block.get('BlockType') == 'WORD':
                        text_parts.append(child_block.get('Text', ''))
        
        return ' '.join(text_parts)
    
    def _extract_tables(self, blocks: List[Dict]) -> List[Dict]:
        """Extract table data"""
        tables = []
        block_map = {block['Id']: block for block in blocks}
        
        for block in blocks:
            if block.get('BlockType') == 'TABLE':
                table_data = self._parse_table(block, block_map)
                if table_data:
                    tables.append(table_data)
        
        return tables
    
    def _parse_table(self, table_block: Dict, block_map: Dict) -> Dict:
        """Parse individual table"""
        rows = {}
        
        relationships = table_block.get('Relationships', [])
        for relationship in relationships:
            if relationship.get('Type') == 'CHILD':
                cell_ids = relationship.get('Ids', [])
                
                for cell_id in cell_ids:
                    cell_block = block_map.get(cell_id)
                    if cell_block and cell_block.get('BlockType') == 'CELL':
                        row_index = cell_block.get('RowIndex', 0)
                        col_index = cell_block.get('ColumnIndex', 0)
                        cell_text = self._get_text_from_block(cell_block, block_map)
                        
                        if row_index not in rows:
                            rows[row_index] = {}
                        rows[row_index][col_index] = cell_text
        
        # Convert to list of lists
        table_rows = []
        for row_idx in sorted(rows.keys()):
            row_data = []
            row = rows[row_idx]
            for col_idx in sorted(row.keys()):
                row_data.append(row[col_idx])
            table_rows.append(row_data)
        
        return {
            'rows': table_rows,
            'row_count': len(table_rows),
            'col_count': max(len(row) for row in table_rows) if table_rows else 0
        }
    
    def _extract_invoice_number(self, lines: List[str], key_values: Dict[str, str]) -> Optional[str]:
        """Extract invoice number"""
        # Try key-values first
        for key in ['factura', 'invoice', 'numero', 'no.', '#']:
            if key in key_values:
                return key_values[key]
        
        # Try regex patterns on text lines
        patterns = [
            r'(?:FACTURA|INVOICE|No\.?|#)\s*:?\s*([A-Z0-9]+)',
            r'PMB(\d+)',  # Specific pattern from your examples
            r'(?:REF|REFERENCIA)\s*:?\s*([A-Z0-9]+)'
        ]
        
        for line in lines:
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        return None
    
    def _extract_date(self, lines: List[str], key_values: Dict[str, str], date_type: str) -> Optional[date]:
        """Extract dates (issue_date, due_date)"""
        # Common date patterns for Colombian invoices
        date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
            r'(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})'
        ]
        
        # Try key-values first
        search_keys = [date_type, f'fecha_{date_type}', 'date']
        for key in search_keys:
            if key in key_values:
                return self._parse_date_string(key_values[key])
        
        # Try text lines
        for line in lines:
            if date_type.lower() in line.lower():
                for pattern in date_patterns:
                    match = re.search(pattern, line)
                    if match:
                        return self._parse_date_string(match.group(1))
        
        return None
    
    def _parse_date_string(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        date_formats = [
            '%d/%m/%Y', '%d-%m-%Y',
            '%Y/%m/%d', '%Y-%m-%d',
            '%m/%d/%Y', '%m-%d-%Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def _extract_supplier_info(self, lines: List[str], key_values: Dict[str, str]) -> Dict[str, Any]:
        """Extract supplier information"""
        supplier = {
            'company_name': None,
            'nit': None,
            'address': None,
            'city': None,
            'department': None,
            'phone': None
        }
        
        # Look for NIT pattern
        for line in lines:
            nit_match = re.search(r'NIT\s*:?\s*([0-9-]+)', line, re.IGNORECASE)
            if nit_match:
                supplier['nit'] = nit_match.group(1)
            
            # Look for company name (usually first few lines)
            if not supplier['company_name'] and len(line) > 10 and any(word in line.upper() for word in ['LTDA', 'S.A.S', 'EMPRESA', 'COMERCIAL']):
                supplier['company_name'] = line.strip()
        
        return supplier
    
    def _extract_customer_info(self, lines: List[str], key_values: Dict[str, str]) -> Dict[str, Any]:
        """Extract customer information"""
        customer = {
            'customer_name': None,
            'customer_id': None,
            'address': None,
            'city': None,
            'department': None,
            'phone': None
        }
        
        # Look for customer patterns
        for line in lines:
            # Customer name patterns
            if 'CLIENTE' in line.upper() or 'NOMBRE' in line.upper():
                parts = line.split(':')
                if len(parts) > 1:
                    customer['customer_name'] = parts[1].strip()
            
            # Phone pattern
            phone_match = re.search(r'(\d{10})', line)
            if phone_match and not customer['phone']:
                customer['phone'] = phone_match.group(1)
        
        return customer
    
    def _extract_line_items(self, tables: List[Dict], lines: List[str]) -> List[Dict]:
        """Extract product line items from tables"""
        line_items = []
        
        # Process the largest table (likely the product table)
        if tables:
            main_table = max(tables, key=lambda t: t['row_count'])
            
            for i, row in enumerate(main_table['rows']):
                if i == 0:  # Skip header row
                    continue
                
                if len(row) >= 4:  # Need at least code, description, quantity, price
                    try:
                        item = {
                            'product_code': row[0] if len(row) > 0 else None,
                            'description': row[1] if len(row) > 1 else None,
                            'reference': row[2] if len(row) > 2 else None,
                            'quantity': self._parse_decimal(row[-3]) if len(row) > 2 else None,
                            'unit_price': self._parse_decimal(row[-2]) if len(row) > 1 else None,
                            'subtotal': self._parse_decimal(row[-1]) if len(row) > 0 else None
                        }
                        
                        # Only add if we have essential data
                        if item['description'] and item['quantity'] and item['unit_price']:
                            line_items.append(item)
                            
                    except Exception as e:
                        logger.warning(f"Error parsing line item {i}: {str(e)}")
                        continue
        
        return line_items
    
    def _extract_totals(self, lines: List[str], key_values: Dict[str, str]) -> Dict[str, Any]:
        """Extract totals and tax information"""
        totals = {
            'subtotal': None,
            'iva_rate': None,
            'iva_amount': None,
            'total': None,
            'total_items': None
        }
        
        # Look for total patterns
        for line in lines:
            # Subtotal
            if 'SUBTOTAL' in line.upper():
                subtotal_match = re.search(r'[\$]?\s*([\d,]+)', line)
                if subtotal_match:
                    totals['subtotal'] = self._parse_decimal(subtotal_match.group(1))
            
            # IVA
            if 'IVA' in line.upper():
                iva_match = re.search(r'[\$]?\s*([\d,]+)', line)
                if iva_match:
                    totals['iva_amount'] = self._parse_decimal(iva_match.group(1))
                
                # IVA rate
                rate_match = re.search(r'(\d+)%', line)
                if rate_match:
                    totals['iva_rate'] = Decimal(rate_match.group(1))
            
            # Total
            if 'TOTAL' in line.upper() and 'SUBTOTAL' not in line.upper():
                total_match = re.search(r'[\$]?\s*([\d,]+)', line)
                if total_match:
                    totals['total'] = self._parse_decimal(total_match.group(1))
        
        return totals
    
    def _extract_payment_info(self, lines: List[str], key_values: Dict[str, str]) -> Dict[str, Any]:
        """Extract payment terms and method"""
        payment_info = {
            'payment_method': None,
            'credit_days': None,
            'discount_percentage': None
        }
        
        for line in lines:
            # Credit terms
            if 'CREDITO' in line.upper():
                payment_info['payment_method'] = 'CREDITO'
                
                # Extract days
                days_match = re.search(r'(\d+)\s*DIAS?', line, re.IGNORECASE)
                if days_match:
                    payment_info['credit_days'] = int(days_match.group(1))
            
            # Discount
            if 'DESCUENTO' in line.upper() or 'DCTO' in line.upper():
                discount_match = re.search(r'(\d+)%', line)
                if discount_match:
                    payment_info['discount_percentage'] = Decimal(discount_match.group(1))
        
        return payment_info
    
    def _parse_decimal(self, value: str) -> Optional[Decimal]:
        """Parse string to Decimal, handling Colombian number format"""
        if not value:
            return None
        
        try:
            # Remove currency symbols and spaces
            cleaned = re.sub(r'[\$\s]', '', str(value))
            # Remove thousand separators (dots/commas)
            cleaned = re.sub(r'[,.](?=\d{3})', '', cleaned)
            # Replace decimal comma with dot
            cleaned = cleaned.replace(',', '.')
            
            return Decimal(cleaned)
        except Exception:
            return None
    
    def _calculate_confidence(self, textract_response: Dict[str, Any]) -> float:
        """Calculate overall confidence score"""
        blocks = textract_response.get('Blocks', [])
        confidence_scores = []
        
        for block in blocks:
            confidence = block.get('Confidence')
            if confidence:
                confidence_scores.append(confidence)
        
        if confidence_scores:
            return sum(confidence_scores) / len(confidence_scores) / 100.0
        
        return 0.0
