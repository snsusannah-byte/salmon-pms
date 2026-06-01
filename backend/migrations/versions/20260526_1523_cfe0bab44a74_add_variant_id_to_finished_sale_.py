"""add_variant_id_to_finished_sale_products_v2

Revision ID: cfe0bab44a74
Revises: c143e346bbd5
Create Date: 2026-05-26 15:23:50.884661+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'cfe0bab44a74'
down_revision: Union[str, Sequence[str], None] = 'c143e346bbd5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('finished_sale_products_v2', sa.Column('variant_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'finished_sale_products_v2', 'product_variants', ['variant_id'], ['id'])


def downgrade() -> None:
    op.drop_column('finished_sale_products_v2', 'variant_id')
