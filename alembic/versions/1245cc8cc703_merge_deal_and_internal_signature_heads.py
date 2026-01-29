"""merge deal and internal signature heads

Revision ID: 1245cc8cc703
Revises: 7d47d1a7fd1b, cafedeadbeef
Create Date: 2026-01-28 11:19:05.845874

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1245cc8cc703'
down_revision: Union[str, Sequence[str], None] = ('7d47d1a7fd1b', 'cafedeadbeef')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
