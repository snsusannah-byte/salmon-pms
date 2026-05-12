"""add_is_locked_to_sales_receipts

Revision ID: 70709c44e9b1
Revises: 038481c48154
Create Date: 2026-05-11 18:41:35.012214+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '70709c44e9b1'
down_revision: Union[str, Sequence[str], None] = '038481c48154'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('sales_receipts', sa.Column('is_locked', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('sales_receipts', 'is_locked')
