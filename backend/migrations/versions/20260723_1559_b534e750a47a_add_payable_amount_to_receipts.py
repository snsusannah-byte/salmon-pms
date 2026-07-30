"""add payable_amount to receipts for prepayment display

Revision ID: b534e750a47a
Revises: a1b2c3d4e5fa
Create Date: 2026-07-23 15:59:00+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b534e750a47a'
down_revision: Union[str, Sequence[str], None] = '20260720_1425_a1b2c3d4e5fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 收款记录中增加“创建时单据应付金额”，用于交易流水中客户预付款展示“应付/实收”
    op.add_column('sales_receipts', sa.Column('payable_amount', sa.Numeric(15, 2), nullable=True))
    op.add_column('finished_product_receipts', sa.Column('payable_amount', sa.Numeric(15, 2), nullable=True))

    # 存量数据：应付金额未知，回退到与实收金额一致（前端会另行按公式兜底）
    op.execute("UPDATE sales_receipts SET payable_amount = amount WHERE payable_amount IS NULL")
    op.execute("UPDATE finished_product_receipts SET payable_amount = amount WHERE payable_amount IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('finished_product_receipts', 'payable_amount')
    op.drop_column('sales_receipts', 'payable_amount')
