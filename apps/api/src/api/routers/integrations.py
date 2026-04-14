"""
Integrations router.

POST /integrations/alegra/connect  — save & validate Alegra token
GET  /integrations/alegra/status   — check live connection status
DELETE /integrations/alegra/disconnect — remove stored token
"""
import logging
from datetime import datetime, timezone
from typing import List

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select

from ...database.connection import AsyncSessionFactory
from ...database.models import Product, Tenant
from ...services.integrations.alegra_integration import (
    AlegraClient,
    build_integration_config,
    extract_alegra_config,
    get_client_from_config,
)
from ...services.integrations.inventory_sync_service import inventory_sync_service
from ..deps import get_tenant_id

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AlegraConnectRequest(BaseModel):
    email: str
    token: str


class AlegraUserInfo(BaseModel):
    id: str | None = None
    email: str | None = None
    role: str | None = None
    status: str | None = None


class AlegraConnectResponse(BaseModel):
    connected: bool
    message: str
    user: AlegraUserInfo
    connected_at: str


class AlegraStatusResponse(BaseModel):
    connected: bool
    email: str | None = None
    user_id: str | None = None
    user_role: str | None = None
    connected_at: str | None = None
    live_check: bool = False
    synced_items: int = 0
    last_sync: str | None = None


class AlegraSyncResponse(BaseModel):
    pushed_items: int
    updated_items: int
    pulled_items: int
    synced_contacts: int
    synced_items: int
    errors: List[str]
    synced_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/alegra/connect",
    response_model=AlegraConnectResponse,
    status_code=status.HTTP_200_OK,
    summary="Connect Alegra account via API token",
)
async def connect_alegra(
    body: AlegraConnectRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> AlegraConnectResponse:
    """
    Validates the Alegra token against the live API, then encrypts it
    with Fernet and stores it in tenant.integration_config.

    Body: { "email": "user@example.com", "token": "<alegra-api-token>" }
    """
    logger.info(f"Connect request received: email={body.email!r} token_len={len(body.token)}")
    # 1. Validate token against Alegra API
    client = AlegraClient(email=body.email, token=body.token)
    try:
        user_info = await client.get_current_user()
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de Alegra inválido. Verifica el email y el token en tu perfil de Alegra.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Alegra API respondió con error {code}.",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo conectar con Alegra: {exc}",
        )

    # 2. Encrypt and persist
    new_config = build_integration_config(
        email=body.email,
        raw_token=body.token,
        user_info=user_info,
    )

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Merge: keep other integrations (e.g. Mayasis), only update alegra key
        existing = dict(tenant.integration_config or {})
        existing.update(new_config)
        tenant.integration_config = existing
        tenant.updated_at = datetime.utcnow()
        await session.commit()

    logger.info(f"Alegra connected for tenant {tenant_id} (user: {user_info.get('email')})")

    return AlegraConnectResponse(
        connected=True,
        message="Alegra conectado exitosamente.",
        user=AlegraUserInfo(
            id=str(user_info.get("id")),
            email=user_info.get("email"),
            role=user_info.get("role"),
            status=user_info.get("status"),
        ),
        connected_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/alegra/status",
    response_model=AlegraStatusResponse,
    summary="Check Alegra integration status",
)
async def alegra_status(
    tenant_id: str = Depends(get_tenant_id),
) -> AlegraStatusResponse:
    """
    Returns whether Alegra is connected.
    Performs a live check against the Alegra API to confirm the token
    is still valid (not just that it exists in the DB).
    """
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    cfg = extract_alegra_config(tenant.integration_config)

    if not cfg or cfg.get("status") != "active":
        return AlegraStatusResponse(connected=False)

    # Live check
    live_ok = False
    try:
        client = get_client_from_config(tenant.integration_config)
        await client.get_current_user()
        live_ok = True
    except Exception as exc:
        logger.warning(f"Alegra live check failed for tenant {tenant_id}: {exc}")

    # Contar productos ya sincronizados con Alegra
    synced_items = 0
    last_sync: str | None = None
    async with AsyncSessionFactory() as session:
        row = (await session.execute(
            select(
                func.count(Product.id).label("cnt"),
                func.max(Product.alegra_synced_at).label("last"),
            ).where(
                Product.tenant_id == tenant_id,
                Product.alegra_item_id.isnot(None),
            )
        )).one_or_none()
        if row:
            synced_items = int(row.cnt or 0)
            last_sync = row.last.isoformat() if row.last else None

    return AlegraStatusResponse(
        connected=live_ok,
        email=cfg.get("email"),
        user_id=str(cfg.get("user_id")) if cfg.get("user_id") else None,
        user_role=cfg.get("user_role"),
        connected_at=cfg.get("connected_at"),
        live_check=live_ok,
        synced_items=synced_items,
        last_sync=last_sync,
    )


@router.post(
    "/alegra/sync-items",
    response_model=AlegraSyncResponse,
    summary="Sync inventory with Alegra",
)
async def sync_alegra_items(
    tenant_id: str = Depends(get_tenant_id),
) -> AlegraSyncResponse:
    """
    Sincronización bidireccional FacturIA ↔ Alegra:
    - PULL: actualiza precios locales desde Alegra
    - PUSH: crea/actualiza ítems en Alegra con datos locales
    - CONTACTS: sincroniza proveedores como contactos en Alegra
    """
    # Verificar que Alegra esté conectado
    async with AsyncSessionFactory() as session:
        tenant = (await session.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant no encontrado")

    cfg = extract_alegra_config(tenant.integration_config)
    if not cfg or cfg.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alegra no está conectado. Ve a Configuración → Integraciones.",
        )

    result = await inventory_sync_service.sync_tenant(tenant_id)

    return AlegraSyncResponse(**result.to_dict())


@router.delete(
    "/alegra/disconnect",
    status_code=status.HTTP_200_OK,
    summary="Remove Alegra integration",
)
async def disconnect_alegra(
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Remove the stored Alegra token from this tenant."""
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        config = dict(tenant.integration_config or {})
        config.pop("alegra", None)
        tenant.integration_config = config
        tenant.updated_at = datetime.utcnow()
        await session.commit()

    logger.info(f"Alegra disconnected for tenant {tenant_id}")
    return {"message": "Integración con Alegra eliminada."}
