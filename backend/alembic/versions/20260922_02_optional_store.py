"""allow price observations without a known retailer

The Phase 1A Australian grocery snapshot does not expose a retailer field.
Retailer-specific sources such as AusCost will populate store_id later.
"""

from alembic import op


revision = "20260922_02"
down_revision = "20260922_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("price_observations", "store_id", nullable=True)


def downgrade() -> None:
    op.alter_column("price_observations", "store_id", nullable=False)
