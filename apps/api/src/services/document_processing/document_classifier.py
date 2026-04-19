"""
DocumentClassifier — clasifica documentos como factura, remisión o desconocido.

Analiza los primeros 1000 caracteres del texto extraído para decidir el tipo
de documento antes de intentar crear una factura en Alegra.
"""
import logging

logger = logging.getLogger(__name__)


class DocumentClassifier:

    REMISION_KEYWORDS = [
        "remisión", "remision",
        "remisión de mercancía", "remision de mercancia",
        "remisión mercancía", "remision mercancia",
        "despacho de mercancía", "despacho de mercancia",
        "remisión de despacho", "remision de despacho",
        "nota de remisión", "nota de remision",
        "nota despacho",
        "remito",
        "remisión pxf", "remision pxf",
    ]

    FACTURA_KEYWORDS = [
        "factura", "factura electrónica", "factura de venta",
        "invoice", "cufe",
    ]

    @staticmethod
    def classify_document(text: str) -> str:
        """
        Retorna: "factura", "remision", o "desconocido".

        Analiza los primeros 1000 caracteres del texto — algunos PDFs tienen
        el título de remisión más abajo en el encabezado.
        Remisión gana ante empate (conservador: no crear bill en Alegra por error).
        """
        text_lower = text[:1000].lower()

        remision_score = sum(
            1 for kw in DocumentClassifier.REMISION_KEYWORDS
            if kw in text_lower
        )
        factura_score = sum(
            1 for kw in DocumentClassifier.FACTURA_KEYWORDS
            if kw in text_lower
        )

        if remision_score > factura_score:
            doc_type = "remision"
        elif factura_score > 0:
            doc_type = "factura"
        else:
            doc_type = "desconocido"

        logger.info(
            f"Document classified as: {doc_type}, "
            f"remision_score={remision_score}, factura_score={factura_score}"
        )
        return doc_type
