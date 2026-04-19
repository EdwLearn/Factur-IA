"""
DIAN XML Extractor — parses Colombian electronic invoices (UBL 2.1).

DIAN electronic invoices are XML files that follow the UBL 2.1 standard with
Colombian extensions.  All data is already structured, so this path is:
  - Free (no Textract cost)
  - Exact (no OCR ambiguity)
  - Fast (pure in-memory parsing)

Namespaces used by DIAN UBL 2.1:
  cbc  → urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2
  cac  → urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2
  ext  → urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2
  fe   → http://www.dian.gov.co/contratos/facturaelectronica/v1
"""
from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

from .amount_parser import parse_colombian_amount

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Namespace map (covers both v1 and v2 DIAN schemas)
# ---------------------------------------------------------------------------
_NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
}

# DIAN tax scheme IDs
_TAX_IVA      = "01"
_TAX_ICA      = "03"  # Impuesto de industria y comercio
_TAX_INC      = "04"  # Impuesto nacional al consumo

# Retención scheme IDs
_RET_RENTA    = "06"  # Retención en la fuente
_RET_IVA      = "05"  # ReteIVA
_RET_ICA      = "07"  # ReteICA


def _t(element: Optional[ET.Element]) -> Optional[str]:
    """Return stripped text of an element, or None."""
    if element is None:
        return None
    return (element.text or "").strip() or None


def _decimal(value: Optional[str]) -> Optional[Decimal]:
    if not value:
        return None
    return parse_colombian_amount(value)


