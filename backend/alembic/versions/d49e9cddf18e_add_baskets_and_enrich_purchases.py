"""add baskets and enrich purchases

Revision ID: d49e9cddf18e
Revises: 20260923_03
Create Date: 2026-09-24 15:54:41.990059
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d49e9cddf18e"
down_revision: Union[str, Sequence[str], None] = "20260923_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # baskets
    # ------------------------------------------------------------------
    op.create_table(
        "baskets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "source_basket_id",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "store_id",
            sa.Integer(),
            sa.ForeignKey("stores.id"),
            nullable=True,
        ),
        sa.Column(
            "purchased_at",
            sa.DateTime(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_baskets_user_id",
        "baskets",
        ["user_id"],
    )

    op.create_index(
        "ix_baskets_source_basket_id",
        "baskets",
        ["source_basket_id"],
    )

    op.create_index(
        "ix_baskets_store_id",
        "baskets",
        ["store_id"],
    )

    op.create_index(
        "ix_baskets_purchased_at",
        "baskets",
        ["purchased_at"],
    )

    # ------------------------------------------------------------------
    # enrich purchases
    # ------------------------------------------------------------------
    op.add_column(
        "purchases",
        sa.Column(
            "basket_id",
            sa.Integer(),
            sa.ForeignKey("baskets.id"),
            nullable=True,
        ),
    )

    op.add_column(
        "purchases",
        sa.Column(
            "sales_value",
            sa.Numeric(12, 4),
            nullable=True,
        ),
    )

    op.add_column(
        "purchases",
        sa.Column(
            "retail_discount",
            sa.Numeric(12, 4),
            nullable=True,
        ),
    )

    op.add_column(
        "purchases",
        sa.Column(
            "coupon_discount",
            sa.Numeric(12, 4),
            nullable=True,
        ),
    )

    op.add_column(
        "purchases",
        sa.Column(
            "coupon_match_discount",
            sa.Numeric(12, 4),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_purchases_basket_id",
        "purchases",
        ["basket_id"],
    )

    op.create_index(
        "ix_purchases_purchased_at",
        "purchases",
        ["purchased_at"],
    )


def downgrade() -> None:
    # Remove purchase indexes first.
    op.drop_index(
        "ix_purchases_purchased_at",
        table_name="purchases",
    )

    op.drop_index(
        "ix_purchases_basket_id",
        table_name="purchases",
    )

    # Remove purchase columns.
    op.drop_column(
        "purchases",
        "coupon_match_discount",
    )

    op.drop_column(
        "purchases",
        "coupon_discount",
    )

    op.drop_column(
        "purchases",
        "retail_discount",
    )

    op.drop_column(
        "purchases",
        "sales_value",
    )

    op.drop_column(
        "purchases",
        "basket_id",
    )

    # Remove basket indexes.
    op.drop_index(
        "ix_baskets_purchased_at",
        table_name="baskets",
    )

    op.drop_index(
        "ix_baskets_store_id",
        table_name="baskets",
    )

    op.drop_index(
        "ix_baskets_source_basket_id",
        table_name="baskets",
    )

    op.drop_index(
        "ix_baskets_user_id",
        table_name="baskets",
    )

    # Finally remove baskets.
    op.drop_table("baskets")