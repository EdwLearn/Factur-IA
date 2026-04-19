"""add_document_type_to_processed_invoices

Agrega columna document_type a processed_invoices para distinguir
facturas de remisiones y otros documentos colombianos.

  document_type  VARCHAR(50) DEFAULT 'factura' NOT NULL
    Valores posibles: 'factura', 'remision', 'desconocido'

La migración es idempotente: verifica si la columna existe antes de crearla.

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = [c['name'] for c in inspector.get_columns('processed_invoices')]

    if 'document_type' not in cols:
        op.add_column(
            'processed_invoices',
            sa.Column(
                'document_type',
                sa.String(50),
                nullable=False,
                server_default='factura',
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = [c['name'] for c in inspector.get_columns('processed_invoices')]

    if 'document_type' in cols:
        op.drop_column('processed_invoices', 'document_type')
