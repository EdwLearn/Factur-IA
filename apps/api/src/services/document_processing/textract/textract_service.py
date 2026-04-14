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

from ....core.config import settings
from .textract_enhancer import enhance_textract_response

logger = logging.getLogger(__name__)

class TextractService:
    """Service for AWS Textract document analysis"""
    
    def __init__(self):
        client_kwargs = {"region_name": settings.aws_region}
        if settings.aws_access_key_id:
            client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
        if settings.aws_secret_access_key:
            client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        if settings.aws_endpoint_url:
            client_kwargs["endpoint_url"] = settings.aws_endpoint_url
        self.textract_client = boto3.client("textract", **client_kwargs)
        self.s3_client = boto3.client("s3", **client_kwargs)
    
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
        raw_invoice_data = {
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
    
        '''
        try:
            enhanced_data = enhance_textract_response(raw_invoice_data)
            logger.info("✅ Applied Textract enhancements successfully")
            return enhanced_data
        except Exception as e:
            logger.warning(f"⚠️ Enhancement failed, using raw data: {str(e)}")
            return raw_invoice_data
        '''
        try:
            logger.info(f"🔧 Raw data before enhancement: {len(raw_invoice_data.get('line_items', []))} items")

            enhanced_data = enhance_textract_response(raw_invoice_data)
    
            logger.info(f"✨ Enhanced data: {len(enhanced_data.get('line_items', []))} items")
    
            # DEBUGGING: Mostrar primer item antes y después
            if raw_invoice_data.get('line_items'):
                raw_item = raw_invoice_data['line_items'][0]
                enhanced_item = enhanced_data['line_items'][0]
                logger.info(f"📊 Raw item 1: {raw_item.get('unit_measure')} - {raw_item.get('quantity')}")
                logger.info(f"📊 Enhanced item 1: {enhanced_item.get('unit_measure')} - {enhanced_item.get('quantity')}")
    
            logger.info("✅ Textract enhancer applied successfully")
            return enhanced_data
        except Exception as e:
            logger.error(f"⚠️ Enhancer failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return raw_invoice_data
        
        
    
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
    
    
    # Known header aliases for an IVA column in Colombian invoices
    _IVA_HEADER_ALIASES = {
        'iva', 'iva%', '%iva', 'tarifa iva', 'tarifa',
        'impuesto', 'imp', 'tax', 'tasa', '% iva',
    }

    # Map of invoice field → keywords that identify that column in a header row.
    # ORDER MATTERS: checked top-to-bottom per cell; first match wins.
    # 'item' removed from description — it's almost always a row-number column.
    _COLUMN_KEYWORD_MAP = {
        'description': {
            'descripcion', 'descripción', 'description', 'detalle',
            'producto', 'articulo', 'artículo', 'concepto',
        },
        'quantity': {
            'cantidad', 'cant', 'qty', 'quantity',
        },
        'unit_price': {
            # explicit price keywords
            'precio', 'price',
            # "valor/vr/vlr + unit*" — catches "Mr. Unitario", "Vlr. Unitario", etc.
            'unitario', 'valor unit', 'vr unit', 'vlr unit',
            'vr. unit', 'p. unit', 'precio unit',
            # bare "valor" when NOT followed by "total" is usually unit price
            'mr. unit', 'mr unit',
        },
        'total': {
            'total', 'valor total', 'subtotal', 'importe', 'vr total',
            'vlr total',
        },
        'unit_measure': {
            'u/m', 'unidad', 'um', 'medida',
            # 'unit' removed — too broad, matched 'unitario' before unit_price could
        },
    }

    def _detect_iva_column(self, header_row: List[str]) -> Optional[int]:
        """Return the column index of the IVA/tarifa column, or None."""
        for idx, cell in enumerate(header_row):
            if str(cell).strip().lower() in self._IVA_HEADER_ALIASES:
                return idx
        return None

    def _detect_column_mapping(self, header_row: List[str]) -> Dict[str, int]:
        """
        Read the header row and return {field: col_index} using partial keyword
        matching (containment). First match per field wins.
        """
        logger.info(f"header_row recibido: {header_row}")
        mapping: Dict[str, int] = {}
        for col_idx, cell in enumerate(header_row):
            cell_lower = str(cell).strip().lower()
            for field, keywords in self._COLUMN_KEYWORD_MAP.items():
                if field not in mapping:
                    if any(kw in cell_lower for kw in keywords):
                        mapping[field] = col_idx
                        break
        logger.info(f"col_mapping detectado: {mapping}")
        return mapping

    def _detect_iva_from_text(self, text: str) -> Optional[Decimal]:
        """
        Try to extract an IVA % from a cell or description string.
        Handles: '19%', '19 %', 'IVA19', '0%', '5%'
        """
        if not text:
            return None
        # Explicit percentage — e.g. "19%", "5 %"
        m = re.search(r'\b(0|5|19)\s*%', str(text))
        if m:
            return Decimal(m.group(1))
        # Inline IVA tag — e.g. "IVA19", "IVA 5"
        m = re.search(r'IVA\s*(0|5|19)\b', str(text), re.IGNORECASE)
        if m:
            return Decimal(m.group(1))
        return None

    # Keywords that identify a product/line-items table header
    _PRODUCT_HEADER_KEYWORDS = {
        'descripcion', 'descripción', 'description',
        'cantidad', 'qty', 'quantity',
        'valor', 'value', 'precio', 'price',
        'item', 'artículo', 'articulo', 'producto',
        'u/m', 'unidad', 'um', 'unit',
    }

    def _find_product_table(self, tables: List[Dict]) -> Optional[Dict]:
        """
        Select the table that most likely contains invoice line items using
        multi-factor scoring:
          1. Header keywords (partial match)
          2. Row count bonus
          3. Presence of long-text cells (description column)
          4. Presence of numeric cells (price/quantity columns)
        Falls back to the largest table if no table scores above 0.
        """
        best_table = None
        best_score = 0

        for table in tables:
            if not table.get('rows') or table['row_count'] < 2:
                continue  # empty or single-row table → skip

            score = 0
            header_row = table['rows'][0]

            # 1. Keywords in header — partial match (containment)
            for cell in header_row:
                cell_lower = str(cell).strip().lower()
                if any(kw in cell_lower for kw in self._PRODUCT_HEADER_KEYWORDS):
                    score += 1

            # 2. Row count bonus
            if table['row_count'] > 3:
                score += 2
            elif table['row_count'] > 2:
                score += 1

            # 3. Long-text cells in data rows → likely a description column
            has_long_text = any(
                len(str(cell).strip()) > 15
                for row in table['rows'][1:]
                for cell in row
            )
            if has_long_text:
                score += 2

            # 4. Numeric cells in data rows → price / quantity columns
            numeric_count = sum(
                1 for row in table['rows'][1:]
                for cell in row
                if self._is_numeric(str(cell).strip()) and str(cell).strip()
            )
            if numeric_count >= 3:
                score += 2
            elif numeric_count >= 1:
                score += 1

            logger.debug(
                f"Table candidate: score={score} rows={table['row_count']} "
                f"cols={table['col_count']} header={header_row}"
            )

            if score > best_score:
                best_score = score
                best_table = table

        if best_table:
            logger.info(
                f"✅ Product table selected (score={best_score}, "
                f"rows={best_table['row_count']}, cols={best_table['col_count']})"
            )
            return best_table

        logger.warning("⚠️ No product table found — fallback to largest table")
        return max(tables, key=lambda t: t['row_count']) if tables else None

    def _extract_line_items(self, tables: List[Dict], lines: List[str]) -> List[Dict]:
        """Extract product line items from tables - FIXED FOR COLOMBIAN INVOICES"""
        line_items = []

        if tables:
            main_table = self._find_product_table(tables)
            if not main_table:
                main_table = max(tables, key=lambda t: t['row_count'])
            header_row = main_table['rows'][0] if main_table['rows'] else []
            logger.info(f"RAW TABLE ROWS: {main_table['rows'][:3]}")
            iva_col_idx = self._detect_iva_column(header_row)
            col_mapping = self._detect_column_mapping(header_row)

            for i, row in enumerate(main_table['rows']):
                if i == 0:  # Skip header row
                    continue

                if len(row) >= 3:
                    try:
                        item = self._parse_colombian_invoice_line(row, i, iva_col_idx, col_mapping)
                        if item.get('description') and item.get('quantity') and item.get('unit_price'):
                            line_items.append(item)
                    except Exception as e:
                        logger.warning(f"Error parsing line item {i}: {str(e)}")
                        continue

        # If no table parsing worked, try text-based extraction
        if not line_items:
            line_items = self._extract_items_from_text_lines(lines)
            
        if not line_items:
            logger.warning("No items from tables — intentando extracción por texto")

        return line_items

    def _extract_items_from_text_lines(self, lines: List[str]) -> List[Dict]:
        """
        Fallback: extrae ítems de factura leyendo líneas de texto plano.
        Busca líneas con al menos 2 valores numéricos (cantidad + precio).
        """
        items = []
        # Patrón: línea que contiene al menos dos números (posiblemente separados por espacios)
        num_re = re.compile(r'[\d]+(?:[.,]\d+)*')

        # Palabras que indican una línea de encabezado o total (las excluimos)
        skip_keywords = re.compile(
            r'SUBTOTAL|TOTAL|IVA|IMPUESTO|DESCUENTO|RETE|PRECIO|VALOR|'
            r'CANTIDAD|DESCRIPCI[OÓ]N|REFERENCIA|CODIGO|ARTÍCULO|ITEM',
            re.IGNORECASE,
        )

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or skip_keywords.search(line_stripped):
                continue

            numbers = num_re.findall(line_stripped)
            if len(numbers) < 2:
                continue

            # El último número es el subtotal, el penúltimo el precio unitario
            # y el antepenúltimo (o el que quede) la cantidad
            try:
                subtotal_str   = numbers[-1]
                unit_price_str = numbers[-2]
                qty_str        = numbers[-3] if len(numbers) >= 3 else "1"

                subtotal   = self._parse_decimal(subtotal_str)
                unit_price = self._parse_decimal(unit_price_str)
                quantity   = self._parse_decimal(qty_str)

                if not unit_price or not quantity:
                    continue

                # La descripción es todo lo que queda antes del primer número
                first_num_pos = line_stripped.index(numbers[0])
                description = line_stripped[:first_num_pos].strip() if first_num_pos > 0 else line_stripped

                if not description:
                    continue

                items.append({
                    'product_code': self._extract_product_code(description),
                    'description':  description,
                    'reference':    None,
                    'unit_measure': self._detect_unit_from_text(description),
                    'quantity':     quantity,
                    'unit_price':   unit_price,
                    'subtotal':     subtotal or (quantity * unit_price),
                    'iva_rate':     self._detect_iva_from_text(line_stripped),
                })
            except Exception as e:
                logger.debug(f"Skipping line (parse error): {line_stripped!r} — {e}")
                continue

        return items

    def _extract_totals(self, lines: List[str], key_values: Dict[str, str]) -> Dict[str, Any]:
        """Extract totals and tax information including DIAN retenciones"""
        totals = {
            'subtotal': None,
            'iva_rate': None,
            'iva_amount': None,
            'rete_renta': None,
            'rete_iva': None,
            'rete_ica': None,
            'total_retenciones': None,
            'total': None,
            'total_items': None,
        }

        # Patterns that signal a monetary amount on the same line
        amount_pattern = re.compile(r'\$?\s*([\d\.]+(?:,\d{2})?)', re.IGNORECASE)

        for line in lines:
            upper = line.upper()

            # --- Subtotal ---
            if 'SUBTOTAL' in upper:
                m = amount_pattern.search(line)
                if m:
                    totals['subtotal'] = self._parse_decimal(m.group(1))

            # --- IVA (skip lines that are actually retenciones) ---
            if 'IVA' in upper and 'RETEIVA' not in upper and 'RETE IVA' not in upper:
                m = amount_pattern.search(line)
                if m:
                    totals['iva_amount'] = self._parse_decimal(m.group(1))
                rate_m = re.search(r'(\d{1,2})\s*%', line)
                if rate_m:
                    totals['iva_rate'] = Decimal(rate_m.group(1))

            # --- Retención en la Fuente ---
            # Aliases: RETEFUENTE, RETE FUENTE, RETENCIÓN FUENTE, RET. FUENTE, RTEFTE
            if re.search(r'RETE\s*FUENTE|RETEFUENTE|RET\.?\s*FUENTE|RTEFTE|RETENCI[OÓ]N\s*EN\s*LA\s*FUENTE', upper):
                m = amount_pattern.search(line)
                if m:
                    totals['rete_renta'] = self._parse_decimal(m.group(1))

            # --- ReteIVA ---
            # Aliases: RETEIVA, RETE IVA, RET IVA, RETENCIÓN IVA
            if re.search(r'RETE\s*IVA|RETEIVA|RET\.?\s*IVA|RETENCI[OÓ]N\s*IVA', upper):
                m = amount_pattern.search(line)
                if m:
                    totals['rete_iva'] = self._parse_decimal(m.group(1))

            # --- ReteICA ---
            # Aliases: RETEICA, RETE ICA, RET ICA, RETENCIÓN ICA
            if re.search(r'RETE\s*ICA|RETEICA|RET\.?\s*ICA|RETENCI[OÓ]N\s*ICA', upper):
                m = amount_pattern.search(line)
                if m:
                    totals['rete_ica'] = self._parse_decimal(m.group(1))

            # --- Total retenciones (línea resumen que algunos proveedores incluyen) ---
            if re.search(r'TOTAL\s*RETENCI[OÓ]N|TOTAL\s*RETE', upper):
                m = amount_pattern.search(line)
                if m:
                    totals['total_retenciones'] = self._parse_decimal(m.group(1))

            # --- Total final ---
            if 'TOTAL' in upper and 'SUBTOTAL' not in upper and not re.search(
                r'RETE|RETENCI[OÓ]N', upper
            ):
                m = amount_pattern.search(line)
                if m:
                    totals['total'] = self._parse_decimal(m.group(1))

        # If no explicit total_retenciones line, compute it from the parts
        if totals['total_retenciones'] is None:
            parts = [totals['rete_renta'], totals['rete_iva'], totals['rete_ica']]
            found = [p for p in parts if p is not None]
            if found:
                totals['total_retenciones'] = sum(found)

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
    
    def _smart_column_mapping(self, row: List[str], headers: List[str], row_index: int) -> Dict:
        """
        Smart mapping of table columns to invoice fields
        Handles variable column orders common in Colombian invoices
        """
        item = {}
    
        # Default mapping if we have enough columns
        if len(row) >= 5:
            # Common pattern: ITEM, CODE, DESCRIPTION, QTY, PRICE, SUBTOTAL
            item = {
                'item_number': row_index,
                'product_code': str(row[1]).strip() if len(row) > 1 else None,
                'description': str(row[2]).strip() if len(row) > 2 else None,
                'unit_measure': 'UND',  # Default, will be detected later
                'quantity': self._parse_decimal(row[-3]) if len(row) >= 3 else None,
                'unit_price': self._parse_decimal(row[-2]) if len(row) >= 2 else None,
                'subtotal': self._parse_decimal(row[-1]) if len(row) >= 1 else None
            }
        elif len(row) >= 4:
            # Minimal pattern: CODE, DESCRIPTION, QTY, PRICE
            item = {
                'item_number': row_index,
                'product_code': str(row[0]).strip(),
                'description': str(row[1]).strip(),
                'unit_measure': 'UND',
                'quantity': self._parse_decimal(row[2]),
                'unit_price': self._parse_decimal(row[3]),
                'subtotal': self._parse_decimal(row[3]) * self._parse_decimal(row[2]) if self._parse_decimal(row[3]) and self._parse_decimal(row[2]) else None
            }
    
        # Try to detect unit from description or separate column
        if item.get('description'):
            item['unit_measure'] = self._detect_unit_from_text(item['description'])
    
        return item

    # 5. Agregar método para detectar unidades:

    def _detect_unit_from_text(self, text: str) -> str:
        """Detect unit of measure from product description - ENHANCED"""
        if not text:
            return 'UND'
    
        text_upper = text.upper()

        # Enhanced unit patterns for Colombian invoices
        unit_patterns = {
            'DOC': ['DOCENA', 'DOC', 'DOZEN', '(X12)', 'X12'],
            'PAR': ['PAR', 'PARES', 'PAIR', '(X2)', 'X2'],
            'GRS': ['GRUESA', 'GRS', 'GROSS', '(X144)', 'X144'],
            'KG': ['KILOGRAMO', 'KG', 'KILO'],
            'G': ['GRAMO', 'GR', 'G'],
            'L': ['LITRO', 'LT', 'L'],
            'ML': ['MILILITRO', 'ML'],
        }
    
        # Check for quantity indicators like (X7), (X6) which suggest dozens
        if re.search(r'\(X[4-9]\)', text_upper) or re.search(r'\(X1[0-2]\)', text_upper):
            return 'DOC'
    
        # Check for explicit unit mentions
        for unit_code, patterns in unit_patterns.items():
            for pattern in patterns:
                if pattern in text_upper:
                    return unit_code
    
        return 'UND'
    
    def _parse_colombian_invoice_line(
        self,
        row: List[str],
        row_index: int,
        iva_col_idx: Optional[int] = None,
        col_mapping: Optional[Dict[str, int]] = None,
    ) -> Dict:
        """
        Parse Colombian invoice line with proper field detection.
        Handles: ITEM, REF, DESCRIPTION, QTY, UNIT, IVA%, PRICE, SUBTOTAL

        col_mapping: {field: col_index} detected from the header row via
                     _detect_column_mapping(). When provided, quantity and
                     unit_price are read from the known column indices instead
                     of being inferred positionally — this fixes the
                     Precio/Cantidad column-order bug.
        iva_col_idx: column index of the IVA column detected from the header row.
        """
        clean_row = [str(cell).strip() for cell in row if cell is not None]

        if len(clean_row) < 4:
            return {}

        # --- IVA extraction ---
        # Priority: explicit column > % in the cell text > embedded in description
        iva_rate: Optional[Decimal] = None
        if iva_col_idx is not None and iva_col_idx < len(clean_row):
            iva_rate = self._detect_iva_from_text(clean_row[iva_col_idx])

        # --- BUG 1 FIX: use header-detected column mapping when available ---
        # If unit_price wasn't detected by keyword but we know quantity and total,
        # infer price as the first numeric column between quantity and total.
        if col_mapping and 'quantity' in col_mapping and 'unit_price' not in col_mapping:
            qty_idx_hint   = col_mapping['quantity']
            total_idx_hint = col_mapping.get('total', len(clean_row) - 1)
            for candidate in range(qty_idx_hint + 1, total_idx_hint):
                if candidate < len(clean_row) and self._is_numeric(clean_row[candidate]):
                    col_mapping = dict(col_mapping)  # don't mutate the shared dict
                    col_mapping['unit_price'] = candidate
                    logger.info(f"unit_price inferred at col {candidate} between qty and total")
                    break

        if (
            col_mapping
            and 'quantity' in col_mapping
            and 'unit_price' in col_mapping
        ):
            qty_idx      = col_mapping['quantity']
            price_idx    = col_mapping['unit_price']
            subtotal_idx = col_mapping.get('total', len(clean_row) - 1)
            desc_idx     = col_mapping.get('description', 0)

            # Guard against out-of-range indices
            if qty_idx < len(clean_row) and price_idx < len(clean_row):
                description = str(clean_row[desc_idx]).strip() if desc_idx < len(clean_row) else ''
                unit = self._detect_unit_from_text(description)
                if iva_rate is None:
                    iva_rate = self._detect_iva_from_text(description)

                raw_reference = clean_row[0] if clean_row else None
                return {
                    'item_number':  row_index,
                    'product_code': self._extract_product_code(description),
                    'description':  description,
                    'reference':    self._clean_reference(raw_reference),
                    'unit_measure': unit,
                    'quantity':     self._parse_decimal(clean_row[qty_idx]),
                    'unit_price':   self._parse_decimal(clean_row[price_idx]),
                    'subtotal':     self._parse_decimal(clean_row[subtotal_idx]) if subtotal_idx < len(clean_row) else None,
                    'iva_rate':     iva_rate,
                }

        # --- Fallback: positional logic (numeric column detection) ---
        # Numeric indices excluding the IVA column
        numeric_indices = []
        for idx, cell in enumerate(clean_row):
            if idx == iva_col_idx:
                continue
            if self._is_numeric(cell):
                numeric_indices.append(idx)

        if len(numeric_indices) >= 3:
            idx_a        = numeric_indices[-3]
            idx_b        = numeric_indices[-2]
            subtotal_idx = numeric_indices[-1]

            # Heuristic: unit price >> quantity in Colombian invoices.
            # Compare magnitudes so we handle both column orderings:
            #   standard:  [Cantidad, Precio, Total]
            #   handmade:  [Precio, Cantidad, Total]
            val_a = self._parse_decimal(clean_row[idx_a]) or Decimal(0)
            val_b = self._parse_decimal(clean_row[idx_b]) or Decimal(0)
            if val_a > val_b:
                # First numeric is larger → it's the price
                price_idx = idx_a
                qty_idx   = idx_b
                logger.info(f"Column order: [price={idx_a}, qty={idx_b}] (magnitude heuristic)")
            else:
                qty_idx   = idx_a
                price_idx = idx_b

            description_parts = [
                c for i, c in enumerate(clean_row[:min(qty_idx, price_idx)]) if i != iva_col_idx
            ]

            item_num = None
            if description_parts and description_parts[0].isdigit():
                item_num = int(description_parts[0])
                description_parts = description_parts[1:]

            full_description = ' '.join(description_parts)
            unit = self._detect_unit_from_text(full_description)

            if iva_rate is None:
                iva_rate = self._detect_iva_from_text(full_description)

            raw_reference = clean_row[0] if clean_row else None
            reference = self._clean_reference(raw_reference)

            return {
                'item_number':  item_num or row_index,
                'product_code': self._extract_product_code(full_description),
                'description':  full_description,
                'reference':    reference,
                'unit_measure': unit,
                'quantity':     self._parse_decimal(clean_row[qty_idx]),
                'unit_price':   self._parse_decimal(clean_row[price_idx]),
                'subtotal':     self._parse_decimal(clean_row[subtotal_idx]),
                'iva_rate':     iva_rate,
            }

        # Last-resort: assume standard column order
        full_description = ' '.join(clean_row[1:-3]) if len(clean_row) > 3 else clean_row[0]
        if iva_rate is None:
            iva_rate = self._detect_iva_from_text(full_description)

        return {
            'item_number':  row_index,
            'product_code': clean_row[0] if clean_row else None,
            'description':  full_description,
            'reference':    clean_row[0] if clean_row else None,
            'unit_measure': self._detect_unit_from_text(' '.join(clean_row)),
            'quantity':     self._parse_decimal(clean_row[-3]) if len(clean_row) >= 3 else None,
            'unit_price':   self._parse_decimal(clean_row[-2]) if len(clean_row) >= 2 else None,
            'subtotal':     self._parse_decimal(clean_row[-1]) if len(clean_row) >= 1 else None,
            'iva_rate':     iva_rate,
        }

        # 4. AGREGAR método para extraer código de producto:
    def _extract_product_code(self, description: str) -> str:
        """Extract product code from description"""
        if not description:
            return ""
    
        # Look for patterns like (ABC-123) or REF-123
        code_patterns = [
            r'\(([A-Z0-9-]+)\)',  # (ABC-123)
            r'REF[:\s]*([A-Z0-9-]+)',  # REF: ABC-123
            r'([A-Z0-9]{3,}-[A-Z0-9]+)',  # ABC-123
            r'^([A-Z0-9]{3,})\s',  # Starting alphanumeric code
        ]
    
        for pattern in code_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)
    
        # Fallback: take first word if it looks like a code
        words = description.split()
        if words and len(words[0]) >= 3:
            return words[0]
    
        return description[:20]  # First 20 chars as fallback

    # 5. AGREGAR método para detectar números:
    def _is_numeric(self, value: str) -> bool:
        """Check if a string represents a number"""
        if not value:
            return False
    
        # Remove common formatting
        clean_value = re.sub(r'[\$\s,.]', '', str(value))
    
        try:
            float(clean_value)
            return True
        except ValueError:
            return False
    
    def _clean_reference(self, raw_reference: str) -> Optional[str]:
        """Clean reference field removing item numbers"""
        if not raw_reference:
            return None
    
        # Remover números del inicio: "1 049 (DAMA)" → "049 (DAMA)"
        cleaned = re.sub(r'^\d+\s+', '', raw_reference.strip())
    
        return cleaned if cleaned else None
    
