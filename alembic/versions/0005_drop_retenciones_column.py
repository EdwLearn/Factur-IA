"""Drop redundant retenciones column from processed_invoices

The column `retenciones` (single Numeric field) was replaced in migration 0003
by four granular columns: rete_renta, rete_iva, rete_ica, total_retenciones.
However the column persisted in the database due to create_tables() re-adding it
from a stale model definition in development. This migration removes it permanently.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    if column_exists("processed_invoices", "retenciones"):
        op.drop_column("processed_invoices", "retenciones")


def downgrade() -> None:
    if not column_exists("processed_invoices", "retenciones"):
        op.add_column(
            "processed_invoices",
            sa.Column("retenciones", sa.Numeric(15, 2), nullable=True),
        )
