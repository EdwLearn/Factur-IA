"""add duplicate detection fields

Revision ID: add_duplicate_fields_001
Revises: cf00ceb491a0
Create Date: 2025-07-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_duplicate_fields_001'
down_revision: Union[str, None] = 'cf00ceb491a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add fields for duplicate detection"""
    
    # Add duplicate resolution status to line items
    op.add_column('invoice_line_items', sa.Column('duplicate_resolution_status', sa.String(length=50), nullable=True))
    op.add_column('invoice_line_items', sa.Column('linked_product_id', sa.UUID(), nullable=True))
    op.add_column('invoice_line_items', sa.Column('similarity_score', sa.Numeric(precision=5, scale=4), nullable=True))
    
    # Add foreign key to products table
    op.create_foreign_key(
        'fk_line_items_linked_product', 
        'invoice_line_items', 
        'products', 
        ['linked_product_id'], 
        ['id']
    )
    
    # Create indexes for better performance
    op.create_index('idx_line_items_duplicate_status', 'invoice_line_items', ['duplicate_resolution_status'])
    op.create_index('idx_line_items_linked_product', 'invoice_line_items', ['linked_product_id'])
    
    # Add comments for documentation
    op.execute("""
        COMMENT ON COLUMN invoice_line_items.duplicate_resolution_status IS 'Status of duplicate resolution: pending, resolved_new, resolved_linked';
        COMMENT ON COLUMN invoice_line_items.linked_product_id IS 'ID of existing product if line item was linked to avoid duplication';
        COMMENT ON COLUMN invoice_line_items.similarity_score IS 'Similarity score with linked product (0.0-1.0)';
    """)


def downgrade() -> None:
    """Remove duplicate detection fields"""
    
    # Drop indexes
    op.drop_index('idx_line_items_linked_product', table_name='invoice_line_items')
    op.drop_index('idx_line_items_duplicate_status', table_name='invoice_line_items')
    
    # Drop foreign key
    op.drop_constraint('fk_line_items_linked_product', 'invoice_line_items', type_='foreignkey')
    
    # Drop columns
    op.drop_column('invoice_line_items', 'similarity_score')
    op.drop_column('invoice_line_items', 'linked_product_id')
    op.drop_column('invoice_line_items', 'duplicate_resolution_status')