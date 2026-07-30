"""add balance_adjustment to finished_product_sales_v2

Revision ID: 20260719_1802_a1b2c3d4e5f7
Revises: 20260718_1036_a1b2c3d4e5f6
Create Date: 2026-07-19 18:02:00+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260719_1802_a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = '20260718_1036_a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'finished_product_sales_v2',
        sa.Column('balance_adjustment', sa.Numeric(precision=10, scale=2), nullable=True, server_default=sa.text('0')),
    )
    # 已有记录的 NULL 填充为 0
    op.execute("UPDATE finished_product_sales_v2 SET balance_adjustment = 0 WHERE balance_adjustment IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('finished_product_sales_v2', 'balance_adjustment')
