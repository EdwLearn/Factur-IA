"""Validation utilities."""

import re
from typing import Optional
from decimal import Decimal


def validate_tenant_id(tenant_id: str) -> bool:
    """Validate tenant ID format."""
    if not tenant_id or len(tenant_id) > 100:
        return False
    # Alphanumeric, hyphens, underscores only
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', tenant_id))


def validate_invoice_number(invoice_number: str) -> bool:
    """Validate invoice number format."""
    if not invoice_number or len(invoice_number) > 50:
        return False
    return True


def validate_price(price: Decimal) -> bool:
    """Validate price is positive and has max 2 decimal places."""
    if price < 0:
        return False
    return price.as_tuple().exponent >= -2


def validate_product_code(code: str) -> bool:
    """Validate product code format."""
    if not code or len(code) > 100:
        return False
    return True


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Validate Colombian phone number format."""
    # Remove common separators
    clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
    # Colombian numbers: 10 digits starting with 3 (mobile) or landline
    return bool(re.match(r'^(\+57)?[0-9]{10}$', clean_phone))
