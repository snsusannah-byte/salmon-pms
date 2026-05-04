"""add finished product v3 with slaughter records

Revision ID: v3_complete
Revises: ecd5c69be146
Create Date: 2026-05-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'v3_complete'
down_revision: Union[str, Sequence[str], None] = 'ecd5c69be146'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Product表新增库存/价格字段
    op.add_column('products', sa.Column('cost_price', sa.Numeric(15, 2), nullable=True))
    op.add_column('products', sa.Column('suggested_retail_price', sa.Numeric(15, 2), nullable=True))
    op.add_column('products', sa.Column('wholesale_price', sa.Numeric(15, 2), nullable=True))
    op.add_column('products', sa.Column('min_price', sa.Numeric(15, 2), nullable=True))
    op.add_column('products', sa.Column('stock_weight_kg', sa.Numeric(12, 3), server_default='0', nullable=True))
    # safety_stock 和 stock_quantity 可能已存在，用条件添加
    from alembic import context
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('products')]
    if 'stock_quantity' not in columns:
        op.add_column('products', sa.Column('stock_quantity', sa.Integer(), server_default='0', nullable=True))
    if 'safety_stock' not in columns:
        op.add_column('products', sa.Column('safety_stock', sa.Integer(), server_default='0', nullable=True))

    # 2. 成品销售主表添加总重量
    op.add_column('finished_product_sales', sa.Column('total_weight_kg', sa.Numeric(12, 3), server_default='0', nullable=True))

    # 3. 成品销售明细子项表（如果不存在则创建，如果存在则添加weight_kg）
    conn = op.get_bind()
    tables = inspector.get_table_names()
    if 'finished_product_sale_items' not in tables:
        op.create_table(
            'finished_product_sale_items',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('sale_id', sa.Integer(), sa.ForeignKey('finished_product_sales.id'), nullable=False),
            sa.Column('item_type', sa.String(20), nullable=False),
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
            sa.Column('product_name', sa.String(100), nullable=False),
            sa.Column('quantity', sa.Integer(), nullable=False),
            sa.Column('weight_kg', sa.Numeric(12, 3), nullable=True),
            sa.Column('unit_price', sa.Numeric(12, 4), nullable=True),
            sa.Column('amount', sa.Numeric(15, 2), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
    else:
        # 添加weight_kg字段
        columns = [c['name'] for c in inspector.get_columns('finished_product_sale_items')]
        if 'weight_kg' not in columns:
            op.add_column('finished_product_sale_items', sa.Column('weight_kg', sa.Numeric(12, 3), nullable=True))

    # 4. 收款/售后/提成表（如果不存在则创建）
    if 'finished_product_receipts' not in tables:
        op.create_table(
            'finished_product_receipts',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('sale_id', sa.Integer(), sa.ForeignKey('finished_product_sales.id'), nullable=False),
            sa.Column('receipt_date', sa.Date(), nullable=False),
            sa.Column('amount', sa.Numeric(15, 2), nullable=False),
            sa.Column('payment_method', sa.String(50), nullable=True),
            sa.Column('bank_account_id', sa.Integer(), sa.ForeignKey('bank_accounts.id'), nullable=True),
            sa.Column('reference_no', sa.String(100), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )

    if 'finished_product_aftersales' not in tables:
        op.create_table(
            'finished_product_aftersales',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('sale_id', sa.Integer(), sa.ForeignKey('finished_product_sales.id'), nullable=False),
            sa.Column('record_date', sa.Date(), nullable=False),
            sa.Column('type', sa.String(50), nullable=True),
            sa.Column('amount', sa.Numeric(15, 2), nullable=False),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('status', sa.String(20), server_default='pending', nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )

    if 'finished_product_commissions' not in tables:
        op.create_table(
            'finished_product_commissions',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('sale_id', sa.Integer(), sa.ForeignKey('finished_product_sales.id'), nullable=False),
            sa.Column('salesperson_id', sa.Integer(), sa.ForeignKey('salespersons.id'), nullable=False),
            sa.Column('sale_date', sa.Date(), nullable=False),
            sa.Column('sale_amount', sa.Numeric(15, 2), nullable=False),
            sa.Column('commission_rate', sa.Numeric(5, 2), nullable=False),
            sa.Column('commission_amount', sa.Numeric(15, 2), nullable=False),
            sa.Column('status', sa.String(20), server_default='pending', nullable=True),
            sa.Column('paid_date', sa.Date(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )

    # 5. 每日宰杀记录表
    if 'daily_slaughter_records' not in tables:
        op.create_table(
            'daily_slaughter_records',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('record_date', sa.Date(), nullable=False, unique=True),
            sa.Column('whole_fish_count', sa.Integer(), nullable=False),
            sa.Column('whole_fish_total_weight_kg', sa.Numeric(12, 3), nullable=False),
            sa.Column('finished_meat_weight_kg', sa.Numeric(12, 3), nullable=False),
            sa.Column('yield_rate', sa.Numeric(5, 2), nullable=False),
            sa.Column('head_count', sa.Integer(), server_default='0', nullable=True),
            sa.Column('tail_count', sa.Integer(), server_default='0', nullable=True),
            sa.Column('bone_count', sa.Integer(), server_default='0', nullable=True),
            sa.Column('scrap_weight_kg', sa.Numeric(12, 3), server_default='0', nullable=True),
            sa.Column('sold_weight_kg', sa.Numeric(12, 3), server_default='0', nullable=True),
            sa.Column('remaining_weight_kg', sa.Numeric(12, 3), server_default='0', nullable=True),
            sa.Column('operator', sa.String(50), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )


def downgrade() -> None:
    # 删除新表
    if 'daily_slaughter_records' in [t for t in op.get_bind().inspect().get_table_names()]:
        op.drop_table('daily_slaughter_records')
    if 'finished_product_commissions' in [t for t in op.get_bind().inspect().get_table_names()]:
        op.drop_table('finished_product_commissions')
    if 'finished_product_aftersales' in [t for t in op.get_bind().inspect().get_table_names()]:
        op.drop_table('finished_product_aftersales')
    if 'finished_product_receipts' in [t for t in op.get_bind().inspect().get_table_names()]:
        op.drop_table('finished_product_receipts')
    if 'finished_product_sale_items' in [t for t in op.get_bind().inspect().get_table_names()]:
        op.drop_table('finished_product_sale_items')
    # 删除列
    op.drop_column('finished_product_sales', 'total_weight_kg')
    op.drop_column('products', 'stock_weight_kg')
    op.drop_column('products', 'cost_price')
    op.drop_column('products', 'suggested_retail_price')
    op.drop_column('products', 'wholesale_price')
    op.drop_column('products', 'min_price')
    # stock_quantity 和 safety_stock 可能之前存在，谨慎处理
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('products')]
    for col in ['stock_quantity', 'safety_stock']:
        if col in columns:
            try:
                op.drop_column('products', col)
            except:
                pass
