"""Make inventory_movements.product_id nullable

Necesario para registrar ventas de Alegra de productos que aún
no existen en el catálogo local de FacturIA.

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "inventory_movements",
        "product_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "inventory_movements",
        "product_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )
