"""
Shared utility for parsing Colombian monetary amounts.

Colombian invoices use two different conventions depending on the supplier:
  American: 19,545.70  (coma=miles, punto=decimal)
  European: 19.545,70  (punto=miles, coma=decimal)

This module provides a single canonical parser that handles both formats
plus edge-cases found in real PDFs ($ symbol, whitespace, letter prefixes).
"""
from decimal import Decimal
import re
import logging

logger = logging.getLogger(__name__)


def parse_colombian_amount(value: str) -> Decimal:
    """
    Parsea valores monetarios colombianos correctamente.

    Formatos soportados:
    - 19,545.70  → 19545.70 (americano: coma=miles)
    - 19.545,70  → 19545.70 (europeo: punto=miles)
    - 19545.70   → 19545.70 (sin separador miles)
    - 19545,70   → 19545.70 (coma decimal)
    - $19.545,70 → 19545.70 (con símbolo)
    - 910,829.78 → 910829.78
    """
    if not value:
        return Decimal('0')

    # Limpiar: quitar $, espacios, letras
    clean = re.sub(r'[^\d,\.]', '', str(value).strip())

    if not clean:
        return Decimal('0')

    has_comma = ',' in clean
    has_dot = '.' in clean

    if has_comma and has_dot:
        comma_pos = clean.rindex(',')
        dot_pos = clean.rindex('.')

        if dot_pos > comma_pos:
            # Americano: 19,545.70
            # punto=decimal, coma=miles
            clean = clean.replace(',', '')
        else:
            # Europeo: 19.545,70
            # coma=decimal, punto=miles
            clean = clean.replace('.', '').replace(',', '.')

    elif has_comma and not has_dot:
        parts = clean.split(',')
        last_part = parts[-1]
        if len(last_part) <= 2:
            # Decimal: 19,54 o 19545,70
            clean = clean.replace(',', '.')
        else:
            # Miles: 19,545
            clean = clean.replace(',', '')

    elif has_dot and not has_comma:
        parts = clean.split('.')
        last_part = parts[-1]
        if len(last_part) > 2:
            # Miles: 19.545
            clean = clean.replace('.', '')
        # Si len <= 2 → decimal normal, no tocar

    try:
        return Decimal(clean)
    except Exception:
        logger.warning(
            f"No se pudo parsear monto: {value!r} "
            f"→ clean={clean!r}"
        )
        return Decimal('0')


def _test_parse_colombian_amount():
    cases = [
        ("19,545.70",  Decimal("19545.70")),
        ("19.545,70",  Decimal("19545.70")),
        ("910,829.78", Decimal("910829.78")),
        ("148,547.35", Decimal("148547.35")),
        ("19545.70",   Decimal("19545.70")),
        ("$19.545,70", Decimal("19545.70")),
        ("0,00",       Decimal("0.00")),
        ("0.00",       Decimal("0.00")),
        ("52,800",     Decimal("52800")),
        ("3,300",      Decimal("3300")),
    ]
    all_pass = True
    for input_val, expected in cases:
        result = parse_colombian_amount(input_val)
        ok = result == expected
        if not ok:
            all_pass = False
        status = "✓" if ok else f"✗ got {result}"
        print(f"{input_val:15} → {expected:12} {status}")
    return all_pass


if __name__ == "__main__":
    _test_parse_colombian_amount()
