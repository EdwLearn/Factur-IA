"""Add multi-page invoice support

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # parent_invoice_id — self-referential FK, nullable
    has_parent = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='processed_invoices' AND column_name='parent_invoice_id'"
    )).fetchone()
    if not has_parent:
        op.add_column(
            'processed_invoices',
            sa.Column(
                'parent_invoice_id',
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey('processed_invoices.id', ondelete='SET NULL'),
                nullable=True,
            )
        )
        op.create_index(
            'idx_parent_invoice_id',
            'processed_invoices',
            ['parent_invoice_id'],
        )

    # page_number
    has_page_number = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='processed_invoices' AND column_name='page_number'"
    )).fetchone()
    if not has_page_number:
        op.add_column(
            'processed_invoices',
            sa.Column('page_number', sa.Integer, nullable=True, server_default='1'),
        )

    # total_pages
    has_total_pages = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='processed_invoices' AND column_name='total_pages'"
    )).fetchone()
    if not has_total_pages:
        op.add_column(
            'processed_invoices',
            sa.Column('total_pages', sa.Integer, nullable=True, server_default='1'),
        )

    # is_consolidated
    has_consolidated = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='processed_invoices' AND column_name='is_consolidated'"
    )).fetchone()
    if not has_consolidated:
        op.add_column(
            'processed_invoices',
            sa.Column('is_consolidated', sa.Boolean, nullable=False, server_default='false'),
        )


def downgrade() -> None:
    op.drop_index('idx_parent_invoice_id', table_name='processed_invoices')
    op.drop_column('processed_invoices', 'is_consolidated')
    op.drop_column('processed_invoices', 'total_pages')
    op.drop_column('processed_invoices', 'page_number')
    op.drop_column('processed_invoices', 'parent_invoice_id')
