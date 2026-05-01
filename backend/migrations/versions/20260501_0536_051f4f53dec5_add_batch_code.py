"""add_batch_code

Revision ID: 051f4f53dec5
Revises: 01db638ad219
Create Date: 2026-05-01 05:36:23.856554+08:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '051f4f53dec5'
down_revision: Union[str, Sequence[str], None] = '01db638ad219'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite 需要使用 batch_alter_table
    with op.batch_alter_table('batches', schema=None) as batch_op:
        batch_op.add_column(sa.Column('batch_code', sa.String(length=20), nullable=True))
        batch_op.create_unique_constraint('uq_batches_batch_code', ['batch_code'])

    # 为现有数据生成 batch_code
    conn = op.get_bind()
    result = conn.execute(text("SELECT id, batch_date FROM batches ORDER BY id"))
    rows = result.fetchall()

    used_codes = set()
    for row in rows:
        batch_id, batch_date = row
        if isinstance(batch_date, str):
            from datetime import date as dt_date
            batch_date = dt_date.fromisoformat(batch_date)
        date_str = batch_date.strftime("%Y%m%d")

        max_num = 0
        for code in used_codes:
            if code.startswith(date_str + "-"):
                try:
                    num = int(code.split("-")[-1])
                    max_num = max(max_num, num)
                except:
                    pass

        new_num = max_num + 1
        code = f"{date_str}-{new_num:03d}"
        used_codes.add(code)

        conn.execute(
            text("UPDATE batches SET batch_code = :code WHERE id = :id"),
            {"code": code, "id": batch_id}
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('batches', schema=None) as batch_op:
        batch_op.drop_constraint('uq_batches_batch_code', type_='unique')
        batch_op.drop_column('batch_code')
