"""
创建物料采购与批次管理表

Revision ID: a1b2c3d4e5f6
Revises: 368caa333c50
Create Date: 2026-05-28 14:49:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '368caa333c50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 物料采购单表
    op.create_table(
        'material_purchase_orders',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('order_no', sa.String(50), nullable=False, unique=True),
        sa.Column('order_date', sa.Date(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('quoted_total', sa.Numeric(15, 2), nullable=True),
        sa.Column('actual_total', sa.Numeric(15, 2), nullable=False),
        sa.Column('paid_amount', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('payment_status', sa.String(20), nullable=False, server_default='unpaid'),
        sa.Column('warehouse_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['supplier_id'], ['companies.id'], name='fk_mpo_supplier'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name='fk_mpo_warehouse'),
    )
    
    # 物料采购单索引
    op.create_index('idx_mpo_supplier', 'material_purchase_orders', ['supplier_id'])
    op.create_index('idx_mpo_status', 'material_purchase_orders', ['status'])
    op.create_index('idx_mpo_date', 'material_purchase_orders', ['order_date'])
    
    # 2. 物料采购明细表
    op.create_table(
        'material_purchase_items',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('purchase_order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('box_count', sa.Integer(), nullable=False),
        sa.Column('items_per_box', sa.Integer(), nullable=False),
        sa.Column('total_qty', sa.Numeric(12, 3), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('quoted_unit_price', sa.Numeric(12, 4), nullable=True),
        sa.Column('quoted_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('actual_amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('actual_unit_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('received_qty', sa.Numeric(12, 3), nullable=False, server_default='0'),
        sa.Column('is_fully_received', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['purchase_order_id'], ['material_purchase_orders.id'], name='fk_mpi_order', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name='fk_mpi_product'),
    )
    
    # 物料采购明细索引
    op.create_index('idx_mpi_order', 'material_purchase_items', ['purchase_order_id'])
    op.create_index('idx_mpi_product', 'material_purchase_items', ['product_id'])
    
    # 3. 物料批次表
    op.create_table(
        'material_batches',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('batch_no', sa.String(100), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('supplier_name', sa.String(200), nullable=True),
        sa.Column('purchase_order_item_id', sa.Integer(), nullable=True),
        sa.Column('inbound_qty', sa.Numeric(12, 3), nullable=False),
        sa.Column('remaining_qty', sa.Numeric(12, 3), nullable=False),
        sa.Column('unit', sa.String(20), nullable=True),
        sa.Column('unit_cost', sa.Numeric(12, 4), nullable=False),
        sa.Column('total_cost', sa.Numeric(15, 2), nullable=False),
        sa.Column('inbound_date', sa.Date(), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('warehouse_id', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name='fk_mb_product'),
        sa.ForeignKeyConstraint(['purchase_order_item_id'], ['material_purchase_items.id'], name='fk_mb_purchase_item'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name='fk_mb_warehouse'),
    )
    
    # 物料批次索引
    op.create_index('idx_mb_product_active', 'material_batches', ['product_id'],
                    postgresql_where=sa.text("status = 'active' AND remaining_qty > 0"))
    op.create_index('idx_mb_inbound_date', 'material_batches', ['inbound_date'])
    op.create_index('idx_mb_batch_no', 'material_batches', ['batch_no'])


def downgrade() -> None:
    # 删除表（倒序）
    op.drop_index('idx_mb_batch_no', table_name='material_batches')
    op.drop_index('idx_mb_inbound_date', table_name='material_batches')
    op.drop_index('idx_mb_product_active', table_name='material_batches')
    op.drop_table('material_batches')
    
    op.drop_index('idx_mpi_product', table_name='material_purchase_items')
    op.drop_index('idx_mpi_order', table_name='material_purchase_items')
    op.drop_table('material_purchase_items')
    
    op.drop_index('idx_mpo_date', table_name='material_purchase_orders')
    op.drop_index('idx_mpo_status', table_name='material_purchase_orders')
    op.drop_index('idx_mpo_supplier', table_name='material_purchase_orders')
    op.drop_table('material_purchase_orders')
