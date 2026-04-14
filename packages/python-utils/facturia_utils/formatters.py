"""Formatting utilities."""

from decimal import Decimal
from typing import Optional


def format_currency(amount: Decimal, currency: str = "COP") -> str:
    """Format currency for Colombian Peso."""
    if currency == "COP":
        # Colombian format: $1.234.567
        amount_str = f"{int(amount):,}".replace(",", ".")
        return f"${amount_str}"
    return f"{currency} {amount:,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage."""
    return f"{value:.{decimals}f}%"


def round_colombian_price(price: Decimal, round_to: int = 1000) -> Decimal:
    """
    Round price to Colombian-friendly amounts.

    Examples:
        10,800 -> 11,000
        15,300 -> 15,000
        1,250 -> 1,500
    """
    price_int = int(price)

    if round_to == 1000:
        # Round to nearest 1000
        rounded = round(price_int / 1000) * 1000
    elif round_to == 500:
        # Round to nearest 500
        rounded = round(price_int / 500) * 500
    elif round_to == 100:
        # Round to nearest 100
        rounded = round(price_int / 100) * 100
    else:
        rounded = price_int

    return Decimal(str(rounded))


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to max length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def normalize_product_name(name: str) -> str:
    """Normalize product name for comparison."""
    # Lowercase, remove extra spaces, remove special chars
    normalized = name.lower().strip()
    normalized = " ".join(normalized.split())
    return normalized
