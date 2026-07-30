"""add discount_reason to whole_fish_sales

Revision ID: 88c77b3f6440
Revises: 82134f63f34a
Create Date: 2026-07-17 19:08:00+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '88c77b3f6440'
down_revision: Union[str, Sequence[str], None] = '82134f63f34a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('whole_fish_sales', sa.Column('discount_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('whole_fish_sales', 'discount_reason')
