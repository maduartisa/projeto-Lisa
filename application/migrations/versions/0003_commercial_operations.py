from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_commercial_ops"
down_revision = "0002_catalog_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("size", sa.String(length=64), nullable=True))
    op.add_column("products", sa.Column("color", sa.String(length=64), nullable=True))
    op.drop_constraint(
        "ck_inventory_movement_type", "inventory_movements", type_="check"
    )
    op.create_check_constraint(
        "ck_inventory_movement_type",
        "inventory_movements",
        "movement_type IN ('initial', 'adjustment', 'sale', 'purchase')",
    )
    op.add_column(
        "tenant_memberships",
        sa.Column("display_name", sa.String(length=160), nullable=True),
    )
    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("document", sa.String(length=32), nullable=True),
        sa.Column("contact_name", sa.String(length=160), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_suppliers_tenant_id"),
    )
    op.create_index("ix_suppliers_tenant_name", "suppliers", ["tenant_id", "name"])
    op.create_table(
        "purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'received', 'cancelled')",
            name="ck_purchases_status",
        ),
        sa.CheckConstraint("total >= 0", name="ck_purchases_total_nonnegative"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "supplier_id"],
            ["suppliers.tenant_id", "suppliers.id"],
            ondelete="RESTRICT",
            name="fk_purchases_supplier_same_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_purchases_tenant_id"),
    )
    op.create_index("ix_purchases_tenant_created", "purchases", ["tenant_id", "created_at"])
    op.create_table(
        "purchase_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_purchase_items_quantity_positive"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_purchase_items_cost_nonnegative"),
        sa.CheckConstraint("line_total >= 0", name="ck_purchase_items_total_nonnegative"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "purchase_id"],
            ["purchases.tenant_id", "purchases.id"],
            ondelete="CASCADE",
            name="fk_purchase_items_purchase_same_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["products.tenant_id", "products.id"],
            ondelete="RESTRICT",
            name="fk_purchase_items_product_same_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "financial_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_type", sa.String(length=16), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "entry_type IN ('payable', 'receivable')",
            name="ck_financial_entries_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'settled', 'cancelled')",
            name="ck_financial_entries_status",
        ),
        sa.CheckConstraint("amount > 0", name="ck_financial_entries_amount_positive"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_financial_entries_tenant_due",
        "financial_entries",
        ["tenant_id", "due_date"],
    )
    op.create_table(
        "access_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=240), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_access_logs_tenant_created",
        "access_logs",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_access_logs_tenant_created", table_name="access_logs")
    op.drop_table("access_logs")
    op.drop_index("ix_financial_entries_tenant_due", table_name="financial_entries")
    op.drop_table("financial_entries")
    op.drop_table("purchase_items")
    op.drop_index("ix_purchases_tenant_created", table_name="purchases")
    op.drop_table("purchases")
    op.drop_index("ix_suppliers_tenant_name", table_name="suppliers")
    op.drop_table("suppliers")
    op.drop_column("tenant_memberships", "display_name")
    op.drop_constraint(
        "ck_inventory_movement_type", "inventory_movements", type_="check"
    )
    op.create_check_constraint(
        "ck_inventory_movement_type",
        "inventory_movements",
        "movement_type IN ('initial', 'adjustment', 'sale')",
    )
    op.drop_column("products", "color")
    op.drop_column("products", "size")
