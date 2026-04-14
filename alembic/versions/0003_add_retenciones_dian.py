"""Add DIAN retenciones columns to processed_invoices

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('processed_invoices', sa.Column('rete_renta', sa.Numeric(15, 2), nullable=True))
    op.add_column('processed_invoices', sa.Column('rete_iva', sa.Numeric(15, 2), nullable=True))
    op.add_column('processed_invoices', sa.Column('rete_ica', sa.Numeric(15, 2), nullable=True))
    op.add_column('processed_invoices', sa.Column('total_retenciones', sa.Numeric(15, 2), nullable=True))
    # Drop the old single-column retenciones if it exists
    op.drop_column('processed_invoices', 'retenciones')


def downgrade() -> None:
    op.add_column('processed_invoices', sa.Column('retenciones', sa.Numeric(15, 2), nullable=True))
    op.drop_column('processed_invoices', 'total_retenciones')
    op.drop_column('processed_invoices', 'rete_ica')
    op.drop_column('processed_invoices', 'rete_iva')
    op.drop_column('processed_invoices', 'rete_renta')
