"""add balance_adjustment to whole_fish_sales

Revision ID: 20260718_1036_a1b2c3d4e5f6
Revises: 88c77b3f6440
Create Date: 2026-07-18 10:36:00+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260718_1036_a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '88c77b3f6440'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('whole_fish_sales', sa.Column('balance_adjustment', sa.Numeric(precision=10, scale=2), nullable=True, server_default=sa.text('0')))
    op.add_column('whole_fish_sales', sa.Column('balance_adjustment_reason', sa.Text(), nullable=True))
    # 已有记录的 NULL 填充为 0
    op.execute("UPDATE whole_fish_sales SET balance_adjustment = 0 WHERE balance_adjustment IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('whole_fish_sales', 'balance_adjustment_reason')
    op.drop_column('whole_fish_sales', 'balance_adjustment')
