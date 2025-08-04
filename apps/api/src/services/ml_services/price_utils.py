# src/services/ml_services/price_utils.py
"""
Price rounding and formatting utilities for Colombian retail
"""
from decimal import Decimal, ROUND_UP
from typing import Union
import math

def round_price_colombian(price: Union[Decimal, float, int]) -> Decimal:
    """
    Round prices using Colombian retail conventions
    
    Rules:
    - Prices >= 10,000: Round to nearest 1,000 (10,800 → 11,000)
    - Prices >= 1,000: Round to nearest 500 (1,300 → 1,500)
    - Prices >= 100: Round to nearest 100 (180 → 200)
    - Prices < 100: Round to nearest 50 (80 → 100, 130 → 150)
    
    Args:
        price: Price to round
        
    Returns:
        Rounded price as Decimal
    """
    if price is None:
        return Decimal('0')
    
    price_decimal = Decimal(str(price))
    
    if price_decimal >= 10000:
        # Round to nearest 1,000 (always round up if remainder exists)
        return _round_to_nearest(price_decimal, 1000, always_up=True)
    
    elif price_decimal >= 1000:
        # Round to nearest 500
        return _round_to_nearest(price_decimal, 500)
    
    elif price_decimal >= 100:
        # Round to nearest 100
        return _round_to_nearest(price_decimal, 100)
    
    else:
        # Round to nearest 50
        return _round_to_nearest(price_decimal, 50)

def _round_to_nearest(price: Decimal, nearest: int, always_up: bool = False) -> Decimal:
    """Helper function to round to nearest value"""
    price_float = float(price)
    
    if always_up:
        # Always round up if there's any remainder
        rounded = math.ceil(price_float / nearest) * nearest
    else:
        # Standard rounding
        rounded = round(price_float / nearest) * nearest
    
    return Decimal(str(int(rounded)))

def format_colombian_price(price: Union[Decimal, float, int]) -> str:
    """
    Format price for Colombian display with thousands separators
    
    Args:
        price: Price to format
        
    Returns:
        Formatted price string (e.g., "$ 45.000")
    """
    if price is None:
        return "$ 0"
    
    price_decimal = Decimal(str(price))
    price_int = int(price_decimal)
    
    # Add thousands separators using Colombian format
    formatted = f"{price_int:,}".replace(",", ".")
    
    return f"$ {formatted}"

def calculate_rounded_margin(cost_price: Decimal, sale_price: Decimal) -> Decimal:
    """
    Calculate margin percentage with rounded sale price
    
    Args:
        cost_price: Original cost price
        sale_price: Rounded sale price
        
    Returns:
        Margin percentage as Decimal
    """
    if cost_price <= 0:
        return Decimal('0')
    
    margin = ((sale_price - cost_price) / cost_price) * 100
    return margin.quantize(Decimal('0.01'))

def suggest_price_alternatives(base_price: Decimal) -> dict:
    """
    Generate alternative price suggestions around the base price
    
    Args:
        base_price: Base calculated price
        
    Returns:
        Dictionary with different pricing strategies
    """
    rounded_price = round_price_colombian(base_price)
    
    alternatives = {
        'conservative': rounded_price,
        'standard': rounded_price,
        'aggressive': rounded_price
    }
    
    # Generate alternatives based on price range
    if rounded_price >= 10000:
        alternatives['conservative'] = rounded_price - 1000
        alternatives['aggressive'] = rounded_price + 1000
    elif rounded_price >= 1000:
        alternatives['conservative'] = rounded_price - 500
        alternatives['aggressive'] = rounded_price + 500
    else:
        alternatives['conservative'] = rounded_price - 100
        alternatives['aggressive'] = rounded_price + 100
    
    # Ensure all alternatives are properly rounded and positive
    for key in alternatives:
        if alternatives[key] < 0:
            alternatives[key] = round_price_colombian(base_price * Decimal('0.8'))
        else:
            alternatives[key] = round_price_colombian(alternatives[key])
    
    return alternatives

def validate_price_business_rules(cost_price: Decimal, sale_price: Decimal) -> dict:
    """
    Validate sale price against business rules
    
    Args:
        cost_price: Product cost price
        sale_price: Proposed sale price
        
    Returns:
        Validation result with warnings/suggestions
    """
    warnings = []
    suggestions = []
    
    if sale_price <= cost_price:
        warnings.append("Precio de venta menor o igual al costo")
        suggestions.append(f"Precio mínimo sugerido: {format_colombian_price(cost_price * Decimal('1.2'))}")
    
    margin = calculate_rounded_margin(cost_price, sale_price)
    
    if margin < 15:
        warnings.append(f"Margen muy bajo ({margin:.1f}%)")
        suggestions.append("Considere aumentar el precio para mejor rentabilidad")
    
    elif margin > 200:
        warnings.append(f"Margen muy alto ({margin:.1f}%)")
        suggestions.append("Precio podría ser poco competitivo")
    
    # Check if price follows Colombian conventions
    expected_rounded = round_price_colombian(sale_price)
    if sale_price != expected_rounded:
        suggestions.append(f"Precio redondeado sugerido: {format_colombian_price(expected_rounded)}")
    
    return {
        'is_valid': len(warnings) == 0,
        'warnings': warnings,
        'suggestions': suggestions,
        'margin_percentage': float(margin),
        'rounded_price': expected_rounded
    }

# Example usage and testing
def test_price_rounding():
    """Test function to validate rounding logic"""
    test_cases = [
        (10800, 11000),   # >= 10k: round to 1000s
        (15300, 16000),   # >= 10k: round to 1000s
        (9800, 10000),    # >= 1k: round to 500s
        (1300, 1500),     # >= 1k: round to 500s
        (1200, 1000),     # >= 1k: round to 500s (down)
        (450, 500),       # >= 100: round to 100s
        (180, 200),       # >= 100: round to 100s
        (80, 100),        # < 100: round to 50s
        (130, 150),       # < 100: round to 50s
    ]
    
    results = []
    for input_price, expected in test_cases:
        result = round_price_colombian(input_price)
        status = "✓" if result == expected else "✗"
        results.append(f"{status} {input_price} → {result} (expected: {expected})")
    
    return results