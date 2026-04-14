"""Add subscription fields to tenants table

Adds billing_period_start for the lazy monthly counter reset
and updates the plan column comment to reflect the new plan names
(freemium / basic / pro).

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-06
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add billing_period_start — defaults to now() so existing tenants
    # get a fresh 30-day window from the moment the migration runs.
    op.add_column(
        'tenants',
        sa.Column(
            'billing_period_start',
            sa.DateTime(),
            nullable=True,
            server_default=sa.func.now(),
        ),
    )

    # Back-fill NULL rows just in case server_default doesn't cover them
    op.execute(
        "UPDATE tenants SET billing_period_start = NOW() WHERE billing_period_start IS NULL"
    )

    # Normalise plan values: rename any legacy 'premium' rows to 'pro'
    op.execute("UPDATE tenants SET plan = 'pro' WHERE plan = 'premium'")


def downgrade() -> None:
    op.drop_column('tenants', 'billing_period_start')
    # Revert plan name change
    op.execute("UPDATE tenants SET plan = 'premium' WHERE plan = 'pro'")
