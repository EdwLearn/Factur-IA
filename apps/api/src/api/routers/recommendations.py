"""
Endpoints de recomendaciones inteligentes de inventario.
"""

from fastapi import APIRouter, Depends, HTTPException
import logging

from ..deps import get_tenant_id
from ...services.ml_services.recommendation_service import recommendation_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/",
    summary="Recomendaciones de inventario",
    description=(
        "Retorna dos tipos de recomendaciones accionables:\n\n"
        "- **restock**: productos por debajo del stock mínimo con cantidad sugerida de compra\n"
        "- **dead_stock**: productos sin movimiento con capital inmovilizado y alternativas de reinversión"
    ),
)
async def get_recommendations(tenant_id: str = Depends(get_tenant_id)):
    try:
        return await recommendation_service.get_recommendations(tenant_id)
    except Exception as exc:
        logger.error(f"Error generando recomendaciones para {tenant_id}: {exc}")
        raise HTTPException(status_code=500, detail="Error al generar recomendaciones")
