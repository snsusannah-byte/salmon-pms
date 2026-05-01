"""add_customer_fields

Revision ID: 7f74e65b9d5d
Revises: 7bd60acd0e8f
Create Date: 2026-05-01 07:20:05.754631+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f74e65b9d5d'
down_revision: Union[str, Sequence[str], None] = '7bd60acd0e8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite 需要使用 batch_alter_table
    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.add_column(sa.Column('logistics_info', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('salesperson_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('customer_category', sa.Enum('WHOLESALER', 'DISTRIBUTOR', 'RETAILER', 'PLATFORM', 'GROUP_BUYING', name='customercategory'), nullable=True))
        batch_op.create_foreign_key('fk_companies_salesperson', 'users', ['salesperson_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.drop_constraint('fk_companies_salesperson', type_='foreignkey')
        batch_op.drop_column('customer_category')
        batch_op.drop_column('salesperson_id')
        batch_op.drop_column('logistics_info')
