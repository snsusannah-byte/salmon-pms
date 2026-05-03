"""add product cost price stock fields

Revision ID: b500c5f12785
Revises: 8153451b33a0
Create Date: 2026-05-03 17:06:00.000000+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b500c5f12785'
down_revision: Union[str, Sequence[str], None] = '8153451b33a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cost_price', sa.Numeric(precision=15, scale=2), nullable=True))
        batch_op.add_column(sa.Column('suggested_retail_price', sa.Numeric(precision=15, scale=2), nullable=True))
        batch_op.add_column(sa.Column('wholesale_price', sa.Numeric(precision=15, scale=2), nullable=True))
        batch_op.add_column(sa.Column('min_price', sa.Numeric(precision=15, scale=2), nullable=True))
        batch_op.add_column(sa.Column('stock_quantity', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('safety_stock', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('safety_stock')
        batch_op.drop_column('stock_quantity')
        batch_op.drop_column('min_price')
        batch_op.drop_column('wholesale_price')
        batch_op.drop_column('suggested_retail_price')
        batch_op.drop_column('cost_price')
