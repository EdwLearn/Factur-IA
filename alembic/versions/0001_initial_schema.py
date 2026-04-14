"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2026-03-28

NOTE: This migration was created to match the existing SQLAlchemy models.
      To regenerate against a live DB run:
        alembic revision --autogenerate -m "describe_change"
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- tenants ---
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("nit", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("plan", sa.String(50), nullable=True),
        sa.Column("invoices_processed_month", sa.Integer(), nullable=True),
        sa.Column("max_invoices_month", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("integration_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenants_tenant_id", "tenants", ["tenant_id"], unique=True)

    # --- processed_invoices ---
    op.create_table(
        "processed_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(100), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("s3_key", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("processing_time_seconds", sa.Numeric(10, 3), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("upload_timestamp", sa.DateTime(), nullable=True),
        sa.Column("processing_timestamp", sa.DateTime(), nullable=True),
        sa.Column("completion_timestamp", sa.DateTime(), nullable=True),
        sa.Column("textract_job_id", sa.String(255), nullable=True),
        sa.Column("textract_raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("invoice_number", sa.String(100), nullable=True),
        sa.Column("invoice_type", sa.String(50), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("supplier_name", sa.String(255), nullable=True),
        sa.Column("supplier_nit", sa.String(50), nullable=True),
        sa.Column("supplier_address", sa.Text(), nullable=True),
        sa.Column("supplier_city", sa.String(100), nullable=True),
        sa.Column("supplier_department", sa.String(100), nullable=True),
        sa.Column("supplier_phone", sa.String(50), nullable=True),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column("customer_id", sa.String(50), nullable=True),
        sa.Column("customer_address", sa.Text(), nullable=True),
        sa.Column("customer_city", sa.String(100), nullable=True),
        sa.Column("customer_department", sa.String(100), nullable=True),
        sa.Column("customer_phone", sa.String(50), nullable=True),
        sa.Column("salesperson", sa.String(255), nullable=True),
        sa.Column("elaborated_by", sa.String(255), nullable=True),
        sa.Column("subtotal", sa.Numeric(15, 2), nullable=True),
        sa.Column("iva_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("iva_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("retenciones", sa.Numeric(15, 2), nullable=True),
        sa.Column("total_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("total_items", sa.Integer(), nullable=True),
        sa.Column("payment_method", sa.String(100), nullable=True),
        sa.Column("credit_days", sa.Integer(), nullable=True),
        sa.Column("discount_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("authorization", sa.Text(), nullable=True),
        sa.Column("cufe", sa.String(255), nullable=True),
        sa.Column("pricing_status", sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_processed_invoices_tenant_id", "processed_invoices", ["tenant_id"])
    op.create_index("ix_processed_invoices_status", "processed_invoices", ["status"])
    op.create_index("ix_processed_invoices_upload_timestamp", "processed_invoices", ["upload_timestamp"])
    op.create_index("ix_processed_invoices_invoice_number", "processed_invoices", ["invoice_number"])
    op.create_index("ix_processed_invoices_issue_date", "processed_invoices", ["issue_date"])
    op.create_index("ix_processed_invoices_supplier_nit", "processed_invoices", ["supplier_nit"])
    op.create_index("ix_processed_invoices_customer_name", "processed_invoices", ["customer_name"])
    op.create_index("ix_processed_invoices_total_amount", "processed_invoices", ["total_amount"])
    op.create_index("idx_tenant_status", "processed_invoices", ["tenant_id", "status"])
    op.create_index("idx_tenant_date", "processed_invoices", ["tenant_id", "issue_date"])
    op.create_index("idx_supplier_tenant", "processed_invoices", ["supplier_nit", "tenant_id"])

    # --- products ---
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(100), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("product_code", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("unit_measure", sa.String(50), nullable=True),
        sa.Column("current_stock", sa.Numeric(15, 4), nullable=True),
        sa.Column("min_stock", sa.Numeric(15, 4), nullable=True),
        sa.Column("max_stock", sa.Numeric(15, 4), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("sale_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("total_purchased", sa.Numeric(15, 4), nullable=True),
        sa.Column("total_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("last_purchase_date", sa.Date(), nullable=True),
        sa.Column("last_purchase_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])
    op.create_index("ix_products_product_code", "products", ["product_code"])
    op.create_index("idx_product_code_tenant", "products", ["product_code", "tenant_id"])

    # --- invoice_line_items ---
    op.create_table(
        "invoice_line_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("processed_invoices.id"), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("product_code", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("unit_measure", sa.String(50), nullable=True),
        sa.Column("box_number", sa.String(50), nullable=True),
        sa.Column("quantity", sa.Numeric(15, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(15, 2), nullable=False),
        sa.Column("sale_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("markup_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("is_priced", sa.Boolean(), nullable=False),
        sa.Column("original_quantity", sa.Numeric(15, 4), nullable=True),
        sa.Column("original_unit", sa.String(20), nullable=True),
        sa.Column("unit_multiplier", sa.Numeric(10, 2), nullable=True),
        sa.Column("item_number", sa.Integer(), nullable=True),
        sa.Column("enhancement_applied", sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_line_items_invoice_id", "invoice_line_items", ["invoice_id"])
    op.create_index("ix_invoice_line_items_product_code", "invoice_line_items", ["product_code"])
    op.create_index("idx_product_code_invoice", "invoice_line_items", ["product_code", "invoice_id"])

    # --- billing_records ---
    op.create_table(
        "billing_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(100), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("processed_invoices.id"), nullable=True),
        sa.Column("processing_date", sa.DateTime(), nullable=True),
        sa.Column("cost_cop", sa.Numeric(10, 2), nullable=False),
        sa.Column("invoice_type", sa.String(50), nullable=True),
        sa.Column("pages_processed", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_billing_records_tenant_id", "billing_records", ["tenant_id"])
    op.create_index("ix_billing_records_processing_date", "billing_records", ["processing_date"])

    # --- suppliers ---
    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(100), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("nit", sa.String(50), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("total_invoices", sa.Integer(), nullable=True),
        sa.Column("total_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("last_invoice_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_suppliers_tenant_id", "suppliers", ["tenant_id"])
    op.create_index("idx_supplier_nit_tenant", "suppliers", ["nit", "tenant_id"])

    # --- inventory_movements ---
    op.create_table(
        "inventory_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("movement_type", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Numeric(15, 4), nullable=False),
        sa.Column("reference_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("movement_date", sa.DateTime(), nullable=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("processed_invoices.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- defective_products ---
    op.create_table(
        "defective_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(15, 4), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_date", sa.DateTime(), nullable=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("processed_invoices.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("defective_products")
    op.drop_table("inventory_movements")
    op.drop_table("suppliers")
    op.drop_table("billing_records")
    op.drop_table("invoice_line_items")
    op.drop_table("products")
    op.drop_table("processed_invoices")
    op.drop_table("tenants")
