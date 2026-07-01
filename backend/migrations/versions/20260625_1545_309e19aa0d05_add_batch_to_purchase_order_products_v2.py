"""add batch to purchase_order_products_v2

Revision ID: 309e19aa0d05
Revises: 57b33c1ae0bb
Create Date: 2026-06-25 15:45:08.624994+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '309e19aa0d05'
down_revision: Union[str, Sequence[str], None] = '57b33c1ae0bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('purchase_order_products_v2', sa.Column('batch', sa.String(50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('purchase_order_products_v2', 'batch')
