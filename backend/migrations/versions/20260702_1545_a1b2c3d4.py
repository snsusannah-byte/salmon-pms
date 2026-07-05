"""add_related_invoice_no_to_transaction_records

Revision ID: 20260702_1545_a1b2c3d4
Revises: 9456dd37996c
Create Date: 2026-07-02 15:45:00.000000+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260702_1545_a1b2c3d4'
down_revision: Union[str, Sequence[str], None] = '9456dd37996c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('transaction_records', sa.Column('related_invoice_no', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('transaction_records', 'related_invoice_no')
