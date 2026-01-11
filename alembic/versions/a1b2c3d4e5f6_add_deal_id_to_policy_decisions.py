"""Add deal_id to policy_decisions table.

Revision ID: a1b2c3d4e5f6
Revises: 9699102e6d82
Create Date: 2025-01-XX XX:XX:XX.XXXXXX
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9699102e6d82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add deal_id foreign key to policy_decisions table."""
    # Add deal_id column
    op.add_column('policy_decisions', sa.Column('deal_id', sa.Integer(), nullable=True))
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_policy_decisions_deal_id',
        'policy_decisions',
        'deals',
        ['deal_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create index for fast queries
    op.create_index('idx_policy_decisions_deal_id', 'policy_decisions', ['deal_id'], unique=False)


def downgrade() -> None:
    """Remove deal_id column from policy_decisions table."""
    op.drop_index('idx_policy_decisions_deal_id', table_name='policy_decisions')
    op.drop_constraint('fk_policy_decisions_deal_id', 'policy_decisions', type_='foreignkey')
    op.drop_column('policy_decisions', 'deal_id')
