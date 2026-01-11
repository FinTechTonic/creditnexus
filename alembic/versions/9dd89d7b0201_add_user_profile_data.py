"""add_user_profile_data

Revision ID: 9dd89d7b0201
Revises: b1bd225cccad
Create Date: 2026-01-09 14:07:34.429665

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '9dd89d7b0201'
down_revision: Union[str, Sequence[str], None] = 'b1bd225cccad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add profile_data JSONB column to users table for enriched profile information."""
    
    # Check if column already exists
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    
    if 'users' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'profile_data' not in columns:
            op.add_column('users', sa.Column('profile_data', JSONB(), nullable=True))
            op.create_index('ix_users_profile_data', 'users', ['profile_data'], postgresql_using='gin')


def downgrade() -> None:
    """Remove profile_data column from users table."""
    op.drop_index('ix_users_profile_data', table_name='users')
    op.drop_column('users', 'profile_data')
