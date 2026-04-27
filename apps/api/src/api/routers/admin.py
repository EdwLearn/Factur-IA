"""
Admin router — protected endpoints for managing invitation codes.
Requires the X-Admin-Key header matching ADMIN_SECRET_KEY in settings.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from ...core.config import get_settings
from ...database.connection import AsyncSessionFactory
from ...database.models import InvitationCode

router = APIRouter()
settings = get_settings()


class CreateInviteCodeRequest(BaseModel):
    code: str
    plan: str = "pro"
    duration_days: int = 60
    max_uses: int = 1
    expires_at: Optional[datetime] = None


class InviteCodeResponse(BaseModel):
    id: str
    code: str
    plan: str
    duration_days: int
    max_uses: int
    current_uses: int
    is_active: bool
    created_at: Optional[datetime]
    expires_at: Optional[datetime]


def _require_admin(x_admin_key: str) -> None:
    if x_admin_key != settings.admin_secret_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key",
        )


@router.post(
    "/invitation-codes",
    response_model=InviteCodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new invitation code",
)
async def create_invitation_code(
    body: CreateInviteCodeRequest,
    x_admin_key: str = Header(...),
) -> InviteCodeResponse:
    _require_admin(x_admin_key)

    async with AsyncSessionFactory() as session:
        existing = await session.execute(
            select(InvitationCode).where(InvitationCode.code == body.code)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Code '{body.code}' already exists",
            )

        invite = InvitationCode(
            code=body.code,
            plan=body.plan,
            duration_days=body.duration_days,
            max_uses=body.max_uses,
            expires_at=body.expires_at,
        )
        session.add(invite)
        await session.commit()
        await session.refresh(invite)

    return InviteCodeResponse(
        id=str(invite.id),
        code=invite.code,
        plan=invite.plan,
        duration_days=invite.duration_days,
        max_uses=invite.max_uses,
        current_uses=invite.current_uses,
        is_active=invite.is_active,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
    )
