"""add_unit_to_purchase_order_products_v2

Revision ID: d99a6c307040
Revises: ecbfde2f0583
Create Date: 2026-05-29 12:56:45.565245+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd99a6c307040'
down_revision: Union[str, Sequence[str], None] = 'ecbfde2f0583'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('purchase_order_products_v2', sa.Column('unit', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('purchase_order_products_v2', 'unit')
