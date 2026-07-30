"""add source_id source_no to finished_product_sales_v2

Revision ID: 4abfdf71a594
Revises: b534e750a47a
Create Date: 2026-07-24 11:55:52.384067+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4abfdf71a594'
down_revision: Union[str, Sequence[str], None] = 'b534e750a47a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('finished_product_sales_v2', sa.Column('source_id', sa.Integer(), nullable=True))
    op.add_column('finished_product_sales_v2', sa.Column('source_no', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('finished_product_sales_v2', 'source_no')
    op.drop_column('finished_product_sales_v2', 'source_id')
