"""fix_companytype_enum_case

Revision ID: f7cee2171e4e
Revises: f7cee2171e4d
Create Date: 2026-05-15 11:53:00.000000+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f7cee2171e4e'
down_revision: Union[str, Sequence[str], None] = 'f7cee2171e4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """将 companytype 枚举值改为小写，与代码一致"""
    # PostgreSQL 不支持直接修改枚举值，需要先转换为 text 再改回来
    
    # 1. 将 companies.type 改为 text 类型
    op.alter_column('companies', 'type',
                    existing_type=postgresql.ENUM('PROCESSING_PLANT', 'FISH_FARM', 'EXPORTER', 'SUPPLIER', 'CUSTOMER', 'CUSTOMS_BROKER', 'LOGISTICS', 'INTERNAL', name='companytype'),
                    type_=sa.Text(),
                    existing_nullable=False,
                    postgresql_using='type::text')
    
    # 2. 删除旧枚举
    op.execute("DROP TYPE IF EXISTS companytype")
    
    # 3. 创建新枚举（小写）
    op.execute("CREATE TYPE companytype AS ENUM ('processing_plant', 'fish_farm', 'exporter', 'supplier', 'customer', 'customs_broker', 'logistics', 'internal')")
    
    # 4. 将 text 转换回枚举
    op.alter_column('companies', 'type',
                    existing_type=sa.Text(),
                    type_=postgresql.ENUM('processing_plant', 'fish_farm', 'exporter', 'supplier', 'customer', 'customs_broker', 'logistics', 'internal', name='companytype'),
                    existing_nullable=False,
                    postgresql_using='LOWER(type)::companytype')


def downgrade() -> None:
    """回滚：将枚举值改回大写"""
    # 1. 将 companies.type 改为 text
    op.alter_column('companies', 'type',
                    existing_type=postgresql.ENUM('processing_plant', 'fish_farm', 'exporter', 'supplier', 'customer', 'customs_broker', 'logistics', 'internal', name='companytype'),
                    type_=sa.Text(),
                    existing_nullable=False,
                    postgresql_using='type::text')
    
    # 2. 删除新枚举
    op.execute("DROP TYPE IF EXISTS companytype")
    
    # 3. 创建旧枚举（大写）
    op.execute("CREATE TYPE companytype AS ENUM ('PROCESSING_PLANT', 'FISH_FARM', 'EXPORTER', 'SUPPLIER', 'CUSTOMER', 'CUSTOMS_BROKER', 'LOGISTICS', 'INTERNAL')")
    
    # 4. 将 text 转换回枚举
    op.alter_column('companies', 'type',
                    existing_type=sa.Text(),
                    type_=postgresql.ENUM('PROCESSING_PLANT', 'FISH_FARM', 'EXPORTER', 'SUPPLIER', 'CUSTOMER', 'CUSTOMS_BROKER', 'LOGISTICS', 'INTERNAL', name='companytype'),
                    existing_nullable=False,
                    postgresql_using='UPPER(type)::companytype')
