"""add location fields to price observations

Revision ID: 20260923_03
Revises: 20260922_02
Create Date: 2026-09-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260923_03"
down_revision = "20260922_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "price_observations",
        sa.Column("postal_code", sa.String(), nullable=True),
    )
    op.add_column(
        "price_observations",
        sa.Column("state", sa.String(), nullable=True),
    )
    op.add_column(
        "price_observations",
        sa.Column("city", sa.String(), nullable=True),
    )

    op.create_index(
        "ix_price_observations_postal_code",
        "price_observations",
        ["postal_code"],
    )
    op.create_index(
        "ix_price_observations_state",
        "price_observations",
        ["state"],
    )
    op.create_index(
        "ix_price_observations_city",
        "price_observations",
        ["city"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_price_observations_city",
        table_name="price_observations",
    )
    op.drop_index(
        "ix_price_observations_state",
        table_name="price_observations",
    )
    op.drop_index(
        "ix_price_observations_postal_code",
        table_name="price_observations",
    )
    op.drop_column("price_observations", "city")
    op.drop_column("price_observations", "state")
    op.drop_column("price_observations", "postal_code")
