"""add_batch_no_to_stock_movements

Revision ID: 6828bc8fd9f7
Revises: e4faddcfd4a3
Create Date: 2026-07-03 10:39:35.751092+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6828bc8fd9f7'
down_revision: Union[str, Sequence[str], None] = 'e4faddcfd4a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 添加 batch_no 列到 stock_movements 表
    op.add_column('stock_movements', sa.Column('batch_no', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('stock_movements', 'batch_no')
