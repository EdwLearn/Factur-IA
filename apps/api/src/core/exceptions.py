"""
Custom exceptions and error handlers.
"""

from typing import Any, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from .logging import get_logger

logger = get_logger(__name__)


class FacturiaException(Exception):
    """Base exception for FacturIA application."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[dict] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class InvoiceProcessingError(FacturiaException):
    """Invoice processing failed."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class TextractError(FacturiaException):
    """AWS Textract service error."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class S3Error(FacturiaException):
    """AWS S3 service error."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class TenantNotFoundError(FacturiaException):
    """Tenant not found."""

    def __init__(self, tenant_id: str):
        super().__init__(
            message=f"Tenant not found: {tenant_id}",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"tenant_id": tenant_id}
        )


class InvoiceNotFoundError(FacturiaException):
    """Invoice not found."""

    def __init__(self, invoice_id: str):
        super().__init__(
            message=f"Invoice not found: {invoice_id}",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"invoice_id": invoice_id}
        )


class DuplicateProductError(FacturiaException):
    """Duplicate product detected."""

    def __init__(self, product_code: str, similarity_score: float):
        super().__init__(
            message=f"Duplicate product detected: {product_code}",
            status_code=status.HTTP_409_CONFLICT,
            details={
                "product_code": product_code,
                "similarity_score": similarity_score
            }
        )


async def facturia_exception_handler(request: Request, exc: FacturiaException) -> JSONResponse:
    """Handle FacturIA custom exceptions."""
    logger.error(
        "facturia_exception",
        path=request.url.path,
        method=request.method,
        error=exc.message,
        status_code=exc.status_code,
        details=exc.details
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        "validation_error",
        path=request.url.path,
        method=request.method,
        errors=errors
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "ValidationError",
                "message": "Request validation failed",
                "details": {"errors": errors}
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception(
        "unexpected_error",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=exc
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "InternalServerError",
                "message": "An unexpected error occurred",
                "details": {}
            }
        }
    )
