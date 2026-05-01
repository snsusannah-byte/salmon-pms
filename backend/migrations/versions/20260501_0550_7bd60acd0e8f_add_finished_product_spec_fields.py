"""add_finished_product_spec_fields

Revision ID: 7bd60acd0e8f
Revises: 051f4f53dec5
Create Date: 2026-05-01 05:50:30.828191+08:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7bd60acd0e8f'
down_revision: Union[str, Sequence[str], None] = '051f4f53dec5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 使用 batch_alter_table 兼容 SQLite
    with op.batch_alter_table('batches', schema=None) as batch_op:
        batch_op.alter_column('batch_code',
               existing_type=sa.VARCHAR(length=20),
               nullable=False)

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('series_code', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('series_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('portion_weight_g', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('portion_boxes', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('portion_boxes')
        batch_op.drop_column('portion_weight_g')
        batch_op.drop_column('series_name')
        batch_op.drop_column('series_code')

    with op.batch_alter_table('batches', schema=None) as batch_op:
        batch_op.alter_column('batch_code',
               existing_type=sa.VARCHAR(length=20),
               nullable=True)
