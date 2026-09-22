"""create the original BudgetBasket database schema

Revision ID: 20260922_00
Revises:
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260922_00"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(), nullable=True, server_default="each"),
        sa.Column("nutrition_tags", sa.String(), nullable=True, server_default=""),
        sa.Column("embedding_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_products_category", "products", ["category"])

    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id"),
            nullable=True,
        ),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column(
            "quantity",
            sa.Float(),
            nullable=True,
            server_default="1.0",
        ),
        sa.Column(
            "purchased_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_purchases_user_id", "purchases", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_purchases_user_id", table_name="purchases")
    op.drop_table("purchases")
    op.drop_table("price_history")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_table("products")
