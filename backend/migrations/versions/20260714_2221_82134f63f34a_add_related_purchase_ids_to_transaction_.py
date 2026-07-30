"""add related_purchase_ids to transaction_records

Revision ID: 82134f63f34a
Revises: 6828bc8fd9f7
Create Date: 2026-07-14 22:21:03.624861+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '82134f63f34a'
down_revision: Union[str, Sequence[str], None] = '6828bc8fd9f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Only add the related_purchase_ids column to transaction_records
    op.add_column('transaction_records', sa.Column('related_purchase_ids', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('transaction_records', 'related_purchase_ids')
