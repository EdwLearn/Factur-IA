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
from ..amount_parser import parse_colombian_amount

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
    
    # Patrón NIT colombiano: cubre NIT. / NIT: / NIT<espacio> / NIT<nada>
    # y también C.C. / CC para personas naturales.
    _NIT_PATTERN = re.compile(
        r'(?:NIT\.?\s*|C\.?C\.?\s*|CC\s+)(\d{6,12}[\s-]?\d{1})',
        re.IGNORECASE,
    )
    # Limpieza complementaria: elimina el bloque NIT+número de un texto
    _NIT_STRIP_PATTERN = re.compile(
        r'\s*(?:NIT\.?|C\.?C\.?|CC)?\s*\d{6,12}[\s-]?\d{1}',
        re.IGNORECASE,
    )

    def _extract_nit_from_text(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Dado un texto que puede contener nombre + NIT concatenados,
        separa y retorna (nombre_limpio, nit).

        Patrones colombianos soportados:
          "NIT. 900816058-4", "NIT: 900816058-4", "NIT 900816058-4",
          "NIT.900816058-4", "C.C. 71384997-3", "CC 71384997-3"
        """
        match = self._NIT_PATTERN.search(text)
        if not match:
            return text, None

        raw = match.group(1).replace(' ', '')
        # Normalizar a formato estándar XXXXXXXXX-D
        if '-' not in raw and len(raw) >= 2:
            raw = f"{raw[:-1]}-{raw[-1]}"
        nit = raw

        # Quitar el bloque NIT del nombre
        clean_name = self._NIT_STRIP_PATTERN.sub('', text).strip()
        clean_name = re.sub(r'[\s\-\.,]+$', '', clean_name).strip()

        return clean_name, nit

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

        for line in lines:
            # Extraer NIT usando el helper que cubre todos los formatos colombianos
            _, nit = self._extract_nit_from_text(line)
            if nit and not supplier['nit']:
                supplier['nit'] = nit

            # Nombre de empresa: líneas con sufijo legal — limpiar NIT del texto
            if (
                not supplier['company_name']
                and len(line) > 10
                and any(word in line.upper() for word in ['LTDA', 'S.A.S', 'EMPRESA', 'COMERCIAL', 'S.A', 'SAS'])
            ):
                clean_name, _ = self._extract_nit_from_text(line)
                supplier['company_name'] = clean_name.strip() or None

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
        'valor impuesto',
        # NOTA: 'impto.cargo' / 'valor impto' se mapean a unit_price (iSiigo),
        #        no se incluyen aquí para evitar confusión con el precio final.
    }

    # Map of invoice field → keywords that identify that column in a header row.
    # ORDER MATTERS: checked top-to-bottom per cell; first match wins.
    # 'item' removed from description — it's almost always a row-number column.
    _COLUMN_KEYWORD_MAP = {
        'product_code': {
            'código', 'codigo', 'cod.', 'cod',
            'código interno', 'cod interno',
            'código comercial', 'cod comercial', 'cód comercial',
            'referencia', 'ref.', 'ref',
            'sku',
            'código producto', 'cod producto',
            'art.', 'artículo', 'articulo',
            # 'item'/'ítem' eliminados: en iSiigo es el número secuencial (1,2,3),
            # no el código de producto. La columna real es "Código".
        },
        'description': {
            'descripcion', 'descripción', 'description', 'detalle',
            'producto', 'articulo', 'artículo', 'concepto',
            'mercancía', 'mercancia',
        },
        'quantity': {
            'cantidad', 'cant', 'cant.', 'cant,', 'can.', 'qty', 'quantity', 'unidades',
        },
        'unit_price': {
            # explicit price keywords
            'precio', 'price',
            # "valor/vr/vlr + unit*" — catches "Vlr. Unitario", "Mr. Unitario", etc.
            'unitario', 'valor unit', 'vr unit', 'vlr unit',
            'vr. unit', 'p. unit', 'precio unit',
            'mr. unit', 'mr unit',
            # aliases adicionales colombianos
            'vlr.unit', 'vlr. unit', 'v.unit', 'v unit', 'vr.unit',
            'valor unitario', 'vr. unitario', 'p.unit',
            # iSiigo: "Valor Impto.Cargo" = precio unitario CON IVA incluido
            # (es el costo real que pagó el negocio, no un campo de tasa de IVA)
            'impto.cargo', 'valor impto', 'impto cargo',
        },
        'total': {
            'total', 'valor total', 'subtotal', 'importe',
            'vr total', 'vlr total',
            'vlr.total', 'vr.total', 'valor.total',
        },
        'unit_measure': {
            'u/m', 'unidad', 'um', 'medida',
            # 'unit' removed — too broad, matched 'unitario' before unit_price could
        },
    }

    # Whitelist de unidades válidas colombianas.
    # Solo valores de la columna U/M que coincidan exactamente con esta lista
    # se aceptan como unidad; cualquier otro → "UND" (default seguro).
    _VALID_UNITS = {
        'und', 'unidad', 'unidades', 'un',
        'cja', 'caja', 'cajas',
        'blt', 'blister',
        'par', 'pares',
        'kg', 'gr', 'gramo', 'gramos',
        'lt', 'litro', 'litros', 'ml',
        'mt', 'metro', 'metros', 'cm',
        'doc', 'docena',
        'paq', 'paquete',
        'niu',
        'set', 'kit',
        'pcs', 'pieza', 'piezas',
    }

    # Keywords de unit_price que tienen PRIORIDAD ABSOLUTA sobre otros matches:
    # cuando se detectan, sobreescriben cualquier mapeo previo de unit_price.
    # Caso iSiigo: tabla con Vr.Unitario (sin IVA) + Valor Impto.Cargo (con IVA);
    # el costo real pagado es el que incluye impuesto.
    _UNIT_PRICE_PRIORITY_KEYWORDS = {
        'impto.cargo', 'valor impto', 'impto cargo',
    }

    # Columnas que deben ser completamente ignoradas en la detección.
    # 'código interno' y 'cod interno' se quitaron de aquí — ahora se mapean
    # como product_code en _COLUMN_KEYWORD_MAP.
    _IGNORE_COLUMN_KEYWORDS = {
        'separa', 'rev', 'revisó', 'reviso',
        'color', 'dsc', 'dto', 'descto',
    }

    def _detect_iva_column(self, header_row: List[str]) -> Optional[int]:
        """Return the column index of the IVA/tarifa column, or None."""
        for idx, cell in enumerate(header_row):
            if str(cell).strip().lower() in self._IVA_HEADER_ALIASES:
                return idx
        return None

    # Celdas de header que deben descartarse antes de mapear columnas.
    # Textract a veces fusiona "Separa- Rev" como una celda y otras la divide
    # en "Separa-" | "Rev", corriendo todos los índices +1.
    # Al filtrarlas ANTES de mapear pero conservando original_idx,
    # los índices resultantes siguen apuntando a las posiciones reales de cada fila.
    _IGNORE_HEADER_CELLS = {
        'separa', 'separa-', 'separa- rev',
        'rev', 'revisó', 'reviso',
        '', 'none',
    }

    def _detect_column_mapping(self, header_row: List[str]) -> Dict[str, int]:
        """
        Read the header row and return {field: col_index} using partial keyword
        matching (containment). First match per field wins, EXCEPT for
        _UNIT_PRICE_PRIORITY_KEYWORDS which override any prior unit_price match.
        Columns matching _IGNORE_COLUMN_KEYWORDS are skipped entirely.

        Junk columns (Separa-, Rev, etc.) are stripped BEFORE matching but
        original_idx is preserved so all returned indices are correct for
        indexing into the actual data rows.
        """
        logger.info(f"HEADER ROW RAW: {header_row}")
        logger.info(f"HEADER ROW LOWER: {[str(c).lower().strip() for c in header_row]}")
        logger.info(f"header_row recibido: {header_row}")

        # Filtrar celdas basura conservando el índice original
        header_filtered = [
            (original_idx, cell)
            for original_idx, cell in enumerate(header_row)
            if str(cell).lower().strip() not in self._IGNORE_HEADER_CELLS
        ]
        logger.info(f"header_filtered (original_idx, cell): {header_filtered}")

        mapping: Dict[str, int] = {}
        for original_idx, cell in header_filtered:
            # Normalizar saltos de línea → espacio para que "CÓDIGO\nINTERNO" → "código interno"
            cell_lower = str(cell).strip().lower().replace('\n', ' ')
            # Saltar columnas que deben ignorarse (coincidencia parcial)
            if any(kw in cell_lower for kw in self._IGNORE_COLUMN_KEYWORDS):
                logger.info(f"Columna {original_idx} ignorada: {cell!r}")
                continue
            # Prioridad: keywords de unit_price que sobreescriben un match previo
            # (ej. iSiigo: Vr.Unitario mapeado primero, luego Valor Impto.Cargo lo reemplaza)
            if any(kw in cell_lower for kw in self._UNIT_PRICE_PRIORITY_KEYWORDS):
                mapping['unit_price'] = original_idx
                logger.info(f"unit_price OVERRIDE → col {original_idx}: {cell!r}")
                continue
            for field, keywords in self._COLUMN_KEYWORD_MAP.items():
                if field not in mapping:
                    if any(kw in cell_lower for kw in keywords):
                        mapping[field] = original_idx
                        break
        logger.info(f"col_mapping detectado: {mapping}")
        logger.info(f"MAPPING COMPLETO: {mapping}")
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

    def _find_header_row_idx(self, rows: List[List[str]]) -> int:
        """
        Encuentra el índice de la fila que contiene los encabezados de columna reales.
        Útil cuando Textract incluye filas de empresa/dirección antes del header real.
        Retorna 0 si ninguna fila supera el umbral de keywords (seguro por defecto).
        """
        best_idx = 0
        best_score = 0
        for idx, row in enumerate(rows[:12]):  # revisar las primeras 12 filas
            score = 0
            for cell in row:
                cell_norm = str(cell).strip().lower().replace('\n', ' ')
                for keywords in self._COLUMN_KEYWORD_MAP.values():
                    if any(kw in cell_norm for kw in keywords):
                        score += 1
                        break
            if score > best_score:
                best_score = score
                best_idx = idx
        if best_score >= 2:
            logger.info(f"Header real detectado en row {best_idx} (score={best_score})")
        return best_idx if best_score >= 2 else 0

    def _expand_merged_rows(self, rows: List[List[str]]) -> List[List[str]]:
        """
        Expande filas donde Textract fusionó múltiples filas de datos en una sola celda.
        Detecta celdas con valores separados por '\\n' y las divide en N filas individuales.
        Ejemplo Tronex: una fila con '1\\n2\\n3\\n4' → 4 filas separadas.
        """
        expanded = []
        for row in rows:
            non_empty = [str(c) for c in row if c and str(c).strip()]
            if not non_empty:
                continue
            max_lines = max(len(c.split('\n')) for c in non_empty)
            if max_lines <= 1:
                expanded.append(row)
                continue
            logger.info(
                f"_expand_merged_rows: fila fusionada con {max_lines} sub-filas detectada"
            )
            for i in range(max_lines):
                sub_row = []
                for cell in row:
                    parts = str(cell).split('\n')
                    sub_row.append(parts[i].strip() if i < len(parts) else '')
                expanded.append(sub_row)
        return expanded

    def _extract_line_items(self, tables: List[Dict], lines: List[str]) -> List[Dict]:
        """Extract product line items from tables - FIXED FOR COLOMBIAN INVOICES"""
        line_items = []

        if tables:
            main_table = self._find_product_table(tables)
            if not main_table:
                main_table = max(tables, key=lambda t: t['row_count'])

            all_rows = main_table['rows']

            # Buscar el header real (puede no ser row[0] — ej. Tronex tiene empresa en filas previas)
            header_row_idx = self._find_header_row_idx(all_rows)
            header_row = all_rows[header_row_idx] if all_rows else []

            # Filas de datos = todo lo posterior al header, expandidas si están fusionadas
            raw_data_rows = all_rows[header_row_idx + 1:]
            table_rows = self._expand_merged_rows(raw_data_rows)

            logger.info(f"RAW TABLE ROWS: {all_rows[:3]}")
            logger.info(f"RAW ROWS COUNT: {len(all_rows)} → data rows: {len(table_rows)}")
            logger.info(f"HEADER ROW (idx={header_row_idx}): {header_row}")
            logger.info(f"DATA ROW 0: {table_rows[0] if table_rows else 'empty'}")
            logger.info(f"DATA ROW 1: {table_rows[1] if len(table_rows) > 1 else 'empty'}")

            iva_col_idx = self._detect_iva_column(header_row)
            col_mapping = self._detect_column_mapping(header_row)

            for i, row in enumerate(table_rows):
                if len(row) >= 3:
                    try:
                        item = self._parse_colombian_invoice_line(row, i, iva_col_idx, col_mapping)
                        if not item:
                            continue
                        desc  = item.get('description', '')
                        qty   = item.get('quantity')
                        price = item.get('unit_price')
                        # Guardia anti-overflow: filas con valores fusionados
                        if qty is not None and qty > 9999:
                            logger.warning(
                                f"Fila {i} descartada — quantity sospechosa: {qty} "
                                f"(probable row-merging). raw={row}"
                            )
                            continue
                        if price is not None and price > 9_999_999:
                            logger.warning(
                                f"Fila {i} descartada — unit_price sospechoso: {price} "
                                f"(probable row-merging). raw={row}"
                            )
                            continue
                        # Filtro de basura: encabezados del PDF colados como productos
                        if self._is_garbage_row(desc, qty, price):
                            logger.info(
                                f"Fila {i} descartada por _is_garbage_row — "
                                f"desc={desc!r}, qty={qty}, price={price}"
                            )
                            continue
                        # BUG 2: incluir si qty y price son legibles (NOT NULL en BD).
                        # La mejora es que ya no se INVENTA qty=1; si no se lee, se descarta.
                        if desc and qty is not None and price is not None:
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
                # BUG 2: si no hay tercer número, dejar qty en None — no inventar
                qty_str = numbers[-3] if len(numbers) >= 3 else None

                subtotal   = parse_colombian_amount(subtotal_str)
                unit_price = parse_colombian_amount(unit_price_str)
                quantity   = self._parse_decimal(qty_str) if qty_str else None

                if not unit_price:
                    continue

                # La descripción es todo lo que queda antes del primer número
                first_num_pos = line_stripped.index(numbers[0])
                description = line_stripped[:first_num_pos].strip() if first_num_pos > 0 else line_stripped

                if not description:
                    continue

                if self._is_garbage_row(description, quantity, unit_price):
                    logger.info(
                        f"Línea de texto descartada por _is_garbage_row — "
                        f"desc={description!r}, qty={quantity}, price={unit_price}"
                    )
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

        # BUG 1 FIX: capture full amount including commas and dots in any format.
        # _parse_colombian_amount handles format detection (European vs American).
        amount_pattern = re.compile(r'\$?\s*([\d,\.]+)', re.IGNORECASE)

        # BUG 2 FIX: track high-priority total ("VALOR TOTAL", "TOTAL A PAGAR")
        # separately from generic TOTAL lines so the explicit field always wins.
        total_high_priority: Optional[Decimal] = None
        total_generic: Optional[Decimal] = None

        for line in lines:
            upper = line.upper()

            # --- Subtotal ---
            if 'SUBTOTAL' in upper:
                m = amount_pattern.search(line)
                if m:
                    totals['subtotal'] = parse_colombian_amount(m.group(1))

            # --- IVA (skip lines that are actually retenciones) ---
            if 'IVA' in upper and 'RETEIVA' not in upper and 'RETE IVA' not in upper:
                m = amount_pattern.search(line)
                if m:
                    totals['iva_amount'] = parse_colombian_amount(m.group(1))
                rate_m = re.search(r'(\d{1,2})\s*%', line)
                if rate_m:
                    totals['iva_rate'] = Decimal(rate_m.group(1))

            # --- Retención en la Fuente ---
            if re.search(r'RETE\s*FUENTE|RETEFUENTE|RET\.?\s*FUENTE|RTEFTE|RETENCI[OÓ]N\s*EN\s*LA\s*FUENTE', upper):
                m = amount_pattern.search(line)
                if m:
                    totals['rete_renta'] = parse_colombian_amount(m.group(1))

            # --- ReteIVA ---
            if re.search(r'RETE\s*IVA|RETEIVA|RET\.?\s*IVA|RETENCI[OÓ]N\s*IVA', upper):
                m = amount_pattern.search(line)
                if m:
                    totals['rete_iva'] = parse_colombian_amount(m.group(1))

            # --- ReteICA ---
            if re.search(r'RETE\s*ICA|RETEICA|RET\.?\s*ICA|RETENCI[OÓ]N\s*ICA', upper):
                m = amount_pattern.search(line)
                if m:
                    totals['rete_ica'] = parse_colombian_amount(m.group(1))

            # --- Total retenciones (línea resumen) ---
            if re.search(r'TOTAL\s*RETENCI[OÓ]N|TOTAL\s*RETE', upper):
                m = amount_pattern.search(line)
                if m:
                    totals['total_retenciones'] = parse_colombian_amount(m.group(1))

            # --- BUG 2 FIX: Total final con prioridad explícita ---
            # Priority 1: "VALOR TOTAL", "TOTAL A PAGAR", "TOTAL FACTURA"
            elif re.search(r'VALOR\s*TOTAL|TOTAL\s*A\s*PAGAR|TOTAL\s*FACTURA', upper):
                m = amount_pattern.search(line)
                if m:
                    total_high_priority = parse_colombian_amount(m.group(1))
            # Priority 2: línea genérica con TOTAL (excluye SUBTOTAL y RETE)
            elif (
                'TOTAL' in upper
                and 'SUBTOTAL' not in upper
                and not re.search(r'RETE|RETENCI[OÓ]N', upper)
            ):
                m = amount_pattern.search(line)
                if m:
                    total_generic = parse_colombian_amount(m.group(1))

        # Asignar total: high-priority > generic > fallback calculado
        if total_high_priority is not None:
            totals['total'] = total_high_priority
        elif total_generic is not None:
            totals['total'] = total_generic
        else:
            sub  = totals.get('subtotal') or Decimal('0')
            iva  = totals.get('iva_amount') or Decimal('0')
            rete = totals.get('total_retenciones') or Decimal('0')
            totals['total'] = sub + iva - rete
            logger.warning(
                f"Total not found in document, calculating as fallback: "
                f"{sub} + {iva} - {rete} = {totals['total']}"
            )

        # Si no hay total_retenciones explícito, calcularlo desde las partes
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

    def _parse_colombian_amount(self, value: str) -> Decimal:
        """
        Parse a Colombian monetary amount to Decimal.

        Handles all common formats found in Colombian invoices:
          19.545,70  (European: dot=thousands, comma=decimal)
          19,545.70  (American: comma=thousands, dot=decimal)
          19,545     (thousands-only with comma)
          19.545     (thousands-only with dot)
          19,54      (decimal comma, no thousands)
          19.54      (decimal dot, no thousands)
        """
        if not value:
            return Decimal('0')

        clean = re.sub(r'[^\d,\.]', '', str(value).strip())

        if not clean:
            return Decimal('0')

        if ',' in clean and '.' in clean:
            # Both separators present — determine which is decimal by position
            if clean.index(',') > clean.index('.'):
                # European: 19.545,70 → remove dot thousands, comma→dot decimal
                clean = clean.replace('.', '').replace(',', '.')
            else:
                # American: 19,545.70 → remove comma thousands
                clean = clean.replace(',', '')
        elif ',' in clean:
            parts = clean.split(',')
            if len(parts[-1]) == 2:
                # Decimal comma: 19,54 → 19.54
                clean = clean.replace(',', '.')
            else:
                # Thousands comma: 19,545 → 19545
                clean = clean.replace(',', '')
        elif '.' in clean:
            parts = clean.split('.')
            if len(parts[-1]) == 2:
                # Decimal dot: 19.54 → keep as-is
                pass
            else:
                # Thousands dot: 19.545 → 19545
                clean = clean.replace('.', '')

        try:
            return Decimal(clean)
        except Exception:
            return Decimal('0')
    
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
                'unit_price': parse_colombian_amount(row[-2]) if len(row) >= 2 else None,
                'subtotal': parse_colombian_amount(row[-1]) if len(row) >= 1 else None
            }
        elif len(row) >= 4:
            # Minimal pattern: CODE, DESCRIPTION, QTY, PRICE
            item = {
                'item_number': row_index,
                'product_code': str(row[0]).strip(),
                'description': str(row[1]).strip(),
                'unit_measure': 'UND',
                'quantity': self._parse_decimal(row[2]),
                'unit_price': parse_colombian_amount(row[3]),
                'subtotal': parse_colombian_amount(row[3]) * self._parse_decimal(row[2]) if parse_colombian_amount(row[3]) and self._parse_decimal(row[2]) else None
            }
    
        # Try to detect unit from description or separate column
        if item.get('description'):
            item['unit_measure'] = self._detect_unit_from_text(item['description'])
    
        return item

    # 5. Agregar método para detectar unidades:

    def _detect_unit_from_text(self, text: str) -> str:
        """
        Detect unit of measure from product description.
        Uses word-boundary matching to avoid false positives like:
        'G' inside 'REGULAR', 'L' inside 'CPMSCL', 'X2' inside product codes.
        """
        if not text:
            return 'UND'

        text_upper = text.upper()

        # Dozens indicator patterns: (X4)…(X12)
        if re.search(r'\(X(?:[4-9]|1[0-2])\)', text_upper):
            return 'DOC'

        # Each unit mapped to regex patterns with word boundaries.
        # Single-letter units (G, L) require explicit \b so they don't match
        # inside longer words.
        unit_patterns = [
            ('DOC', [r'\bDOCENA\b', r'\bDOC\b', r'\bDOZEN\b', r'\(X12\)', r'\bX12\b']),
            ('PAR', [r'\bPARES\b', r'\bPAIR\b', r'\(X2\)']),   # 'PAR' solo → demasiado común en descripciones
            ('GRS', [r'\bGRUESA\b', r'\bGRS\b', r'\bGROSS\b', r'\(X144\)', r'\bX144\b']),
            ('KG',  [r'\bKILOGRAMO\b', r'\bKG\b', r'\bKILO\b']),
            ('ML',  [r'\bMILILITRO\b', r'\bML\b']),
            ('G',   [r'\bGRAMO\b', r'\bGR\b']),  # '\bG\b' removido — demasiado ambiguo
            ('L',   [r'\bLITRO\b', r'\bLT\b']),  # '\bL\b' removido — demasiado ambiguo
        ]

        for unit_code, patterns in unit_patterns:
            for pattern in patterns:
                if re.search(pattern, text_upper):
                    return unit_code

        return 'UND'
    
    # Patrones regex que identifican filas de encabezado de PDF disfrazadas de productos.
    # Se aplican contra la descripción del ítem (case-insensitive, inicio de cadena).
    _HEADER_GARBAGE_PATTERNS = [
        # Campos de datos del cliente / empresa
        r"^(tel|teléfono|telefono)[\.\:\s]",
        r"^(fecha|date)[\.\:\s]",
        r"^(dirección|direccion|dir)[\.\:\s]",
        r"^(ciudad|city)[\.\:\s]",
        r"^(nit|cc|c\.c)[\.\:\s]",
        r"^(nombre|name)[\.\:\s]",
        r"^(cliente|customer)[\.\:\s]",
        r"^(vendedor|vendor)[\:\s]",
        r"^(página|pagina|page)\s*\d",
        r"^página\s*\d+\s*de\s*\d+",
        # Líneas de totales / impuestos
        r"^(subtotal|total|iva|descuento)[\.\:\s]",
        # Condiciones de pago y logística
        r"^(forma de pago|medio de pago)",
        r"^(observaci[oó]n)",
        r"^(elabor[oó]|recibido|firma)",
        r"^(reclamos?)\s+solo",
        # Encabezados de columna sueltos que Textract cuela como fila de datos
        r"^(do|unidad|und)[\.\:\s]?$",
        r"^(despacho|reviso|revisó|separa|rev)[\.\:\s]?$",
        # Datos de empresa / Tronex específicos
        r"^pbx[\.\:\s]",
        r"^linea\s+de\s+servicio",
        r"^factura\s+(electr[oó]nica|electronica)\s+de\s+venta",
        r"^pedido\s+n[o°]",
        r"^cufe[\:\s]",
        r"^(cid|uuid)[\:\s]",
        r"^(resolución|resolucion)\s+(habilitaci[oó]n|dian)",
        # Campos de logística y cliente
        r"^(entregar\s+a|comprador|enviar\s+a|despachar\s+a)",
        r"^(direcci[oó]n\s+de\s+entrega|direcci[oó]n\s+envio)",
        # Valores que no son productos
        r"^\d{7,}$",            # teléfono o NIT (solo dígitos, 7+)
        r"^[a-f0-9]{20,}$",     # hash largo tipo CUFE
        r"^\d{2}/\d{2}/\d{4}$", # fecha como 18/10/2025
        r"^[A-Z]\d+\s*$",       # una letra + números sueltos (código sin texto)
        # Footer de Tronex y documentos similares
        r"^a\s+numrot\b",                        # "a NumRot 2.0 Version..."
        r"^hhme\d+",                             # "HHME1450437"
        r"^numrot\b",                            # variante sin "a"
        r"^(página|pagina)\s*\d",               # "Página 1 de 2"
        r"^\$\s*[\d,\.]+$",                      # solo un valor monetario "$910,829.78"
        r"^valor\s+(neto|total|bruto|iva|rete)",  # líneas de totales
        r"^rete\s+(fuente|iva|ica)",
        r"^otros\s+gastos",
        r"^distribuidor\s+oficial",
        r"^proveedor\s+tecnol[oó]gico",
        r"^factura\s+impresa",
        r"^total\s+l[ií]neas",                   # "TOTAL LÍNEAS: 4 TOTAL: 308"
        r"^recib[ií]\s+real",                    # "RECIBÍ REAL Y MATERIALMENTE..."
        r"^firma\s+y\s+sello",
    ]

    def _is_garbage_row(
        self,
        description: str,
        quantity,   # Decimal | None
        unit_price, # Decimal | None
    ) -> bool:
        """
        Retorna True si la fila parece ser basura del encabezado del PDF
        y NO debe guardarse como line item.
        """
        if not description:
            return True
        desc = description.strip()
        # Menos de 3 caracteres → fragmento de encabezado, no producto
        if len(desc) < 3:
            return True

        # Verificar patrones de encabezado
        for pattern in self._HEADER_GARBAGE_PATTERNS:
            if re.match(pattern, desc, re.IGNORECASE):
                return True

        # Cantidad que parece número de teléfono o NIT (> 999 999)
        if quantity is not None and quantity > 999_999:
            return True

        # Precio que parece NIT colombiano (9 dígitos → > 99 999 999)
        if unit_price is not None and unit_price > 99_999_999:
            return True

        # Fila de resumen / total: precio absurdamente alto y descripción corta
        # (ej. HHME con unit_price=910,829.78 y description='HHME')
        if unit_price is not None and unit_price > 500_000:
            word_count = len(desc.split())
            if word_count < 3:
                return True

        return False

    def _apply_iva_normalization(self, item: Dict) -> Dict:
        """
        Si iva_rate > 100, se asume que es el VALOR ABSOLUTO del IVA (no el porcentaje).
        Calcula el porcentaje real y lo normaliza a las tarifas DIAN colombianas: 0, 5, 19.
        """
        iva_rate = item.get('iva_rate')
        unit_price = item.get('unit_price')
        if iva_rate and unit_price and iva_rate > 100 and unit_price > 0:
            pct = round((float(iva_rate) / float(unit_price)) * 100, 2)
            if pct < 3:
                normalized = Decimal('0')
            elif pct < 10:
                normalized = Decimal('5')
            else:
                normalized = Decimal('19')
            logger.info(
                f"IVA normalizado: valor absoluto {iva_rate} / precio {unit_price} "
                f"= {pct:.1f}% → tarifa DIAN {normalized}%"
            )
            return {**item, 'iva_rate': normalized}
        return item

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

        logger.info(f"RAW CELLS: {clean_row}")
        logger.info(f"col_mapping usado: {col_mapping}")
        if col_mapping and col_mapping.get('quantity') == 1:
            logger.info(f"CANT raw value: {clean_row[1] if len(clean_row) > 1 else 'N/A'}")
            logger.info(f"DETALLE raw value: {clean_row[2] if len(clean_row) > 2 else 'N/A'}")
            logger.info(f"VLR.UNIT raw value: {clean_row[3] if len(clean_row) > 3 else 'N/A'}")

        if len(clean_row) < 4:
            return {}

        # --- IVA extraction ---
        # Priority: explicit column > % in the cell text > embedded in description
        iva_rate: Optional[Decimal] = None
        if iva_col_idx is not None and iva_col_idx < len(clean_row):
            iva_rate = self._detect_iva_from_text(clean_row[iva_col_idx])
            if iva_rate is None:
                # La columna puede contener el VALOR ABSOLUTO del IVA (ej. iSiigo "Valor Impto.Cargo")
                # → parsear como decimal; _apply_iva_normalization lo convertirá al % real
                iva_rate = self._parse_decimal(clean_row[iva_col_idx])

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

            logger.info(
                f"Column order: desc={desc_idx}, qty={qty_idx}, "
                f"price={price_idx}, total={subtotal_idx}"
            )

            # Guard against out-of-range indices
            if qty_idx < len(clean_row) and price_idx < len(clean_row):
                description = str(clean_row[desc_idx]).strip() if desc_idx < len(clean_row) else ''

                # Extraer product_code desde su columna dedicada cuando está mapeada.
                # Si no hay columna explícita, intentar regex sobre descripción.
                if 'product_code' in col_mapping:
                    pc_idx = col_mapping['product_code']
                    product_code = (
                        str(clean_row[pc_idx]).strip()
                        if pc_idx < len(clean_row) and clean_row[pc_idx]
                        else None
                    )
                    logger.info(f"product_code from col {pc_idx}: {product_code!r}")
                else:
                    code_match = re.match(r'^([A-Z0-9\-\.]{3,15})\s+(.+)$', description, re.IGNORECASE)
                    if code_match:
                        product_code = code_match.group(1)
                        description  = code_match.group(2)
                        logger.info(f"product_code extracted from desc: {product_code!r}")
                    else:
                        product_code = None

                mapped_cols = set(col_mapping.values())
                if iva_col_idx is not None:
                    mapped_cols.add(iva_col_idx)

                # Prefijo de descripción: Textract a veces parte una palabra en la columna
                # anterior a DESCRIPCIÓN (ej. Tronex "CÓDIGO COMERCIAL": 'EN' + 'CENDEDOR...'
                # → 'ENCENDEDOR...').  Si la celda previa al desc_idx no está mapeada y es
                # texto corto (≤ 5 chars) y no numérico, lo concatenamos al inicio.
                if desc_idx > 0:
                    prev_idx = desc_idx - 1
                    if prev_idx not in mapped_cols:
                        prev_cell = clean_row[prev_idx].strip() if prev_idx < len(clean_row) else ''
                        if prev_cell and not self._is_numeric(prev_cell) and len(prev_cell) <= 5:
                            description = prev_cell + description
                            logger.info(
                                f"Descripción prefijada: '{prev_cell}' + '...' → '{description[:40]}'"
                            )

                # Fusión dígito adyacente: Textract parte "E27" → "E" (celda desc) + "27".
                # Si la descripción termina en letra y la siguiente celda no mapeada es dígito puro.
                check_idx = desc_idx + 1
                while (
                    check_idx < len(clean_row)
                    and check_idx not in mapped_cols
                ):
                    adjacent = clean_row[check_idx].strip()
                    if re.match(r'^\d+$', adjacent) and description and description[-1].isalpha():
                        description += adjacent   # "E" + "27" → "E27"
                        check_idx += 1
                    else:
                        break

                # Unit measure: usar columna dedicada con whitelist, o detectar desde descripción.
                if 'unit_measure' in col_mapping:
                    um_idx = col_mapping['unit_measure']
                    if um_idx < len(clean_row):
                        unit_raw = str(clean_row[um_idx]).strip().lower()
                        unit = unit_raw.upper() if unit_raw in self._VALID_UNITS else 'UND'
                        logger.info(f"unit_measure from col {um_idx}: '{unit_raw}' → '{unit}'")
                    else:
                        unit = self._detect_unit_from_text(description)
                else:
                    unit = self._detect_unit_from_text(description)

                if iva_rate is None:
                    iva_rate = self._detect_iva_from_text(description)

                raw_reference = clean_row[0] if clean_row else None

                # BUG 2 FIX: leer qty y price directamente; no calcular subtotal si no se puede leer.
                qty_val   = self._parse_decimal(clean_row[qty_idx])
                price_val = parse_colombian_amount(clean_row[price_idx])
                sub_val   = (
                    parse_colombian_amount(clean_row[subtotal_idx])
                    if subtotal_idx < len(clean_row)
                    else None
                )

                return self._apply_iva_normalization({
                    'item_number':  row_index,
                    'product_code': product_code,
                    'description':  description,
                    'reference':    self._clean_reference(raw_reference),
                    'unit_measure': unit,
                    'quantity':     qty_val,
                    'unit_price':   price_val,
                    'subtotal':     sub_val,
                    'iva_rate':     iva_rate,
                })

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

            # Prefer header-detected quantity index over magnitude heuristic.
            # Fixes: CANT (pos 2) before DETALLE (pos 3) — if mapper already knows
            # which column is quantity, trust it unconditionally.
            if col_mapping and 'quantity' in col_mapping:
                qty_idx = col_mapping['quantity']
                price_idx = idx_b if idx_a == qty_idx else idx_a
                logger.info(
                    f"Column order: qty={qty_idx}, price={price_idx} (header-mapped qty)"
                )
            else:
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

            # Fallback: sin col_mapping de product_code — regex sobre descripción
            code_match = re.match(r'^([A-Z0-9\-\.]{3,15})\s+(.+)$', full_description, re.IGNORECASE)
            if code_match:
                fallback_code = code_match.group(1)
                full_description = code_match.group(2)
            else:
                fallback_code = None

            return self._apply_iva_normalization({
                'item_number':  item_num or row_index,
                'product_code': fallback_code,
                'description':  full_description,
                'reference':    reference,
                'unit_measure': unit,
                'quantity':     self._parse_decimal(clean_row[qty_idx]),
                'unit_price':   parse_colombian_amount(clean_row[price_idx]),
                'subtotal':     parse_colombian_amount(clean_row[subtotal_idx]),
                'iva_rate':     iva_rate,
            })

        # Last-resort: assume standard column order
        full_description = ' '.join(clean_row[1:-3]) if len(clean_row) > 3 else clean_row[0]
        if iva_rate is None:
            iva_rate = self._detect_iva_from_text(full_description)

        return self._apply_iva_normalization({
            'item_number':  row_index,
            'product_code': clean_row[0] if clean_row else None,
            'description':  full_description,
            'reference':    clean_row[0] if clean_row else None,
            'unit_measure': self._detect_unit_from_text(' '.join(clean_row)),
            'quantity':     self._parse_decimal(clean_row[-3]) if len(clean_row) >= 3 else None,
            'unit_price':   parse_colombian_amount(clean_row[-2]) if len(clean_row) >= 2 else None,
            'subtotal':     parse_colombian_amount(clean_row[-1]) if len(clean_row) >= 1 else None,
            'iva_rate':     iva_rate,
        })

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

        return None  # No se pudo detectar código — mejor None que texto basura

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

    def _auto_rotate_image(self, image_bytes: bytes) -> bytes:
        """
        Detecta y corrige la orientación de la imagen antes de enviar a Textract.
        1. Usa metadatos EXIF (tag 274 = Orientation) si existen.
        2. Heurística: si ancho > alto × 1.2 la foto de factura está girada → rotar 90°.
        """
        try:
            from PIL import Image
            import io as _io

            img = Image.open(_io.BytesIO(image_bytes))

            # Corregir por EXIF orientation
            try:
                exif = img._getexif()
                if exif:
                    orientation = exif.get(274)  # 274 = Orientation tag
                    rotations = {3: 180, 6: 270, 8: 90}
                    if orientation in rotations:
                        img = img.rotate(rotations[orientation], expand=True)
                        logger.info(
                            f"_auto_rotate_image: rotada {rotations[orientation]}° "
                            f"(EXIF orientation={orientation})"
                        )
            except Exception:
                pass  # Sin EXIF o EXIF inaccesible — continuar

            # Heurística de aspect ratio: facturas son más altas que anchas
            w, h = img.size
            if w > h * 1.2:
                img = img.rotate(90, expand=True)
                logger.info(f"_auto_rotate_image: rotada 90° por aspect ratio ({w}x{h})")

            output = _io.BytesIO()
            fmt = getattr(img, 'format', None) or 'JPEG'
            img.save(output, format=fmt, quality=95)
            return output.getvalue()

        except ImportError:
            logger.warning("PIL no instalado — se omite la rotación automática de imagen")
            return image_bytes
        except Exception as e:
            logger.warning(f"_auto_rotate_image falló ({e}) — se usa imagen original")
            return image_bytes

