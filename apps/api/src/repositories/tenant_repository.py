"""
TenantRepository — all database access for Tenant and related config.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Tenant


class TenantRepository:
    """Encapsulates every query that touches the tenants table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_tenant_id(self, tenant_id: str) -> Optional[Tenant]:
        """Return the tenant row, or None if not found."""
        result = await self._session.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update_integration_config(
        self, tenant: Tenant, config: Dict[str, Any]
    ) -> None:
        """Persist a new integration_config on an already-loaded tenant object."""
        tenant.integration_config = config
        await self._session.commit()
