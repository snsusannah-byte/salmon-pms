"""add batch to finished_sale_products_v2

Revision ID: 0f3a8c2b5d71
Revises: 20b535e17f95
Create Date: 2026-07-24 15:57:00.000000+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f3a8c2b5d71'
down_revision: Union[str, Sequence[str], None] = '20b535e17f95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('finished_sale_products_v2', sa.Column('batch', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('finished_sale_products_v2', 'batch')
