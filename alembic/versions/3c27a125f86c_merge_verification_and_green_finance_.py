"""merge_verification_and_green_finance_heads

Revision ID: 3c27a125f86c
Revises: add_remote_verification, e81cf5457d2d
Create Date: 2026-01-13 03:43:15.601071

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c27a125f86c'
down_revision: Union[str, Sequence[str], None] = ('add_remote_verification', 'e81cf5457d2d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
