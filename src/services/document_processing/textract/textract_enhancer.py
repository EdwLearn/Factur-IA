# src/services/document_processing/textract/textract_enhancer.py
"""
Data cleaning and enhancement for Textract responses
Handles Colombian invoice-specific parsing issues
"""
import re
import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

class TextractDataEnhancer:
    """
    Enhance and clean Textract-extracted data for Colombian invoices
    """
    
    def __init__(self):
        # Unit conversion mapping
        self.unit_conversions = {
            'DOC': 12,      # Docena
            'DOCENA': 12,   # Docena (español)
            'PAR': 2,       # Par
            'PARES': 2,     # Pares
            'GRS': 144,     # Gruesa (12 docenas)
            'GRUESA': 144,  # Gruesa
            'PCS': 1,       # Piezas
            'UND': 1,       # Unidad
            'UNIDAD': 1,    # Unidad
            'PIEZA': 1,     # Pieza
            'KG': 1,        # Kilogramo (sin conversión por ahora)
            'G': 1,         # Gramo
            'L': 1,         # Litro
            'ML': 1,        # Mililitro
        }
    
    def enhance_extracted_data(self, raw_data: Dict) -> Dict:
        """
        Main enhancement function - cleans all extracted data
        
        Args:
            raw_data: Raw data from Textract service
            
        Returns:
            Enhanced and cleaned data
        """
        enhanced_data = raw_data.copy()
        
        # 1. Clean and enhance line items
        if 'line_items' in enhanced_data:
            enhanced_data['line_items'] = self._enhance_line_items(enhanced_data['line_items'])
        
        # 2. Clean text fields
        enhanced_data = self._clean_text_fields(enhanced_data)
        
        # 3. Validate data consistency
        warnings = self._validate_enhanced_data(enhanced_data)
        enhanced_data['enhancement_warnings'] = warnings
        
        logger.info(f"Enhanced data with {len(warnings)} warnings")
        return enhanced_data
    
    def _enhance_line_items(self, line_items: List[Dict]) -> List[Dict]:
        """Enhance line items with Colombian-specific corrections"""
        enhanced_items = []
        
        for i, item in enumerate(line_items):
            try:
                enhanced_item = item.copy()
                
                # 1. Separate ITEM number from product code
                enhanced_item = self._separate_item_and_ref(enhanced_item, i + 1)
                
                # 2. Convert units to pieces
                enhanced_item = self._convert_units_to_pieces(enhanced_item)
                
                # 3. Clean and validate fields
                enhanced_item = self._clean_line_item_fields(enhanced_item)
                
                # 4. Recalculate subtotal if needed
                enhanced_item = self._recalculate_subtotal(enhanced_item)
                
                enhanced_items.append(enhanced_item)
                
            except Exception as e:
                logger.warning(f"Error enhancing line item {i}: {str(e)}")
                # Keep original item if enhancement fails
                enhanced_items.append(item)
        
        return enhanced_items
    
    def _separate_item_and_ref(self, item: Dict, line_number: int) -> Dict:
        """
        Separate item number from product reference
        Example: "1 049 (DAMA)" → item=1, ref="049 (DAMA)"
        """
        product_code = item.get('product_code', '').strip()
        
        if not product_code:
            return item
        
        # Pattern 1: Number + space + rest (most common)
        # "1 049 (DAMA)" → groups: ("1", "049 (DAMA)")
        pattern1 = r'^(\d+)\s+(.+)$'
        match1 = re.match(pattern1, product_code)
        
        if match1:
            extracted_item_num = match1.group(1)
            clean_ref = match1.group(2)
            
            # Validate: extracted number should match line position
            if int(extracted_item_num) == line_number:
                item['item_number'] = int(extracted_item_num)
                item['product_code'] = clean_ref
                item['_enhancement_applied'] = 'item_ref_separated'
                
                logger.debug(f"✅ Separated: '{product_code}' → item={extracted_item_num}, ref='{clean_ref}'")
                return item
        
        # Pattern 2: Item number at start with different separators
        # "1. ABC123" or "1) XYZ-789"
        pattern2 = r'^(\d+)[\.\)\s]+(.+)$'
        match2 = re.match(pattern2, product_code)
        
        if match2:
            extracted_item_num = match2.group(1)
            clean_ref = match2.group(2)
            
            if int(extracted_item_num) == line_number:
                item['item_number'] = int(extracted_item_num)
                item['product_code'] = clean_ref
                item['_enhancement_applied'] = 'item_ref_separated_alt'
                
                logger.debug(f"✅ Separated (alt): '{product_code}' → item={extracted_item_num}, ref='{clean_ref}'")
                return item
        
        # If no pattern matches, keep original but set item number
        if 'item_number' not in item:
            item['item_number'] = line_number
        
        return item
    
    def _convert_units_to_pieces(self, item: Dict) -> Dict:
        """
        Convert units to individual pieces
        Example: 1 DOC → 12 PCS
        """
        quantity = item.get('quantity')
        unit = item.get('unit_measure', '').strip().upper()
        
        if not quantity or not unit:
            return item
        
        # Store original values
        item['original_quantity'] = quantity
        item['original_unit'] = unit
        
        # Get conversion multiplier
        multiplier = self.unit_conversions.get(unit, 1)
        
        if multiplier != 1:
            try:
                original_qty = Decimal(str(quantity))
                converted_quantity = original_qty * Decimal(str(multiplier))
                
                # Update item
                item['quantity'] = converted_quantity
                item['unit_measure'] = 'PCS'  # Convert to pieces
                item['unit_multiplier'] = multiplier
                item['_enhancement_applied'] = f'unit_converted_{unit}_to_PCS'
                
                # Update subtotal if we have unit price
                if item.get('unit_price'):
                    # Unit price should now be per piece
                    original_unit_price = Decimal(str(item['unit_price']))
                    new_unit_price = original_unit_price / Decimal(str(multiplier))
                    item['unit_price'] = new_unit_price
                
                logger.info(f"🔄 Unit conversion: {original_qty} {unit} → {converted_quantity} PCS (x{multiplier})")
                
            except Exception as e:
                logger.warning(f"Error converting units for {item.get('product_code')}: {str(e)}")
                item['unit_multiplier'] = 1
        else:
            item['unit_multiplier'] = 1
        
        return item
    
    def _clean_line_item_fields(self, item: Dict) -> Dict:
        """Clean text fields in line items"""
        
        # Clean product code
        if item.get('product_code'):
            # Remove extra spaces and normalize
            clean_code = re.sub(r'\s+', ' ', str(item['product_code']).strip())
            # Remove common prefixes that got mixed in
            clean_code = re.sub(r'^(REF|CODIGO|COD|ITEM|#)\s*:?\s*', '', clean_code, flags=re.IGNORECASE)
            item['product_code'] = clean_code
        
        # Clean description
        if item.get('description'):
            clean_desc = re.sub(r'\s+', ' ', str(item['description']).strip())
            # Remove obvious OCR artifacts
            clean_desc = re.sub(r'[^\w\s\(\)\-\.]', '', clean_desc)
            item['description'] = clean_desc
        
        # Clean and validate numeric fields
        for field in ['quantity', 'unit_price', 'subtotal']:
            if field in item:
                item[field] = self._clean_decimal_field(item[field])
        
        return item
    
    def _recalculate_subtotal(self, item: Dict) -> Dict:
        """Recalculate subtotal if quantity or unit_price changed"""
        try:
            quantity = item.get('quantity')
            unit_price = item.get('unit_price')
            
            if quantity and unit_price:
                calculated_subtotal = Decimal(str(quantity)) * Decimal(str(unit_price))
                
                # Check if current subtotal is significantly different
                current_subtotal = item.get('subtotal')
                if current_subtotal:
                    current_subtotal = Decimal(str(current_subtotal))
                    difference_pct = abs((calculated_subtotal - current_subtotal) / current_subtotal) * 100
                    
                    if difference_pct > 5:  # More than 5% difference
                        item['subtotal'] = calculated_subtotal
                        item['_subtotal_recalculated'] = True
                        logger.debug(f"📊 Recalculated subtotal: {current_subtotal} → {calculated_subtotal}")
                else:
                    item['subtotal'] = calculated_subtotal
                    item['_subtotal_calculated'] = True
                    
        except Exception as e:
            logger.warning(f"Error recalculating subtotal: {str(e)}")
        
        return item
    
    def _clean_decimal_field(self, value) -> Optional[Decimal]:
        """Clean and convert decimal field"""
        if value is None:
            return None
        
        try:
            # Convert to string first
            str_value = str(value).strip()
            
            # Remove currency symbols and spaces
            cleaned = re.sub(r'[\$\s]', '', str_value)
            
            # Handle Colombian number format (dots as thousand separators)
            # 1.234.567,89 → 1234567.89
            if ',' in cleaned and '.' in cleaned:
                # Both comma and dot present - dot is thousands, comma is decimal
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif cleaned.count('.') > 1:
                # Multiple dots - they're thousand separators except the last one
                parts = cleaned.split('.')
                if len(parts[-1]) == 2:  # Last part is 2 digits - it's decimal
                    cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
                else:  # All dots are thousand separators
                    cleaned = ''.join(parts)
            
            return Decimal(cleaned)
            
        except Exception as e:
            logger.warning(f"Error cleaning decimal field '{value}': {str(e)}")
            return None
    
    def _clean_text_fields(self, data: Dict) -> Dict:
        """Clean text fields in main data structure"""
        
        # Clean supplier info
        if 'supplier' in data:
            supplier = data['supplier']
            for field in ['company_name', 'nit', 'address', 'city']:
                if field in supplier and supplier[field]:
                    supplier[field] = self._clean_text_string(supplier[field])
        
        # Clean customer info
        if 'customer' in data:
            customer = data['customer']
            for field in ['customer_name', 'customer_id', 'address', 'city']:
                if field in customer and customer[field]:
                    customer[field] = self._clean_text_string(customer[field])
        
        # Clean invoice fields
        for field in ['invoice_number']:
            if field in data and data[field]:
                data[field] = self._clean_text_string(data[field])
        
        return data
    
    def _clean_text_string(self, text: str) -> str:
        """Clean individual text string"""
        if not text:
            return text
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', str(text).strip())
        
        # Remove common OCR artifacts
        cleaned = re.sub(r'[^\w\s\-\.\(\)\,\:]', '', cleaned)
        
        return cleaned
    
    def _validate_enhanced_data(self, data: Dict) -> List[str]:
        """Validate enhanced data and return warnings"""
        warnings = []
        
        # Validate line items
        line_items = data.get('line_items', [])
        for i, item in enumerate(line_items, 1):
            
            # Check for missing essential data
            if not item.get('description'):
                warnings.append(f"Línea {i}: descripción faltante")
            
            if not item.get('quantity') or item.get('quantity') <= 0:
                warnings.append(f"Línea {i}: cantidad inválida ({item.get('quantity')})")
            
            if not item.get('unit_price') or item.get('unit_price') <= 0:
                warnings.append(f"Línea {i}: precio unitario inválido ({item.get('unit_price')})")
            
            # Check for suspiciously high unit conversions
            multiplier = item.get('unit_multiplier', 1)
            if multiplier > 100:
                warnings.append(f"Línea {i}: conversión de unidades muy alta ({multiplier}x) - verificar")
            
            # Check subtotal consistency
            if item.get('_subtotal_recalculated'):
                warnings.append(f"Línea {i}: subtotal recalculado automáticamente")
        
        # Validate totals
        if data.get('totals'):
            totals = data['totals']
            if totals.get('total') and totals.get('total') <= 0:
                warnings.append("Total de factura inválido o cero")
        
        return warnings

# Function to integrate with existing textract_service.py
def enhance_textract_response(raw_textract_data: Dict) -> Dict:
    """
    Convenience function to enhance textract data
    Can be called from existing textract_service.py
    """
    enhancer = TextractDataEnhancer()
    return enhancer.enhance_extracted_data(raw_textract_data)