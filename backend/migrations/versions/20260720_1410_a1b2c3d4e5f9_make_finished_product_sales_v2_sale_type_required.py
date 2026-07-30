"""make finished_product_sales_v2.sale_type required

Revision ID: 20260720_1410_a1b2c3d4e5f9
Revises: 20260720_1110_a1b2c3d4e5f8
Create Date: 2026-07-20 14:10:00+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260720_1410_a1b2c3d4e5f9'
down_revision: Union[str, Sequence[str], None] = '20260720_1110_a1b2c3d4e5f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 已有记录的 NULL 填充为 whole_fish
    op.execute("UPDATE finished_product_sales_v2 SET sale_type = 'whole_fish' WHERE sale_type IS NULL")
    # 改为非空并去掉默认值
    op.alter_column(
        'finished_product_sales_v2',
        'sale_type',
        existing_type=sa.String(length=20),
        nullable=False,
        server_default=None,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'finished_product_sales_v2',
        'sale_type',
        existing_type=sa.String(length=20),
        nullable=True,
        server_default=sa.text("'whole_fish'"),
    )
