"""add_related_exchange_id_to_transaction_records

Revision ID: 9456dd37996c
Revises: 62636a3a9cb3
Create Date: 2026-07-02 12:59:55.317750+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9456dd37996c'
down_revision: Union[str, Sequence[str], None] = '62636a3a9cb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('transaction_records', sa.Column('related_exchange_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_transaction_records_exchange', 'transaction_records', 'exchange_records', ['related_exchange_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_transaction_records_exchange', 'transaction_records', type_='foreignkey')
    op.drop_column('transaction_records', 'related_exchange_id')