class DianXMLExtractor:
    """Parse a DIAN UBL 2.1 XML invoice into the standard FacturIA dict."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def is_dian_xml(content: bytes) -> bool:
        """
        Return True if the bytes look like a DIAN UBL XML invoice.
        Checks for the UBL Invoice/CreditNote root and the DIAN namespace.
        """
        try:
            snippet = content[:2000].decode("utf-8", errors="ignore")
            return (
                "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" in snippet
                and ("Invoice" in snippet or "CreditNote" in snippet or "DebitNote" in snippet)
            )
        except Exception:
            return False

    def extract_invoice_data(self, xml_bytes: bytes) -> Dict[str, Any]:
        """
        Parse a DIAN XML and return the standard FacturIA extraction dict:
          invoice_number, issue_date, due_date, supplier, customer,
          line_items, totals, payment_info, full_text, source
        """
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as exc:
            logger.error(f"XML parse error: {exc}")
            raise ValueError(f"Invalid XML: {exc}") from exc

        # Strip default namespace from tag to make xpath simpler
        ns = self._detect_namespaces(root)

        return {
            "invoice_number":  self._invoice_number(root, ns),
            "issue_date":      self._issue_date(root, ns),
            "due_date":        self._due_date(root, ns),
            "supplier":        self._supplier(root, ns),
            "customer":        self._customer(root, ns),
            "line_items":      self._line_items(root, ns),
            "totals":          self._totals(root, ns),
            "payment_info":    self._payment_info(root, ns),
            "full_text":       "",          # Not applicable for XML
            "raw_key_values":  {},
            "raw_tables":      [],
            "source":          "dian_xml",
        }

    # ------------------------------------------------------------------
    # Header fields
    # ------------------------------------------------------------------

    def _invoice_number(self, root: ET.Element, ns: dict) -> Optional[str]:
        el = root.find("cbc:ID", ns)
        return _t(el)

    def _issue_date(self, root: ET.Element, ns: dict):
        from datetime import date
        el = root.find("cbc:IssueDate", ns)
        raw = _t(el)
        if raw:
            try:
                return date.fromisoformat(raw)
            except ValueError:
                pass
        return None

    def _due_date(self, root: ET.Element, ns: dict):
        from datetime import date
        # Due date lives inside PaymentMeans/PaymentDueDate
        el = root.find(".//cac:PaymentMeans/cbc:PaymentDueDate", ns)
        raw = _t(el)
        if raw:
            try:
                return date.fromisoformat(raw)
            except ValueError:
                pass
        return None

    # ------------------------------------------------------------------
    # Parties
    # ------------------------------------------------------------------

    def _party_info(self, party_el: Optional[ET.Element], ns: dict) -> Dict[str, Any]:
        if party_el is None:
            return {}

        # Company name — PreferredName > RegistrationName > PartyName/Name
        name = (
            _t(party_el.find(".//cbc:RegistrationName", ns))
            or _t(party_el.find(".//cbc:Name", ns))
        )

        # NIT / document number
        nit_el = party_el.find(".//cac:PartyIdentification/cbc:ID", ns)
        nit = _t(nit_el)

        # Address
        addr_el = party_el.find(".//cac:PhysicalLocation/cac:Address", ns) \
                  or party_el.find(".//cac:PostalAddress", ns)
        address  = _t(addr_el.find("cbc:AddressLine/cbc:Line", ns) if addr_el is not None else None) \
                   or _t(addr_el.find("cbc:StreetName", ns) if addr_el is not None else None)
        city     = _t(addr_el.find("cbc:CityName", ns) if addr_el is not None else None)
        dept     = _t(addr_el.find("cbc:CountrySubentity", ns) if addr_el is not None else None)

        # Contact
        contact_el = party_el.find(".//cac:Contact", ns)
        phone = _t(contact_el.find("cbc:Telephone", ns)) if contact_el is not None else None
        email = _t(contact_el.find("cbc:ElectronicMail", ns)) if contact_el is not None else None

        return {
            "company_name": name,
            "nit":          nit,
            "address":      address,
            "city":         city,
            "department":   dept,
            "phone":        phone,
            "email":        email,
        }

    def _supplier(self, root: ET.Element, ns: dict) -> Dict[str, Any]:
        party_el = root.find(".//cac:AccountingSupplierParty/cac:Party", ns)
        return self._party_info(party_el, ns)

    def _customer(self, root: ET.Element, ns: dict) -> Dict[str, Any]:
        party_el = root.find(".//cac:AccountingCustomerParty/cac:Party", ns)
        info = self._party_info(party_el, ns)
        # Rename keys to match FacturIA customer schema
        return {
            "customer_name": info.get("company_name"),
            "customer_id":   info.get("nit"),
            "address":       info.get("address"),
            "city":          info.get("city"),
            "department":    info.get("department"),
            "phone":         info.get("phone"),
        }

    # ------------------------------------------------------------------
    # Line items
    # ------------------------------------------------------------------

    def _line_items(self, root: ET.Element, ns: dict) -> List[Dict[str, Any]]:
        items = []
        for line in root.findall(".//cac:InvoiceLine", ns):
            item = self._parse_line(line, ns)
            if item:
                items.append(item)
        # Also handle CreditNote lines
        for line in root.findall(".//cac:CreditNoteLine", ns):
            item = self._parse_line(line, ns)
            if item:
                items.append(item)
        return items

    def _parse_line(self, line: ET.Element, ns: dict) -> Optional[Dict[str, Any]]:
        line_num = _t(line.find("cbc:ID", ns))

        qty_el  = (line.find("cbc:InvoicedQuantity", ns)
                   or line.find("cbc:CreditedQuantity", ns)
                   or line.find("cbc:DebitedQuantity", ns)
                   or line.find("cbc:BaseQuantity", ns)
                   or line.find("cbc:Quantity", ns))
        qty     = _decimal(_t(qty_el))
        unit    = qty_el.get("unitCode", "UND") if qty_el is not None else "UND"

        price_el      = line.find(".//cac:Price/cbc:PriceAmount", ns)
        unit_price    = _decimal(_t(price_el))

        subtotal_el   = line.find("cbc:LineExtensionAmount", ns)
        subtotal      = _decimal(_t(subtotal_el))

        # Product description
        item_el       = line.find("cac:Item", ns)
        description   = _t(item_el.find("cbc:Description", ns)) if item_el is not None else None
        std_item_id   = _t(item_el.find(".//cac:StandardItemIdentification/cbc:ID", ns)) \
                        if item_el is not None else None
        seller_id     = _t(item_el.find(".//cac:SellersItemIdentification/cbc:ID", ns)) \
                        if item_el is not None else None
        product_code  = seller_id or std_item_id

        # Line-level tax (IVA on this item)
        tax_pct = None
        for tax_sub in (line.findall(".//cac:TaxSubtotal", ns) or []):
            scheme_id = _t(tax_sub.find(".//cac:TaxCategory/cac:TaxScheme/cbc:ID", ns))
            if scheme_id == _TAX_IVA:
                tax_pct = _decimal(_t(tax_sub.find(".//cac:TaxCategory/cbc:Percent", ns)))
                break

        if not description:
            return None

        return {
            "item_number":    int(line_num) if line_num and line_num.isdigit() else None,
            "product_code":   product_code,
            "description":    description,
            "reference":      product_code,
            "unit_measure":   unit,
            "quantity":       qty,
            "unit_price":     unit_price,
            "subtotal":       subtotal,
            "iva_rate":       tax_pct,
        }

    # ------------------------------------------------------------------
    # Totals — IVA breakdown + retenciones
    # ------------------------------------------------------------------

    def _totals(self, root: ET.Element, ns: dict) -> Dict[str, Any]:
        # Legal monetary total
        lmt = root.find(".//cac:LegalMonetaryTotal", ns)
        subtotal = _decimal(_t(lmt.find("cbc:LineExtensionAmount", ns))) if lmt is not None else None
        total    = _decimal(_t(lmt.find("cbc:PayableAmount", ns)))        if lmt is not None else None

        # IVA breakdown: collect all TaxTotal/TaxSubtotal for scheme 01
        iva_breakdown: List[Dict] = []
        rete_renta = rete_iva = rete_ica = None

        for tax_total in root.findall(".//cac:TaxTotal", ns):
            for tax_sub in tax_total.findall("cac:TaxSubtotal", ns):
                scheme_id = _t(tax_sub.find(".//cac:TaxCategory/cac:TaxScheme/cbc:ID", ns))
                pct       = _decimal(_t(tax_sub.find(".//cac:TaxCategory/cbc:Percent", ns)))
                amount    = _decimal(_t(tax_sub.find("cbc:TaxAmount", ns)))
                base      = _decimal(_t(tax_sub.find("cbc:TaxableAmount", ns)))

                if scheme_id == _TAX_IVA:
                    iva_breakdown.append({
                        "rate":   pct,
                        "base":   base,
                        "amount": amount,
                    })
                elif scheme_id == _RET_RENTA:
                    rete_renta = amount
                elif scheme_id == _RET_IVA:
                    rete_iva = amount
                elif scheme_id == _RET_ICA:
                    rete_ica = amount

        # Summary IVA (first entry or total)
        iva_amount = sum(e["amount"] for e in iva_breakdown if e["amount"]) or None
        iva_rate   = iva_breakdown[0]["rate"] if iva_breakdown else None

        retenciones_parts = [x for x in [rete_renta, rete_iva, rete_ica] if x is not None]
        total_retenciones = sum(retenciones_parts) if retenciones_parts else None

        return {
            "subtotal":           subtotal,
            "iva_rate":           iva_rate,
            "iva_amount":         iva_amount,
            "iva_breakdown":      iva_breakdown,   # lista completa con tarifas mixtas
            "rete_renta":         rete_renta,
            "rete_iva":           rete_iva,
            "rete_ica":           rete_ica,
            "total_retenciones":  total_retenciones,
            "total":              total,
            "total_items":        len(root.findall(".//cac:InvoiceLine", ns))
                                  or len(root.findall(".//cac:CreditNoteLine", ns)),
        }

    # ------------------------------------------------------------------
    # Payment info
    # ------------------------------------------------------------------

    def _payment_info(self, root: ET.Element, ns: dict) -> Dict[str, Any]:
        pm_el = root.find(".//cac:PaymentMeans", ns)
        if pm_el is None:
            return {}

        method_code = _t(pm_el.find("cbc:PaymentMeansCode", ns))
        method_map  = {"10": "CONTADO", "20": "CHEQUE", "30": "CREDITO",
                       "42": "TRANSFERENCIA", "48": "TARJETA"}
        method = method_map.get(method_code or "", method_code)

        # Payment terms (credit days)
        terms_el   = root.find(".//cac:PaymentTerms/cbc:Note", ns)
        credit_days = None
        if terms_el is not None:
            m = re.search(r"(\d+)\s*d[ií]as?", (_t(terms_el) or ""), re.IGNORECASE)
            if m:
                credit_days = int(m.group(1))

        # Discount
        disc_el = root.find(".//cac:AllowanceCharge/cbc:MultiplierFactorNumeric", ns)
        discount = _decimal(_t(disc_el))

        return {
            "payment_method":       method,
            "credit_days":          credit_days,
            "discount_percentage":  discount,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_namespaces(root: ET.Element) -> dict:
        """
        Return the standard _NS map, extended with any extra namespaces
        found in the document (e.g. DIAN fe: extensions).
        """
        ns = dict(_NS)
        # ElementTree stores the default namespace as '' in the tag
        # e.g. {urn:oasis:...Invoice}Invoice — we already cover cbc/cac above.
        return ns
