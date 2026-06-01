"""Add product_series, product_specs, variant_price_tiers; refactor product_templates and product_variants

Revision ID: 20260525_2352_f1a2b3c4d5e6
Revises: 4e36257a8e47
Create Date: 2026-05-25 23:52:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260525_2352_f1a2b3c4d5e6'
down_revision: Union[str, None] = '4e36257a8e47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 创建 product_series 表
    op.create_table(
        'product_series',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    
    # 2. 创建 product_specs 表
    op.create_table(
        'product_specs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('parts_config', sa.Text(), nullable=True),
        sa.Column('total_weight_g', sa.Integer(), nullable=True),
        sa.Column('portion_count', sa.Integer(), default=1),
        sa.Column('box_count', sa.Integer(), default=1),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['product_templates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 3. 创建 variant_price_tiers 表
    op.create_table(
        'variant_price_tiers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('variant_id', sa.Integer(), nullable=False),
        sa.Column('tier_type', sa.String(length=20), nullable=False),
        sa.Column('tier_key', sa.String(length=50), nullable=False),
        sa.Column('tier_name', sa.String(length=100), nullable=False),
        sa.Column('min_qty', sa.Integer(), default=1),
        sa.Column('max_qty', sa.Integer(), nullable=True),
        sa.Column('price', sa.Numeric(15, 2), nullable=False),
        sa.Column('valid_from', sa.String(length=10), nullable=True),
        sa.Column('valid_to', sa.String(length=10), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['variant_id'], ['product_variants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 4. 给 product_templates 加 series_id
    op.add_column('product_templates', sa.Column('series_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_templates_series', 'product_templates', 'product_series', ['series_id'], ['id'])
    
    # 5. 给 product_variants 加 spec_id
    op.add_column('product_variants', sa.Column('spec_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_variants_spec', 'product_variants', 'product_specs', ['spec_id'], ['id'])
    
    # 6. 给 template_boms 加 material_type 和 is_main
    op.add_column('template_boms', sa.Column('material_type', sa.String(length=20), server_default='salmon'))
    op.add_column('template_boms', sa.Column('is_main', sa.Boolean(), server_default='false'))
    
    # 7. 给 variant_accessories 加 accessory_type
    op.add_column('variant_accessories', sa.Column('accessory_type', sa.String(length=20), server_default='accessory'))
    
    # 8. 创建索引
    op.create_index('ix_product_specs_template_id', 'product_specs', ['template_id'])
    op.create_index('ix_product_variants_spec_id', 'product_variants', ['spec_id'])
    op.create_index('ix_variant_price_tiers_variant_id', 'variant_price_tiers', ['variant_id'])


def downgrade() -> None:
    # 逆序删除
    op.drop_index('ix_variant_price_tiers_variant_id', table_name='variant_price_tiers')
    op.drop_index('ix_product_variants_spec_id', table_name='product_variants')
    op.drop_index('ix_product_specs_template_id', table_name='product_specs')
    
    op.drop_column('variant_accessories', 'accessory_type')
    op.drop_column('template_boms', 'is_main')
    op.drop_column('template_boms', 'material_type')
    op.drop_constraint('fk_variants_spec', 'product_variants', type_='foreignkey')
    op.drop_column('product_variants', 'spec_id')
    op.drop_constraint('fk_templates_series', 'product_templates', type_='foreignkey')
    op.drop_column('product_templates', 'series_id')
    
    op.drop_table('variant_price_tiers')
    op.drop_table('product_specs')
    op.drop_table('product_series')
