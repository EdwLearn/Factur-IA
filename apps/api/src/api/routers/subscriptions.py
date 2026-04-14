"""
Subscription management endpoints.

GET  /subscriptions/plans    — public list of available plans and pricing
GET  /subscriptions/current  — plan details for the authenticated tenant
GET  /subscriptions/usage    — invoice usage + days until monthly reset
POST /subscriptions/upgrade  — change plan (manual; no payment flow yet)
POST /subscriptions/webhook  — Wompi payment webhook (HMAC-validated skeleton)
"""
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from ...config.plans import PLANS, PlanConfig, get_plan
from ...core.config import settings
from ...database.connection import AsyncSessionFactory
from ...database.models import Tenant
from ..deps import get_tenant_id

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PlanResponse(BaseModel):
    name: str
    display_name: str
    price_cop: int
    invoice_limit: Optional[int]
    supplier_limit: Optional[int]
    history_days: Optional[int]
    max_users: int
    can_export: bool
    can_inventory: bool
    can_alerts: bool
    support_level: str

    @classmethod
    def from_config(cls, cfg: PlanConfig) -> "PlanResponse":
        return cls(**cfg.__dict__)


class CurrentSubscriptionResponse(BaseModel):
    tenant_id: str
    plan: str
    plan_details: PlanResponse
    billing_period_start: Optional[datetime]


class UsageResponse(BaseModel):
    invoice_count: int
    invoice_limit: Optional[int]   # None = unlimited
    days_until_reset: int
    plan: str


class UpgradeRequest(BaseModel):
    new_plan: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_tenant_or_404(tenant_id: str) -> Tenant:
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


def _days_until_reset(billing_period_start: Optional[datetime]) -> int:
    """Return days remaining in the current 30-day billing window (min 0)."""
    if billing_period_start is None:
        return 30
    elapsed = (datetime.utcnow() - billing_period_start).days
    return max(0, 30 - elapsed)


async def maybe_reset_invoice_counter(tenant_id: str) -> None:
    """
    Lazy billing-period reset: if 30+ days have elapsed since billing_period_start,
    reset invoices_processed_month to 0 and advance billing_period_start to today.

    Call this at the start of any operation that reads or enforces invoice limits.
    """
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return

        period_start = tenant.billing_period_start or datetime.utcnow()
        if (datetime.utcnow() - period_start).days >= 30:
            tenant.invoices_processed_month = 0
            tenant.billing_period_start = datetime.utcnow()
            await session.commit()
            logger.info(f"Billing period reset for tenant {tenant_id}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/plans",
    response_model=list[PlanResponse],
    summary="List all available plans",
)
async def list_plans() -> list[PlanResponse]:
    """Public endpoint — no authentication required."""
    return [PlanResponse.from_config(cfg) for cfg in PLANS.values()]


@router.get(
    "/current",
    response_model=CurrentSubscriptionResponse,
    summary="Get current subscription for authenticated tenant",
)
async def get_current_subscription(
    tenant_id: str = Depends(get_tenant_id),
) -> CurrentSubscriptionResponse:
    tenant = await _get_tenant_or_404(tenant_id)
    plan_cfg = get_plan(tenant.plan)
    return CurrentSubscriptionResponse(
        tenant_id=tenant.tenant_id,
        plan=tenant.plan,
        plan_details=PlanResponse.from_config(plan_cfg),
        billing_period_start=tenant.billing_period_start,
    )


@router.get(
    "/usage",
    response_model=UsageResponse,
    summary="Get invoice usage for the current billing period",
)
async def get_usage(
    tenant_id: str = Depends(get_tenant_id),
) -> UsageResponse:
    # Reset counter first if period has expired
    await maybe_reset_invoice_counter(tenant_id)

    tenant = await _get_tenant_or_404(tenant_id)
    plan_cfg = get_plan(tenant.plan)

    return UsageResponse(
        invoice_count=tenant.invoices_processed_month or 0,
        invoice_limit=plan_cfg.invoice_limit,
        days_until_reset=_days_until_reset(tenant.billing_period_start),
        plan=tenant.plan,
    )


@router.post(
    "/upgrade",
    summary="Change subscription plan (manual — no payment flow yet)",
)
async def upgrade_plan(
    body: UpgradeRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    if body.new_plan not in PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown plan '{body.new_plan}'. Valid values: {list(PLANS.keys())}",
        )

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        old_plan = tenant.plan
        tenant.plan = body.new_plan
        tenant.updated_at = datetime.utcnow()
        await session.commit()

    logger.info(f"Tenant {tenant_id} upgraded from {old_plan} to {body.new_plan}")
    new_cfg = get_plan(body.new_plan)
    return {
        "message": f"Plan updated to {new_cfg.display_name}",
        "old_plan": old_plan,
        "new_plan": body.new_plan,
        "new_plan_details": PlanResponse.from_config(new_cfg),
    }


# ---------------------------------------------------------------------------
# Wompi webhook skeleton
# ---------------------------------------------------------------------------

def _verify_wompi_signature(payload: bytes, signature_header: Optional[str], secret: str) -> bool:
    """
    Validate Wompi HMAC-SHA256 webhook signature.

    Wompi sends the signature as:  sha256=<hex_digest>
    in the X-Wompi-Signature header.

    Returns True when the signature is valid or when no secret is configured
    (dev mode — disable in production by ensuring WOMPI_WEBHOOK_SECRET is set).
    """
    if not secret:
        logger.warning("WOMPI_WEBHOOK_SECRET not set — skipping signature validation (dev mode)")
        return True

    if not signature_header:
        return False

    # Support both "sha256=<digest>" and raw hex formats
    expected_prefix = "sha256="
    if signature_header.startswith(expected_prefix):
        received_digest = signature_header[len(expected_prefix):]
    else:
        received_digest = signature_header

    expected_digest = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_digest, received_digest)


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Wompi payment webhook (HMAC validated)",
)
async def wompi_webhook(
    request: Request,
    x_wompi_signature: Optional[str] = Header(None, alias="X-Wompi-Signature"),
) -> dict[str, str]:
    """
    Skeleton endpoint for Wompi payment events.

    Signature validation is already wired up — just fill in the business logic
    inside the if/elif blocks when you connect a real Wompi account.
    """
    payload = await request.body()

    if not _verify_wompi_signature(payload, x_wompi_signature, settings.wompi_webhook_secret):
        logger.warning("Wompi webhook received with invalid signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    try:
        event = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    event_type: str = event.get("event", "unknown")
    logger.info(f"Wompi webhook received: event={event_type}")

    # TODO: implement handlers as you connect real Wompi payments
    if event_type == "transaction.updated":
        pass  # e.g. activate plan on successful payment
    elif event_type == "subscription.created":
        pass  # e.g. map Wompi subscription to tenant plan
    elif event_type == "subscription.cancelled":
        pass  # e.g. downgrade tenant to freemium

    return {"status": "received"}
