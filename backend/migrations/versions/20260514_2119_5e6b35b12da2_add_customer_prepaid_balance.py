"""add customer prepaid_balance

Revision ID: 5e6b35b12da2
Revises: bde0d893b2e9
Create Date: 2026-05-14 21:19:58.175488+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5e6b35b12da2'
down_revision: Union[str, Sequence[str], None] = 'bde0d893b2e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add prepaid_balance column to companies table."""
    op.add_column(
        'companies',
        sa.Column('prepaid_balance', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0')
    )


def downgrade() -> None:
    """Drop prepaid_balance column."""
    op.drop_column('companies', 'prepaid_balance')
