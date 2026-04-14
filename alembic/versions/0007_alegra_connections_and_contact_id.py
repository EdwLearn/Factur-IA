"""Add alegra_connections table and suppliers.alegra_contact_id

Tablas/campos necesarios para el flujo completo de integración Alegra:

  alegra_connections  (tabla nueva)
    - Un registro por tenant, guarda el token encriptado
    - unique(tenant_id) — un tenant solo puede tener una conexión activa

  suppliers.alegra_contact_id
    - ID del proveedor en Alegra, obtenido de GET /contacts
    - Evita buscar el contacto en cada POST /bills

Nota: la tabla puede ya existir si create_tables() la creó desde el modelo.
La migración es idempotente — usa IF NOT EXISTS / IF EXISTS en cada paso.

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def table_exists(name: str) -> bool:
    return inspect(op.get_bind()).has_table(name)


def column_exists(table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    # ── 1. alegra_connections ────────────────────────────────────────────────
    if not table_exists("alegra_connections"):
        op.create_table(
            "alegra_connections",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.String(100),
                      sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
                      nullable=False),
            sa.Column("alegra_token", sa.Text(), nullable=False),
            sa.Column("alegra_user_email", sa.String(255), nullable=False),
            sa.Column("alegra_company_name", sa.String(255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("connected_at", sa.DateTime(), nullable=False,
                      server_default=sa.func.now()),
            sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        )

    # Unique constraint e index — usamos SQL directo para IF NOT EXISTS
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_alegra_connections_tenant_id'
            ) THEN
                ALTER TABLE alegra_connections
                ADD CONSTRAINT uq_alegra_connections_tenant_id UNIQUE (tenant_id);
            END IF;
        END $$;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_alegra_connections_tenant_id
        ON alegra_connections (tenant_id);
    """)

    # ── 2. suppliers.alegra_contact_id ───────────────────────────────────────
    if not column_exists("suppliers", "alegra_contact_id"):
        op.add_column("suppliers",
            sa.Column("alegra_contact_id", sa.String(100), nullable=True))
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_suppliers_alegra_contact_id
        ON suppliers (alegra_contact_id);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_suppliers_alegra_contact_id")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='suppliers' AND column_name='alegra_contact_id'
            ) THEN
                ALTER TABLE suppliers DROP COLUMN alegra_contact_id;
            END IF;
        END $$;
    """)

    op.execute("DROP INDEX IF EXISTS idx_alegra_connections_tenant_id")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_alegra_connections_tenant_id'
            ) THEN
                ALTER TABLE alegra_connections
                DROP CONSTRAINT uq_alegra_connections_tenant_id;
            END IF;
        END $$;
    """)
    op.execute("DROP TABLE IF EXISTS alegra_connections")
