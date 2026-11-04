from alembic import op
import sqlalchemy as sa

revision = "0005_product_fiscal_ids"
down_revision = "0004_customer_product_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("barcode", sa.String(length=32), nullable=True))
    op.add_column("products", sa.Column("ncm", sa.String(length=8), nullable=True))
    op.add_column("products", sa.Column("cst", sa.String(length=3), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "cst")
    op.drop_column("products", "ncm")
    op.drop_column("products", "barcode")
