"""add unit conversion fields

Revision ID: add_unit_fields_001
Revises: cf00ceb491a0
Create Date: 2025-07-22 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_unit_fields_001'
down_revision: Union[str, None] = 'cf00ceb491a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unit conversion fields to invoice_line_items"""
    
    # Add new columns
    op.add_column('invoice_line_items', sa.Column('original_quantity', sa.Numeric(precision=15, scale=4), nullable=True))
    op.add_column('invoice_line_items', sa.Column('original_unit', sa.String(length=20), nullable=True))
    op.add_column('invoice_line_items', sa.Column('unit_multiplier', sa.Numeric(precision=10, scale=2), nullable=True, default=1))
    op.add_column('invoice_line_items', sa.Column('item_number', sa.Integer(), nullable=True))
    op.add_column('invoice_line_items', sa.Column('enhancement_applied', sa.String(length=100), nullable=True))
    
    # Create indexes
    op.create_index('idx_invoice_line_items_original_unit', 'invoice_line_items', ['original_unit'])
    op.create_index('idx_invoice_line_items_unit_multiplier', 'invoice_line_items', ['unit_multiplier'])
    op.create_index('idx_invoice_line_items_item_number', 'invoice_line_items', ['item_number'])
    
    # Update existing records
    op.execute("""
        UPDATE invoice_line_items 
        SET 
            original_quantity = quantity,
            original_unit = COALESCE(unit_measure, 'UND'),
            unit_multiplier = 1
        WHERE original_quantity IS NULL
    """)


def downgrade() -> None:
    """Remove unit conversion fields"""
    
    # Drop indexes
    op.drop_index('idx_invoice_line_items_item_number', table_name='invoice_line_items')
    op.drop_index('idx_invoice_line_items_unit_multiplier', table_name='invoice_line_items')
    op.drop_index('idx_invoice_line_items_original_unit', table_name='invoice_line_items')
    
    # Drop columns
    op.drop_column('invoice_line_items', 'enhancement_applied')
    op.drop_column('invoice_line_items', 'item_number')
    op.drop_column('invoice_line_items', 'unit_multiplier')
    op.drop_column('invoice_line_items', 'original_unit')
    op.drop_column('invoice_line_items', 'original_quantity')