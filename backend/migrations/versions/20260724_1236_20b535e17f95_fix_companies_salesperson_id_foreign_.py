"""fix companies salesperson_id foreign key to salespersons

Revision ID: 20b535e17f95
Revises: 4abfdf71a594
Create Date: 2026-07-24 12:36:56.457102+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20b535e17f95'
down_revision: Union[str, Sequence[str], None] = '4abfdf71a594'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('companies_salesperson_id_fkey', 'companies', type_='foreignkey')
    op.create_foreign_key(None, 'companies', 'salespersons', ['salesperson_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # 删除自动生成的外键名（需要查询实际名称，这里用通用方式）
    op.drop_constraint(None, 'companies', type_='foreignkey')
    op.create_foreign_key('companies_salesperson_id_fkey', 'companies', 'users', ['salesperson_id'], ['id'])

