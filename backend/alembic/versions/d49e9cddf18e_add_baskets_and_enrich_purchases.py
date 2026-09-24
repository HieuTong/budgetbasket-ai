"""add baskets and enrich purchases

Revision ID: d49e9cddf18e
Revises: 20260923_03
Create Date: 2026-09-24 15:54:41.990059

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd49e9cddf18e'
down_revision: Union[str, Sequence[str], None] = '20260923_03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
