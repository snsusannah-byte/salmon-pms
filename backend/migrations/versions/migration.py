"""add finished product receipts and aftersales tables

Revision ID: 8153451b33a0
Revises: ecd5c69be146
Create Date: 2026-05-02 00:00:00.000000+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8153451b33a0'
down_revision: Union[str, Sequence[str], None] = 'ecd5c69be146'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create finished_product_receipts table
    op.create_table(
        'finished_product_receipts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sale_id', sa.Integer(), nullable=False),
        sa.Column('receipt_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('bank_account_id', sa.Integer(), nullable=True),
        sa.Column('reference_no', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['bank_account_id'], ['bank_accounts.id']),
        sa.ForeignKeyConstraint(['sale_id'], ['finished_product_sales.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create finished_product_aftersales table
    op.create_table(
        'finished_product_aftersales',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sale_id', sa.Integer(), nullable=False),
        sa.Column('record_date', sa.Date(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=True),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sale_id'], ['finished_product_sales.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('finished_product_aftersales')
    op.drop_table('finished_product_receipts')
