"""add after_sales_adjustment and balance_adjustment to finished_product_sales

Revision ID: 20260720_1110_a1b2c3d4e5f8
Revises: 20260719_1802_a1b2c3d4e5f7
Create Date: 2026-07-20 11:10:00+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260720_1110_a1b2c3d4e5f8'
down_revision: Union[str, Sequence[str], None] = '20260719_1802_a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'finished_product_sales',
        sa.Column('after_sales_adjustment', sa.Numeric(precision=10, scale=2), nullable=True, server_default=sa.text('0')),
    )
    op.add_column(
        'finished_product_sales',
        sa.Column('balance_adjustment', sa.Numeric(precision=10, scale=2), nullable=True, server_default=sa.text('0')),
    )
    op.add_column(
        'finished_product_sales',
        sa.Column('balance_adjustment_reason', sa.Text(), nullable=True),
    )
    # 已有记录的 NULL 填充为 0
    op.execute("UPDATE finished_product_sales SET after_sales_adjustment = 0 WHERE after_sales_adjustment IS NULL")
    op.execute("UPDATE finished_product_sales SET balance_adjustment = 0 WHERE balance_adjustment IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('finished_product_sales', 'balance_adjustment_reason')
    op.drop_column('finished_product_sales', 'balance_adjustment')
    op.drop_column('finished_product_sales', 'after_sales_adjustment')
