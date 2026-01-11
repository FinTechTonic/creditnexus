"""merge_user_profile_and_policy_template_heads

Revision ID: cb70003e8b8c
Revises: 9dd89d7b0201, 9f0a1b2c3d4e
Create Date: 2026-01-09 22:33:37.182739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb70003e8b8c'
down_revision: Union[str, Sequence[str], None] = ('9dd89d7b0201', '9f0a1b2c3d4e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
