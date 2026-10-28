from alembic import op
import sqlalchemy as sa

revision = "0004_customer_product_fields"
down_revision = "0003_commercial_ops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "cost_price",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    for field in ("icms_rate", "ipi_rate", "pis_rate", "cofins_rate"):
        op.add_column(
            "products",
            sa.Column(
                field,
                sa.Numeric(precision=5, scale=2),
                nullable=False,
                server_default="0",
            ),
        )
    op.create_check_constraint(
        "ck_products_cost_price_nonnegative", "products", "cost_price >= 0"
    )
    for field in ("icms_rate", "ipi_rate", "pis_rate", "cofins_rate"):
        op.create_check_constraint(
            f"ck_products_{field}_range",
            "products",
            f"{field} BETWEEN 0 AND 100",
        )

    op.add_column("customers", sa.Column("document", sa.String(length=14)))
    op.add_column("customers", sa.Column("address", sa.String(length=500)))
    op.add_column("customers", sa.Column("postal_code", sa.String(length=8)))


def downgrade() -> None:
    op.drop_column("customers", "postal_code")
    op.drop_column("customers", "address")
    op.drop_column("customers", "document")

    for field in ("icms_rate", "ipi_rate", "pis_rate", "cofins_rate"):
        op.drop_constraint(f"ck_products_{field}_range", "products", type_="check")
    op.drop_constraint("ck_products_cost_price_nonnegative", "products", type_="check")
    for field in ("cofins_rate", "pis_rate", "ipi_rate", "icms_rate", "cost_price"):
        op.drop_column("products", field)
