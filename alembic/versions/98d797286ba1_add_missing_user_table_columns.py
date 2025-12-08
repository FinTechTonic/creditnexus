"""Add missing user table columns

Revision ID: 98d797286ba1
Revises: 781c3c4131c9
Create Date: 2025-12-08 15:22:19.624397

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '98d797286ba1'
down_revision: Union[str, Sequence[str], None] = '781c3c4131c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to users table."""
    # Add is_email_verified column
    op.add_column('users', sa.Column('is_email_verified', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add failed_login_attempts column
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    
    # Add locked_until column
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True))
    
    # Add password_changed_at column
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove columns from users table."""
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'is_email_verified')
