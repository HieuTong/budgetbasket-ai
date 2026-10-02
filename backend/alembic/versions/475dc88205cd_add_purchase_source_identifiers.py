"""add purchase source identifiers

Revision ID: 475dc88205cd
Revises: d49e9cddf18e
Create Date: 2026-09-25 10:56:33.940634

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '475dc88205cd'
down_revision: Union[str, Sequence[str], None] = 'd49e9cddf18e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "purchases",
        sa.Column(
            "source",
            sa.String(),
            nullable=True,
        ),
    )

    op.add_column(
        "purchases",
        sa.Column(
            "source_transaction_id",
            sa.String(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_purchases_source",
        "purchases",
        ["source"],
    )

    op.create_index(
        "ix_purchases_source_transaction_id",
        "purchases",
        ["source_transaction_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_purchases_source_transaction_id",
        table_name="purchases",
    )

    op.drop_index(
        "ix_purchases_source",
        table_name="purchases",
    )

    op.drop_column(
        "purchases",
        "source_transaction_id",
    )

    op.drop_column(
        "purchases",
        "source",
    )
