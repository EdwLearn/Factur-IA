"""
Authentication router — tenant registration and login.

POST /auth/register  → creates a new tenant with hashed password
POST /auth/login     → validates credentials, returns JWT access token

The JWT payload includes `tenant_id` so that deps.get_tenant_id can
cross-check it against the x-tenant-id header on every protected endpoint.
"""
from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from ...core.security import create_access_token, hash_password, verify_password
from ...core.config import get_settings
from ...database.connection import AsyncSessionFactory
from ...database.models import Tenant

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


class LoginRequest(BaseModel):
    tenant_id: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    company_name: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new tenant",
)
async def register(body: RegisterRequest) -> TokenResponse:
    """
    Create a new tenant account.

    Returns a JWT token so the caller can start using protected endpoints
    immediately after registration.
    """
    async with AsyncSessionFactory() as session:
        # Check that tenant_id is not already taken
        existing = await session.execute(
            select(Tenant).where(Tenant.tenant_id == body.tenant_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"tenant_id '{body.tenant_id}' is already registered",
            )

        tenant = Tenant(
            tenant_id=body.tenant_id,
            company_name=body.company_name,
            email=body.email,
            nit=body.nit,
            phone=body.phone,
            password_hash=hash_password(body.password),
            plan="freemium",
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


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and obtain a JWT access token",
)
async def login(body: LoginRequest) -> TokenResponse:
    """
    Authenticate a tenant with their tenant_id and password.

    Returns a JWT access token. Include it in subsequent requests as:
        Authorization: Bearer <token>
    """
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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _issue_token(tenant: Tenant) -> str:
    """Build and sign a JWT for the given tenant."""
    return create_access_token(
        data={
            "sub": tenant.tenant_id,
            "tenant_id": tenant.tenant_id,
            "company_name": tenant.company_name,
            "is_admin": False,
        },
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
