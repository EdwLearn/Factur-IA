"""Add rotation fields to inventory_movements

Agrega campos necesarios para calcular rotación de inventario
conectando ventas de Alegra con el inventario de FacturIA.

MIGRACIÓN ADITIVA — no modifica ni elimina columnas existentes.

Columnas nuevas en inventory_movements:
  - tenant_id    VARCHAR(255) nullable
  - product_code VARCHAR(100) nullable
  - description  TEXT nullable
  - tipo         VARCHAR(20)  nullable  ("entrada" | "salida")
  - origen       VARCHAR(50)  nullable  ("factura_compra" | "factura_venta_alegra" | "manual")
  - origen_id    VARCHAR(100) nullable  (id factura en Alegra)
  - unit_price   NUMERIC(15,2) nullable
  - fecha        DATE nullable
  - created_at   TIMESTAMP nullable DEFAULT NOW()

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def column_exists(table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not column_exists("inventory_movements", "tenant_id"):
        op.add_column(
            "inventory_movements",
            sa.Column("tenant_id", sa.String(255), nullable=True)
        )

    if not column_exists("inventory_movements", "product_code"):
        op.add_column(
            "inventory_movements",
            sa.Column("product_code", sa.String(100), nullable=True)
        )

    if not column_exists("inventory_movements", "description"):
        op.add_column(
            "inventory_movements",
            sa.Column("description", sa.Text(), nullable=True)
        )

    if not column_exists("inventory_movements", "tipo"):
        op.add_column(
            "inventory_movements",
            sa.Column("tipo", sa.String(20), nullable=True)
        )

    if not column_exists("inventory_movements", "origen"):
        op.add_column(
            "inventory_movements",
            sa.Column("origen", sa.String(50), nullable=True)
        )

    if not column_exists("inventory_movements", "origen_id"):
        op.add_column(
            "inventory_movements",
            sa.Column("origen_id", sa.String(100), nullable=True)
        )

    if not column_exists("inventory_movements", "unit_price"):
        op.add_column(
            "inventory_movements",
            sa.Column("unit_price", sa.Numeric(15, 2), nullable=True)
        )

    if not column_exists("inventory_movements", "fecha"):
        op.add_column(
            "inventory_movements",
            sa.Column("fecha", sa.Date(), nullable=True)
        )

    if not column_exists("inventory_movements", "created_at"):
        op.add_column(
            "inventory_movements",
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=True,
                server_default=sa.text("NOW()")
            )
        )

    # Índice para la query principal de rotación
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_inv_mov_rotation
        ON inventory_movements (tenant_id, tipo, origen, fecha)
    """))

    # Índice de deduplicación para sync idempotente
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_inv_mov_origen_id
        ON inventory_movements (tenant_id, origen, origen_id)
    """))


def downgrade() -> None:
    op.execute(text("DROP INDEX IF EXISTS idx_inv_mov_rotation"))
    op.execute(text("DROP INDEX IF EXISTS idx_inv_mov_origen_id"))

    for col in ["created_at", "fecha", "unit_price", "origen_id",
                "origen", "tipo", "description", "product_code", "tenant_id"]:
        if column_exists("inventory_movements", col):
            op.drop_column("inventory_movements", col)
