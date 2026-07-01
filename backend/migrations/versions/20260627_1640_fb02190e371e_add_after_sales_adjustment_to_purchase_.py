"""add_after_sales_adjustment_to_purchase_order_v2

Revision ID: fb02190e371e
Revises: e8cbf558d076
Create Date: 2026-06-27 16:40:17.274341+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fb02190e371e'
down_revision: Union[str, Sequence[str], None] = 'e8cbf558d076'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('purchase_orders_v2', sa.Column('after_sales_adjustment', sa.Numeric(precision=15, scale=2), server_default=sa.text('0'), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('purchase_orders_v2', 'after_sales_adjustment')
