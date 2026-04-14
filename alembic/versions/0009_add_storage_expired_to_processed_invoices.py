"""add_storage_expired_to_processed_invoices

Agrega columna a processed_invoices para rastrear facturas
cuyo archivo S3 fue eliminado por expiración del plan.

  storage_expired  BOOLEAN DEFAULT FALSE NOT NULL
    True  → el archivo S3 fue borrado por el cleanup job.
    False → archivo todavía disponible (o nunca tuvo s3_key).

Revision ID: 0009
Revises: 08a0871ca659
Create Date: 2026-04-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0009'
down_revision = '08a0871ca659'
branch_labels = None
depends_on = None


def column_exists(table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not column_exists("processed_invoices", "storage_expired"):
        op.add_column(
            "processed_invoices",
            sa.Column(
                "storage_expired",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'processed_invoices'
                  AND column_name = 'storage_expired'
            ) THEN
                ALTER TABLE processed_invoices DROP COLUMN storage_expired;
            END IF;
        END $$;
    """)
