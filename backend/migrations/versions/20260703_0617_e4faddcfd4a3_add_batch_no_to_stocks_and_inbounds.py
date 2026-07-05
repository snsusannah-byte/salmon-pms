"""add_batch_no_to_stocks_and_inbounds

Revision ID: e4faddcfd4a3
Revises: 33e1642e9cac
Create Date: 2026-07-03 06:17:40.748446+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e4faddcfd4a3'
down_revision: Union[str, Sequence[str], None] = '33e1642e9cac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 添加 batch_no 列到 stock_inbounds 表
    op.add_column('stock_inbounds', sa.Column('batch_no', sa.String(length=50), nullable=True))
    # 添加 batch_no 列到 stocks 表
    op.add_column('stocks', sa.Column('batch_no', sa.String(length=50), nullable=True))
    # 修改唯一约束，增加 batch_no
    op.drop_constraint('uq_stock_warehouse_product_batch', 'stocks', type_='unique')
    op.create_unique_constraint('uq_stock_warehouse_product_batch', 'stocks', ['warehouse_id', 'product_id', 'batch_id', 'batch_no'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_stock_warehouse_product_batch', 'stocks', type_='unique')
    op.create_unique_constraint('uq_stock_warehouse_product_batch', 'stocks', ['warehouse_id', 'product_id', 'batch_id'])
    op.drop_column('stocks', 'batch_no')
    op.drop_column('stock_inbounds', 'batch_no')
