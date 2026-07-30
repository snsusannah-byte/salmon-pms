"""add freight to finished_product_sales_v2

Revision ID: 3c7d9e1a4f82
Revises: 0f3a8c2b5d71
Create Date: 2026-07-24 18:21:00.000000+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c7d9e1a4f82'
down_revision: Union[str, Sequence[str], None] = '0f3a8c2b5d71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('finished_product_sales_v2', sa.Column('freight', sa.Numeric(precision=10, scale=2), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('finished_product_sales_v2', 'freight')
