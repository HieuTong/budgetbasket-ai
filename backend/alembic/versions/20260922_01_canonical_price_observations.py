"""establish canonical product and price observation schema

Revision ID: 20260922_01
Revises:
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260922_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.execute(
        "INSERT INTO users (id, created_at) "
        "SELECT DISTINCT user_id, CURRENT_TIMESTAMP FROM purchases "
        "WHERE user_id IS NOT NULL"
    )

    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("name"),
    )

    for name, column in [
        ("brand", sa.String()),
        ("sub_category", sa.String()),
        ("product_group", sa.String()),
        ("barcode", sa.String()),
        ("package_size", sa.String()),
        ("source", sa.String()),
        ("source_product_id", sa.String()),
        ("created_at", sa.DateTime()),
        ("updated_at", sa.DateTime()),
    ]:
        op.add_column("products", sa.Column(column.name, column, nullable=True))

    op.execute(
        "UPDATE products SET created_at = CURRENT_TIMESTAMP, "
        "updated_at = CURRENT_TIMESTAMP "
        "WHERE created_at IS NULL OR updated_at IS NULL"
    )
    op.alter_column("products", "created_at", nullable=False)
    op.alter_column("products", "updated_at", nullable=False)

    op.create_index("ix_products_barcode", "products", ["barcode"])
    op.create_index("ix_products_source", "products", ["source"])
    op.create_index("ix_products_source_product_id", "products", ["source_product_id"])
    op.create_index("ix_products_sub_category", "products", ["sub_category"])

    op.create_table(
        "price_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 4), nullable=True),
        sa.Column("unit_price_unit", sa.String(), nullable=True),
        sa.Column("retail_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("is_special", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("in_stock", sa.Boolean(), nullable=True),
        sa.Column("is_estimated", sa.Boolean(), nullable=True),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_record_id", sa.String(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for name, column in [
        ("ix_price_observations_product_id", "product_id"),
        ("ix_price_observations_store_id", "store_id"),
        ("ix_price_observations_observed_at", "observed_at"),
        ("ix_price_observations_source", "source"),
        ("ix_price_observations_source_record_id", "source_record_id"),
    ]:
        op.create_index(name, "price_observations", [column])

    op.create_foreign_key(
        "fk_purchases_user_id_users",
        "purchases",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_purchases_user_id_users", "purchases", type_="foreignkey")
    op.drop_index("ix_price_observations_source_record_id", table_name="price_observations")
    op.drop_index("ix_price_observations_source", table_name="price_observations")
    op.drop_index("ix_price_observations_observed_at", table_name="price_observations")
    op.drop_index("ix_price_observations_store_id", table_name="price_observations")
    op.drop_index("ix_price_observations_product_id", table_name="price_observations")
    op.drop_table("price_observations")

    for name in ["ix_products_sub_category", "ix_products_source_product_id", "ix_products_source", "ix_products_barcode"]:
        op.drop_index(name, table_name="products")
    for column in ["updated_at", "created_at", "source_product_id", "source", "package_size", "barcode", "product_group", "sub_category", "brand"]:
        op.drop_column("products", column)

    op.drop_table("stores")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
