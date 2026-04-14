"""Link invoice_line_items to products; add Alegra sync fields to products

Gap crítico para integración Alegra: invoice_line_items necesita referenciar
products para obtener alegra_item_id sin matching en cada request.

Cambios:
  invoice_line_items.product_id  UUID FK → products.id  (nullable)
  products.alegra_item_id        VARCHAR(100)            (nullable, indexed)
  products.alegra_synced_at      TIMESTAMP               (nullable)

Post-DDL: popula product_id en filas existentes via product_code + tenant_id.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Campos Alegra en products ─────────────────────────────────────────
    op.add_column('products',
        sa.Column('alegra_item_id', sa.String(100), nullable=True))
    op.add_column('products',
        sa.Column('alegra_synced_at', sa.DateTime(), nullable=True))
    op.create_index('idx_products_alegra_item_id', 'products', ['alegra_item_id'])

    # ── 2. FK product_id en invoice_line_items ───────────────────────────────
    op.add_column('invoice_line_items',
        sa.Column('product_id', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_line_items_product_id',
        'invoice_line_items', 'products',
        ['product_id'], ['id'],
        ondelete='SET NULL',   # si se borra el producto la línea no pierde datos
    )
    op.create_index('idx_line_items_product_id', 'invoice_line_items', ['product_id'])

    # ── 3. Poblar product_id en filas existentes ─────────────────────────────
    # El JOIN va por: line_item → invoice (para obtener tenant_id) → product
    op.execute("""
        UPDATE invoice_line_items ili
        SET product_id = p.id
        FROM products p
        JOIN processed_invoices pi ON pi.tenant_id = p.tenant_id
        WHERE ili.invoice_id = pi.id
          AND ili.product_code = p.product_code
          AND ili.product_id IS NULL
    """)


def downgrade() -> None:
    op.drop_index('idx_line_items_product_id', 'invoice_line_items')
    op.drop_constraint('fk_line_items_product_id', 'invoice_line_items', type_='foreignkey')
    op.drop_column('invoice_line_items', 'product_id')

    op.drop_index('idx_products_alegra_item_id', 'products')
    op.drop_column('products', 'alegra_synced_at')
    op.drop_column('products', 'alegra_item_id')
