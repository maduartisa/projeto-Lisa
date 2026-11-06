from alembic import op
import sqlalchemy as sa

revision = "0006_purchase_nfe"
down_revision = "0005_product_fiscal_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchases", sa.Column("invoice_access_key", sa.String(length=44)))
    op.add_column("purchases", sa.Column("invoice_number", sa.String(length=20)))
    op.create_unique_constraint(
        "uq_purchases_tenant_invoice_access_key",
        "purchases",
        ["tenant_id", "invoice_access_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_purchases_tenant_invoice_access_key",
        "purchases",
        type_="unique",
    )
    op.drop_column("purchases", "invoice_number")
    op.drop_column("purchases", "invoice_access_key")
