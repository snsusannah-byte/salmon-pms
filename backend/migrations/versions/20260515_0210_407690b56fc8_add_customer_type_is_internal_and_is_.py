"""add customer_type is_internal and is_internal_sale

Revision ID: 407690b56fc8
Revises: 5e6b35b12da2
Create Date: 2026-05-15 02:10:43.384946+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '407690b56fc8'
down_revision: Union[str, Sequence[str], None] = '5e6b35b12da2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add customer_type, is_internal to companies; add is_internal_sale to whole_fish_sales."""
    # companies.customer_type: 客户类型细分
    op.add_column('companies', sa.Column('customer_type', sa.String(length=20), nullable=True))
    
    # companies.is_internal: 是否内部客户（加工厂/代工方）
    op.add_column(
        'companies',
        sa.Column('is_internal', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )
    
    # whole_fish_sales.is_internal_sale: 是否内部销售（加工厂流转）
    op.add_column(
        'whole_fish_sales',
        sa.Column('is_internal_sale', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )


def downgrade() -> None:
    """Drop the added columns."""
    op.drop_column('whole_fish_sales', 'is_internal_sale')
    op.drop_column('companies', 'is_internal')
    op.drop_column('companies', 'customer_type')
