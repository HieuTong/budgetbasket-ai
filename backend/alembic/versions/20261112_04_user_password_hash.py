"""add a password hash to users

Revision ID: 20261112_04
Revises: 475dc88205cd
Create Date: 2026-11-12

Nullable on purpose: users created by the seed and import scripts have no
password. A NULL hash means "this account cannot log in with a password".
"""

from alembic import op
import sqlalchemy as sa


revision = "20261112_04"
down_revision = "475dc88205cd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "password_hash")
