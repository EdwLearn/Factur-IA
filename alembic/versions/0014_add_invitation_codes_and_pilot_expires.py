"""Add invitation_codes table and pilot_expires_at to tenants

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invitation_codes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("plan", sa.String(20), nullable=False, server_default="pro"),
        sa.Column("duration_days", sa.Integer, nullable=False, server_default="60"),
        sa.Column("max_uses", sa.Integer, nullable=False, server_default="1"),
        sa.Column("current_uses", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=True,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("expires_at", sa.DateTime, nullable=True),
    )
    op.create_unique_constraint(
        "uq_invitation_codes_code",
        "invitation_codes",
        ["code"],
    )
    op.create_index("idx_invitation_codes_code", "invitation_codes", ["code"])

    op.add_column(
        "tenants",
        sa.Column("pilot_expires_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "pilot_expires_at")
    op.drop_table("invitation_codes")
