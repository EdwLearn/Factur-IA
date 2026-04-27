"""
Authentication router — tenant registration and login.

POST /auth/register  → creates a new tenant with hashed password
POST /auth/login     → validates credentials, returns JWT access token
GET  /auth/validate-invite → validates an invitation code

The JWT payload includes `tenant_id` so that deps.get_tenant_id can
cross-check it against the x-tenant-id header on every protected endpoint.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from ...core.security import create_access_token, hash_password, verify_password
from ...core.config import get_settings
from ...database.connection import AsyncSessionFactory
from ...database.models import Tenant, InvitationCode
from ..deps import get_tenant_id

router = APIRouter()
settings = get_settings()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    tenant_id: str
    company_name: str
    email: EmailStr
    password: str
    nit: str | None = None
    phone: str | None = None
    invitation_code: Optional[str] = None


class LoginRequest(BaseModel):
    tenant_id: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    company_name: str


class InviteValidationResponse(BaseModel):
    valid: bool
    plan: str
    duration_days: int
    message: str


class TenantProfileResponse(BaseModel):
    tenant_id: str
    company_name: str
    nit: Optional[str]
    email: str
    phone: Optional[str]
    plan: str


class UpdateProfileRequest(BaseModel):
    company_name: Optional[str] = None
    nit: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_valid_invite(session, code: str) -> InvitationCode:
    """Fetch and validate an invitation code; raises HTTPException on failure."""
    result = await session.execute(
        select(InvitationCode).where(InvitationCode.code == code)
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Código inválido")
    if not invite.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código desactivado")
    if invite.current_uses >= invite.max_uses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código agotado")
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código expirado")

    return invite


def _issue_token(tenant: Tenant) -> str:
    return create_access_token(
        data={
            "sub": tenant.tenant_id,
            "tenant_id": tenant.tenant_id,
            "company_name": tenant.company_name,
            "is_admin": False,
        },
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/validate-invite",
    response_model=InviteValidationResponse,
    summary="Validate an invitation code",
)
async def validate_invite(code: str = Query(...)) -> InviteValidationResponse:
    async with AsyncSessionFactory() as session:
        invite = await _get_valid_invite(session, code)

    return InviteValidationResponse(
        valid=True,
        plan=invite.plan,
        duration_days=invite.duration_days,
        message=f"¡Código válido! Tendrás Plan Pro gratis por {invite.duration_days} días",
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new tenant",
)
async def register(body: RegisterRequest) -> TokenResponse:
    async with AsyncSessionFactory() as session:
        existing = await session.execute(
            select(Tenant).where(Tenant.tenant_id == body.tenant_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"tenant_id '{body.tenant_id}' is already registered",
            )

        plan = "freemium"
        pilot_expires_at = None

        if body.invitation_code:
            invite = await _get_valid_invite(session, body.invitation_code)
            plan = invite.plan
            pilot_expires_at = datetime.utcnow() + timedelta(days=invite.duration_days)
            invite.current_uses += 1

        tenant = Tenant(
            tenant_id=body.tenant_id,
            company_name=body.company_name,
            email=body.email,
            nit=body.nit,
            phone=body.phone,
            password_hash=hash_password(body.password),
            plan=plan,
            pilot_expires_at=pilot_expires_at,
            max_invoices_month=10,
            invoices_processed_month=0,
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

    token = _issue_token(tenant)
    return TokenResponse(
        access_token=token,
        tenant_id=tenant.tenant_id,
        company_name=tenant.company_name,
    )


@router.get(
    "/me",
    response_model=TenantProfileResponse,
    summary="Get current tenant profile",
)
async def get_me(tenant_id: str = Depends(get_tenant_id)) -> TenantProfileResponse:
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    return TenantProfileResponse(
        tenant_id=tenant.tenant_id,
        company_name=tenant.company_name,
        nit=tenant.nit,
        email=tenant.email,
        phone=tenant.phone,
        plan=tenant.plan,
    )


@router.patch(
    "/me",
    response_model=TenantProfileResponse,
    summary="Update current tenant profile",
)
async def update_me(
    body: UpdateProfileRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> TenantProfileResponse:
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

        if body.company_name is not None:
            tenant.company_name = body.company_name
        if body.nit is not None:
            tenant.nit = body.nit
        if body.email is not None:
            tenant.email = body.email
        if body.phone is not None:
            tenant.phone = body.phone

        await session.commit()
        await session.refresh(tenant)

    return TenantProfileResponse(
        tenant_id=tenant.tenant_id,
        company_name=tenant.company_name,
        nit=tenant.nit,
        email=tenant.email,
        phone=tenant.phone,
        plan=tenant.plan,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and obtain a JWT access token",
)
async def login(body: LoginRequest) -> TokenResponse:
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.tenant_id == body.tenant_id)
        )
        tenant = result.scalar_one_or_none()

    if not tenant or not tenant.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not verify_password(body.password, tenant.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    token = _issue_token(tenant)
    return TokenResponse(
        access_token=token,
        tenant_id=tenant.tenant_id,
        company_name=tenant.company_name,
    )
