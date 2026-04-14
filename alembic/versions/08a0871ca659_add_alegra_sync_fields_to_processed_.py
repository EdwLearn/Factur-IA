"""add_alegra_sync_fields_to_processed_invoices

Agrega dos columnas a processed_invoices para registrar el resultado
del POST /bills a Alegra:

  alegra_sync_status  VARCHAR(50) nullable
    Valores: "synced" | "failed" | "pending" | null (no intentado)

  alegra_error  TEXT nullable
    Mensaje de error si el POST /bills falló. Truncado a 500 chars
    en la capa de servicio.

Revision ID: 08a0871ca659
Revises: 0007
Create Date: 2026-04-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '08a0871ca659'
down_revision = '0007'
branch_labels = None
depends_on = None


def column_exists(table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not column_exists("processed_invoices", "alegra_sync_status"):
        op.add_column(
            "processed_invoices",
            sa.Column("alegra_sync_status", sa.String(50), nullable=True),
        )

    if not column_exists("processed_invoices", "alegra_error"):
        op.add_column(
            "processed_invoices",
            sa.Column("alegra_error", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'processed_invoices'
                  AND column_name = 'alegra_error'
            ) THEN
                ALTER TABLE processed_invoices DROP COLUMN alegra_error;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'processed_invoices'
                  AND column_name = 'alegra_sync_status'
            ) THEN
                ALTER TABLE processed_invoices DROP COLUMN alegra_sync_status;
            END IF;
        END $$;
    """)
