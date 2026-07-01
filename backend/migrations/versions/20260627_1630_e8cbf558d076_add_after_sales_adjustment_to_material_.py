"""add_after_sales_adjustment_to_material_purchase

Revision ID: e8cbf558d076
Revises: 309e19aa0d05
Create Date: 2026-06-27 16:30:00.929778+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e8cbf558d076'
down_revision: Union[str, Sequence[str], None] = '309e19aa0d05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('material_purchase_orders', sa.Column('after_sales_adjustment', sa.Numeric(precision=15, scale=2), server_default=sa.text('0'), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('material_purchase_orders', 'after_sales_adjustment')
