"""add_purchase_return_tables

Revision ID: 62636a3a9cb3
Revises: fb02190e371e
Create Date: 2026-06-27 17:25:56.860971+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '62636a3a9cb3'
down_revision: Union[str, Sequence[str], None] = 'fb02190e371e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('purchase_return_orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('return_no', sa.String(length=30), nullable=False),
        sa.Column('purchase_order_type', sa.String(length=20), nullable=False),
        sa.Column('purchase_order_v2_id', sa.Integer(), nullable=True),
        sa.Column('material_purchase_order_id', sa.Integer(), nullable=True),
        sa.Column('return_date', sa.Date(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('supplier_name', sa.String(length=200), nullable=True),
        sa.Column('total_weight_kg', sa.Numeric(precision=12, scale=3), nullable=False, server_default=sa.text('0')),
        sa.Column('total_amount', sa.Numeric(precision=15, scale=2), nullable=False, server_default=sa.text('0')),
        sa.Column('refund_method', sa.Enum('DEDUCT_PAYABLE', 'DIRECT_REFUND', 'DEFERRED', name='purchaserefundmethod'), nullable=True),
        sa.Column('refund_amount', sa.Numeric(precision=15, scale=2), nullable=False, server_default=sa.text('0')),
        sa.Column('refund_date', sa.Date(), nullable=True),
        sa.Column('bank_account_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'COMPLETED', 'REJECTED', 'CANCELLED', name='purchasereturnstatus'), nullable=False),
        sa.Column('problem_description', sa.Text(), nullable=True),
        sa.Column('supplier_feedback', sa.Text(), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('approved_by_id', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['bank_account_id'], ['bank_accounts.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['material_purchase_order_id'], ['material_purchase_orders.id']),
        sa.ForeignKeyConstraint(['purchase_order_v2_id'], ['purchase_orders_v2.id']),
        sa.ForeignKeyConstraint(['supplier_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('return_no')
    )
    op.create_table('purchase_return_attachments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('return_order_id', sa.Integer(), nullable=False),
        sa.Column('file_type', sa.Enum('IMAGE', 'VIDEO', 'DOCUMENT', name='purchasereturnattachmenttype'), nullable=False),
        sa.Column('original_name', sa.String(length=255), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['return_order_id'], ['purchase_return_orders.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('purchase_return_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('return_order_id', sa.Integer(), nullable=False),
        sa.Column('weight_kg', sa.Numeric(precision=12, scale=3), nullable=False, server_default=sa.text('0')),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=4), nullable=False, server_default=sa.text('0')),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False, server_default=sa.text('0')),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('purchase_order_product_v2_id', sa.Integer(), nullable=True),
        sa.Column('material_purchase_item_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['material_purchase_item_id'], ['material_purchase_items.id']),
        sa.ForeignKeyConstraint(['purchase_order_product_v2_id'], ['purchase_order_products_v2.id']),
        sa.ForeignKeyConstraint(['return_order_id'], ['purchase_return_orders.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('purchase_return_items')
    op.drop_table('purchase_return_attachments')
    op.drop_table('purchase_return_orders')
