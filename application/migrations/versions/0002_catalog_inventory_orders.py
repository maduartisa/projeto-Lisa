from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_catalog_orders"
down_revision = "0001_identity_tenants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("stock_quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("price >= 0", name="ck_products_price_nonnegative"),
        sa.CheckConstraint(
            "stock_quantity >= 0", name="ck_products_stock_nonnegative"
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_products_tenant_id"),
        sa.UniqueConstraint("tenant_id", "sku", name="uq_products_tenant_sku"),
    )
    op.create_index(
        "ix_products_tenant_category", "products", ["tenant_id", "category"]
    )

    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_customers_tenant_id"),
    )
    op.create_index("ix_customers_tenant_name", "customers", ["tenant_id", "name"])

    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("fulfillment_method", sa.String(length=16), nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('quote', 'pending', 'separating', 'ready_for_pickup', "
            "'in_transit', 'completed', 'cancelled')",
            name="ck_orders_status",
        ),
        sa.CheckConstraint(
            "source IN ('counter', 'catalog', 'whatsapp')",
            name="ck_orders_source",
        ),
        sa.CheckConstraint(
            "fulfillment_method IN ('counter', 'pickup', 'delivery')",
            name="ck_orders_fulfillment_method",
        ),
        sa.CheckConstraint("total >= 0", name="ck_orders_total_nonnegative"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "customer_id"],
            ["customers.tenant_id", "customers.id"],
            ondelete="RESTRICT",
            name="fk_orders_customer_same_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_orders_tenant_id"),
    )
    op.create_index(
        "ix_orders_tenant_status_created",
        "orders",
        ["tenant_id", "status", "created_at"],
    )

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.CheckConstraint(
            "quantity > 0", name="ck_order_items_quantity_positive"
        ),
        sa.CheckConstraint(
            "unit_price >= 0", name="ck_order_items_price_nonnegative"
        ),
        sa.CheckConstraint(
            "line_total >= 0", name="ck_order_items_total_nonnegative"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "order_id"],
            ["orders.tenant_id", "orders.id"],
            ondelete="CASCADE",
            name="fk_order_items_order_same_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["products.tenant_id", "products.id"],
            ondelete="RESTRICT",
            name="fk_order_items_product_same_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("movement_type", sa.String(length=16), nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity_delta != 0", name="ck_inventory_delta_nonzero"),
        sa.CheckConstraint(
            "movement_type IN ('initial', 'adjustment', 'sale')",
            name="ck_inventory_movement_type",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["products.tenant_id", "products.id"],
            ondelete="RESTRICT",
            name="fk_inventory_product_same_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_movements_tenant_product_created",
        "inventory_movements",
        ["tenant_id", "product_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inventory_movements_tenant_product_created",
        table_name="inventory_movements",
    )
    op.drop_table("inventory_movements")
    op.drop_table("order_items")
    op.drop_index("ix_orders_tenant_status_created", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_customers_tenant_name", table_name="customers")
    op.drop_table("customers")
    op.drop_index("ix_products_tenant_category", table_name="products")
    op.drop_table("products")
