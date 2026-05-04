"""add_batch_id_to_exchange_records

Revision ID: 61a295fcd54e
Revises: v3_complete
Create Date: 2026-05-04 19:36:39.247710+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61a295fcd54e'
down_revision: Union[str, None] = 'v3_complete'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add batch_id to exchange_records
    op.add_column('exchange_records', sa.Column('batch_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'exchange_records_batch_id_fkey',
        'exchange_records', 'batches',
        ['batch_id'], ['id']
    )

    # Make bank_account_id nullable (for batch-based exchanges)
    op.alter_column('exchange_records', 'bank_account_id',
        existing_type=sa.Integer(),
        nullable=True
    )


def downgrade() -> None:
    op.drop_constraint('exchange_records_batch_id_fkey', 'exchange_records', type_='foreignkey')
    op.drop_column('exchange_records', 'batch_id')
    op.alter_column('exchange_records', 'bank_account_id',
        existing_type=sa.Integer(),
        nullable=False
    )
