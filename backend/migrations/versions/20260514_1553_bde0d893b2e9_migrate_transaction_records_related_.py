"""migrate transaction_records.related_sale_ids to JSONB

Revision ID: bde0d893b2e9
Revises: 7c2b9d4e8f31
Create Date: 2026-05-14 15:53:36.399089+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bde0d893b2e9'
down_revision: Union[str, Sequence[str], None] = '7c2b9d4e8f31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 将 related_sale_ids 从 TEXT 迁移到 JSONB
    # 使用 USING 子句将现有 JSON 字符串转换为 JSONB
    op.execute(
        "ALTER TABLE transaction_records "
        "ALTER COLUMN related_sale_ids TYPE JSONB "
        "USING related_sale_ids::jsonb"
    )
    # 添加 GIN 索引加速 JSONB 包含查询
    op.create_index(
        'ix_transaction_records_related_sale_ids_gin',
        'transaction_records',
        ['related_sale_ids'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_transaction_records_related_sale_ids_gin', table_name='transaction_records')
    op.execute(
        "ALTER TABLE transaction_records "
        "ALTER COLUMN related_sale_ids TYPE TEXT "
        "USING related_sale_ids::text"
    )
