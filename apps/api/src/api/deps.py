"""
Shared FastAPI dependencies.

get_tenant_id is the single source of truth for tenant identification.
It is JWT-aware: when a Bearer token is present it validates the token
and cross-checks that the tenant_id claim matches the x-tenant-id header.
When no token is provided it falls back to the header alone (dev / legacy).

This keeps the API backwards-compatible while adding security progressively
as the login flow is implemented.
"""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..core.security import decode_access_token

# Optional bearer — does NOT return 403 when the Authorization header is absent.
_optional_bearer = HTTPBearer(auto_error=False)


async def get_tenant_id(
    x_tenant_id: str = Header(..., description="Tenant identifier"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
) -> str:
    """
    Resolve and validate the current tenant_id.

    Behaviour:
    - JWT present  → decode token, verify tenant_id claim matches x-tenant-id header.
                     Admin tokens (is_admin=True) may access any tenant.
    - JWT absent   → accept x-tenant-id header as-is (development / migration period).

    Once a login endpoint exists and all clients send tokens, remove the
    JWT-absent fallback and make the Bearer token mandatory.
    """
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="x-tenant-id header is required",
        )

    if credentials:
        payload = decode_access_token(credentials.credentials)
        token_tenant: Optional[str] = payload.get("tenant_id")
        is_admin: bool = payload.get("is_admin", False)

        if not is_admin and token_tenant != x_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="x-tenant-id header does not match token claims",
            )

    return x_tenant_id
