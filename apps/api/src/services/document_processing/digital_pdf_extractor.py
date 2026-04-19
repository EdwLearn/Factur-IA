"""
DigitalPDFExtractor — fast, free extraction for digital PDFs.

A digital PDF has text already embedded (e.g. DIAN electronic invoices).
We extract it directly with pdfplumber instead of sending it to Textract,
saving cost and latency.

Scanned PDFs (images inside a PDF wrapper) and mobile photos still go
through the normal OpenCV → Textract path.
"""
from __future__ import annotations

import io
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber

logger = logging.getLogger(__name__)

# Minimum number of text characters across the first pages to consider
# a PDF "digital".  Scanned PDFs produce near-zero extractable text.
_MIN_TEXT_CHARS = 80


class DigitalPDFExtractor:
    """Extract structured invoice data from digital (text-bearing) PDFs."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def is_digital(pdf_bytes: bytes) -> bool:
        """
        Return True if the PDF contains extractable text.

        Checks the first 3 pages; a total of at least _MIN_TEXT_CHARS
        characters is required to be considered digital.
        """
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                total_text = ""
                for page in pdf.pages[:3]:
                    total_text += page.extract_text() or ""
            return len(total_text.strip()) >= _MIN_TEXT_CHARS
        except Exception as exc:
            logger.warning(f"Could not inspect PDF for text: {exc}")
            return False

    def extract_invoice_data(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract structured invoice fields from a digital PDF.

        Returns the same dict structure expected by invoice_processor:
          invoice_number, issue_date, due_date, supplier, customer,
          line_items, totals, payment_info, full_text
        """
        lines, tables, full_text = self._parse_pdf(pdf_bytes)
        key_values = self._extract_key_values(lines)

        # Reuse the field-parsing methods from TextractService via lazy import
        # to avoid a circular dependency.  We instantiate the service without
        # making any AWS calls.
        from .textract.textract_service import TextractService
        _parser = TextractService.__new__(TextractService)

        return {
            "invoice_number": _parser._extract_invoice_number(lines, key_values),
            "issue_date": _parser._extract_date(lines, key_values, "fecha"),
            "due_date": _parser._extract_date(lines, key_values, "vencimiento"),
            "supplier": _parser._extract_supplier_info(lines, key_values),
            "customer": _parser._extract_customer_info(lines, key_values),
            "line_items": _parser._extract_line_items(tables, lines),
            "totals": _parser._extract_totals(lines, key_values),
            "payment_info": _parser._extract_payment_info(lines, key_values),
            "full_text": full_text,
            "raw_tables": tables,
            "raw_key_values": key_values,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_pdf(
        self, pdf_bytes: bytes
    ) -> Tuple[List[str], List[Dict], str]:
        """
        Use pdfplumber to extract:
          - lines  : list of non-empty text lines across all pages
          - tables : list of {rows, row_count, col_count} dicts (same
                     format as TextractService._parse_table output)
          - full_text: entire document text joined by newlines
        """
        lines: List[str] = []
        tables: List[Dict] = []

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                all_page_tables: List[Dict] = []  # Todas las tablas antes de fusionar

                for page in pdf.pages:
                    # Text lines
                    raw_text = page.extract_text() or ""
                    page_lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
                    lines.extend(page_lines)

                    # Tables — recopilar por página antes de fusionar
                    for raw_table in page.extract_tables() or []:
                        if not raw_table:
                            continue
                        # Normalize cells: replace None with empty string
                        clean_rows = [
                            [str(cell) if cell is not None else "" for cell in row]
                            for row in raw_table
                        ]
                        if clean_rows:
                            all_page_tables.append({
                                "rows": clean_rows,
                                "row_count": len(clean_rows),
                                "col_count": max(len(r) for r in clean_rows),
                            })

                # Fusionar tablas multipágina: si dos tablas consecutivas tienen el
                # mismo col_count, se asume que la segunda es continuación de la primera.
                # Se omiten filas de encabezado repetidas en páginas 2+.
                for tbl in all_page_tables:
                    if not tables:
                        tables.append(tbl)
                        continue
                    prev = tables[-1]
                    if prev["col_count"] == tbl["col_count"]:
                        header_first_cell = prev["rows"][0][0] if prev["rows"] else None
                        continuation_rows = [
                            row for row in tbl["rows"]
                            if not (row and row[0] == header_first_cell)
                        ]
                        if continuation_rows:
                            prev["rows"].extend(continuation_rows)
                            prev["row_count"] = len(prev["rows"])
                            logger.info(
                                f"Tabla multipágina: fusionadas {len(continuation_rows)} "
                                f"filas adicionales (col_count={prev['col_count']})"
                            )
                    else:
                        tables.append(tbl)

        except Exception as exc:
            logger.error(f"pdfplumber extraction failed: {exc}")

        full_text = "\n".join(lines)
        return lines, tables, full_text

    def _extract_key_values(self, lines: List[str]) -> Dict[str, str]:
        """
        Build a key→value dict from lines that follow the pattern
        'Key: Value' or 'Key  Value' — common in Colombian invoices.
        """
        key_values: Dict[str, str] = {}
        for line in lines:
            # Pattern: "some label: some value"
            match = re.match(r"^(.{3,40}?)\s*:\s*(.+)$", line)
            if match:
                key = match.group(1).strip().lower()
                value = match.group(2).strip()
                key_values[key] = value
        return key_values
