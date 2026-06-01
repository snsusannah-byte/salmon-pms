"""add_customer_level_to_companies

Revision ID: c143e346bbd5
Revises: 20260525_2352_f1a2b3c4d5e6
Create Date: 2026-05-26 15:05:38.298140+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c143e346bbd5'
down_revision: Union[str, Sequence[str], None] = '20260525_2352_f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('customer_level', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'customer_level')
