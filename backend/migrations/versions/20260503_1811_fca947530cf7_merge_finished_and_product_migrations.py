"""merge finished and product migrations

Revision ID: fca947530cf7
Revises: b500c5f12785
Create Date: 2026-05-03 18:11:32.661524+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fca947530cf7'
down_revision: Union[str, Sequence[str], None] = 'b500c5f12785'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
