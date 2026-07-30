"""add sale_unit base_quantity product_id to finished_sale_products_v2

Revision ID: 20260720_1425_a1b2c3d4e5fa
Revises: 20260720_1410_a1b2c3d4e5f9
Create Date: 2026-07-20 14:25:00+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260720_1425_a1b2c3d4e5fa'
down_revision: Union[str, Sequence[str], None] = '20260720_1410_a1b2c3d4e5f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 添加新列
    op.add_column(
        'finished_sale_products_v2',
        sa.Column('product_id', sa.Integer(), nullable=True)
    )
    op.add_column(
        'finished_sale_products_v2',
        sa.Column('sale_unit', sa.String(length=20), nullable=True)
    )
    op.add_column(
        'finished_sale_products_v2',
        sa.Column('base_quantity', sa.Numeric(precision=12, scale=2), nullable=True)
    )

    # 创建外键（可选，保持与 products.id 关联）
    op.create_foreign_key(
        'fk_finished_sale_products_v2_product_id',
        'finished_sale_products_v2',
        'products',
        ['product_id'],
        ['id'],
    )

    # 数据回填：
    # sale_unit 优先取关联产品的 unit，否则 '盘'
    # base_quantity 取 weight_kg（如果未知则 0）
    op.execute("""
        UPDATE finished_sale_products_v2 f
        SET sale_unit = COALESCE(
            (SELECT p.unit FROM products p WHERE p.id = f.product_id),
            '盘'
        ),
        base_quantity = COALESCE(f.weight_kg, 0)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_finished_sale_products_v2_product_id', 'finished_sale_products_v2', type_='foreignkey')
    op.drop_column('finished_sale_products_v2', 'base_quantity')
    op.drop_column('finished_sale_products_v2', 'sale_unit')
    op.drop_column('finished_sale_products_v2', 'product_id')
