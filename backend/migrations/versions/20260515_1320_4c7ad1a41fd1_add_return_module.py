"""add_return_module

Revision ID: 4c7ad1a41fd1
Revises: f7cee2171e4e
Create Date: 2026-05-15 13:20:07.630345+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c7ad1a41fd1'
down_revision: Union[str, Sequence[str], None] = 'f7cee2171e4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ==================== 退货单 ====================
    op.create_table(
        'return_orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('return_no', sa.String(length=30), nullable=False),
        sa.Column('sale_type', sa.String(length=20), nullable=False),
        sa.Column('whole_fish_sale_id', sa.Integer(), nullable=True),
        sa.Column('finished_product_sale_id', sa.Integer(), nullable=True),
        sa.Column('return_date', sa.Date(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('processing_plant_id', sa.Integer(), nullable=True),
        sa.Column('processing_plant_name', sa.String(length=200), nullable=True),
        sa.Column('total_weight_kg', sa.Numeric(precision=12, scale=3), server_default='0'),
        sa.Column('total_quantity', sa.Integer(), server_default='0'),
        sa.Column('total_amount', sa.Numeric(precision=15, scale=2), server_default='0'),
        sa.Column('refund_method', sa.Enum('direct_refund', 'balance_deduction', 'prepayment', 'deferred', name='refundmethod'), nullable=True),
        sa.Column('refund_amount', sa.Numeric(precision=15, scale=2), server_default='0'),
        sa.Column('refund_date', sa.Date(), nullable=True),
        sa.Column('bank_account_id', sa.Integer(), nullable=True),
        sa.Column('transaction_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'pending_approval', 'approved', 'refunding', 'completed', 'rejected', 'cancelled', name='returnstatus'), server_default='draft'),
        sa.Column('problem_description', sa.Text(), nullable=True),
        sa.Column('customer_feedback', sa.Text(), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('approved_by_id', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['bank_account_id'], ['bank_accounts.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['finished_product_sale_id'], ['finished_product_sales.id']),
        sa.ForeignKeyConstraint(['processing_plant_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['transaction_id'], ['transaction_records.id']),
        sa.ForeignKeyConstraint(['whole_fish_sale_id'], ['whole_fish_sales.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('return_no')
    )

    # ==================== 退货明细 ====================
    op.create_table(
        'return_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('return_order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('product_name', sa.String(length=100), nullable=True),
        sa.Column('spec', sa.String(length=100), nullable=True),
        sa.Column('quantity', sa.Integer(), server_default='0'),
        sa.Column('weight_kg', sa.Numeric(precision=12, scale=3), server_default='0'),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=4), server_default='0'),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), server_default='0'),
        sa.Column('return_reason', sa.Enum('quality_issue', 'logistics_damage', 'spec_mismatch', 'temperature_issue', 'foreign_matter', 'customer_reason', 'expired', 'other', name='returnreason'), nullable=False),
        sa.Column('reason_detail', sa.Text(), nullable=True),
        sa.Column('whole_fish_sale_item_id', sa.Integer(), nullable=True),
        sa.Column('finished_product_sale_item_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['finished_product_sale_item_id'], ['finished_product_sale_items.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['return_order_id'], ['return_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['whole_fish_sale_item_id'], ['whole_fish_sale_items.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # ==================== 退货附件 ====================
    op.create_table(
        'return_attachments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('return_order_id', sa.Integer(), nullable=False),
        sa.Column('file_type', sa.Enum('image', 'video', 'document', name='returnattachmenttype'), nullable=False),
        sa.Column('original_name', sa.String(length=255), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), server_default='0'),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['return_order_id'], ['return_orders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # ==================== 索引 ====================
    op.create_index('ix_return_orders_return_date', 'return_orders', ['return_date'])
    op.create_index('ix_return_orders_customer_id', 'return_orders', ['customer_id'])
    op.create_index('ix_return_orders_processing_plant_id', 'return_orders', ['processing_plant_id'])
    op.create_index('ix_return_orders_status', 'return_orders', ['status'])
    op.create_index('ix_return_orders_whole_fish_sale_id', 'return_orders', ['whole_fish_sale_id'])
    op.create_index('ix_return_orders_finished_product_sale_id', 'return_orders', ['finished_product_sale_id'])
    op.create_index('ix_return_items_return_order_id', 'return_items', ['return_order_id'])
    op.create_index('ix_return_items_return_reason', 'return_items', ['return_reason'])
    op.create_index('ix_return_attachments_return_order_id', 'return_attachments', ['return_order_id'])

    # ==================== 补充外键 ====================
    op.create_foreign_key(None, 'whole_fish_sales', 'users', ['salesperson_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_return_attachments_return_order_id', table_name='return_attachments')
    op.drop_index('ix_return_items_return_reason', table_name='return_items')
    op.drop_index('ix_return_items_return_order_id', table_name='return_items')
    op.drop_index('ix_return_orders_finished_product_sale_id', table_name='return_orders')
    op.drop_index('ix_return_orders_whole_fish_sale_id', table_name='return_orders')
    op.drop_index('ix_return_orders_status', table_name='return_orders')
    op.drop_index('ix_return_orders_processing_plant_id', table_name='return_orders')
    op.drop_index('ix_return_orders_customer_id', table_name='return_orders')
    op.drop_index('ix_return_orders_return_date', table_name='return_orders')

    op.drop_table('return_attachments')
    op.drop_table('return_items')
    op.drop_table('return_orders')

    # 删除枚举类型
    op.execute("DROP TYPE IF EXISTS returnattachmenttype")
    op.execute("DROP TYPE IF EXISTS returnreason")
    op.execute("DROP TYPE IF EXISTS refundmethod")
    op.execute("DROP TYPE IF EXISTS returnstatus")

    op.drop_constraint(None, 'whole_fish_sales', type_='foreignkey')
