"""Add password_hash column to tenants

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-28

Adds an optional password_hash column to the tenants table so tenants
can authenticate via POST /auth/login and receive a JWT access token.
Existing rows are left with NULL (the API's dev fallback in deps.py
continues to work without a password while tenants are migrated).
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("password_hash", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "password_hash")
