"""add_box_count_to_stock_and_outbound

Revision ID: 33e1642e9cac
Revises: 20260702_1545_a1b2c3d4
Create Date: 2026-07-02 21:43:05.333183+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33e1642e9cac'
down_revision: Union[str, Sequence[str], None] = '20260702_1545_a1b2c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # stocks 表增加箱数字段
    op.add_column('stocks', sa.Column('current_box_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('stocks', sa.Column('available_box_count', sa.Integer(), nullable=False, server_default='0'))
    
    # stock_outbounds 表增加箱数字段
    op.add_column('stock_outbounds', sa.Column('box_count', sa.Integer(), nullable=False, server_default='0'))
    
    # stock_movements 表增加箱数字段（记录变动）
    op.add_column('stock_movements', sa.Column('box_count_change', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('stock_movements', sa.Column('box_count_before', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('stock_movements', sa.Column('box_count_after', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('stock_movements', 'box_count_after')
    op.drop_column('stock_movements', 'box_count_before')
    op.drop_column('stock_movements', 'box_count_change')
    op.drop_column('stock_outbounds', 'box_count')
    op.drop_column('stocks', 'available_box_count')
    op.drop_column('stocks', 'current_box_count')
