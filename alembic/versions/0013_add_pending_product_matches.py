"""Add pending_product_matches table

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pending_product_matches",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.String(100),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processed_invoices.id"),
            nullable=False,
        ),
        sa.Column(
            "line_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoice_line_items.id"),
            nullable=False,
        ),
        sa.Column("line_item_description", sa.Text, nullable=False),
        sa.Column("alegra_product_id", sa.String(100), nullable=False),
        sa.Column("alegra_product_name", sa.Text, nullable=False),
        sa.Column("match_score", sa.Integer, nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "idx_pending_matches_tenant_status",
        "pending_product_matches",
        ["tenant_id", "status"],
    )
    op.create_unique_constraint(
        "uq_pending_matches_line_item",
        "pending_product_matches",
        ["line_item_id"],
    )
    op.create_index(
        "idx_pending_matches_invoice",
        "pending_product_matches",
        ["invoice_id"],
    )


def downgrade() -> None:
    op.drop_table("pending_product_matches")
