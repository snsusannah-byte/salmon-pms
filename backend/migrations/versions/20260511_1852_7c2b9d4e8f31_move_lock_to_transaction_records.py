"""move_lock_to_transaction_records

Revision ID: 7c2b9d4e8f31
Revises: 70709c44e9b1
Create Date: 2026-05-11 18:52:00.000000+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7c2b9d4e8f31'
down_revision: Union[str, Sequence[str], None] = '70709c44e9b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 删除 sales_receipts 的 is_locked（刚加的）
    op.drop_column('sales_receipts', 'is_locked')
    # 2. 给 transaction_records 加 is_locked
    op.add_column('transaction_records', sa.Column('is_locked', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    op.drop_column('transaction_records', 'is_locked')
    op.add_column('sales_receipts', sa.Column('is_locked', sa.Boolean(), server_default=sa.text('false'), nullable=False))
