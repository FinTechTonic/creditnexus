"""add_signup_approval_fields

Revision ID: 413e2bd62d87
Revises: a1b2c3d4e5f6
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '413e2bd62d87'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add signup approval workflow columns to users table
    op.add_column('users', sa.Column('signup_status', sa.String(20), server_default='pending', nullable=False))
    op.add_column('users', sa.Column('signup_submitted_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('signup_reviewed_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('signup_reviewed_by', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('signup_rejection_reason', sa.Text(), nullable=True))
    
    # Create index on signup_status for filtering
    op.create_index(op.f('ix_users_signup_status'), 'users', ['signup_status'], unique=False)
    
    # Create foreign key for signup_reviewed_by
    op.create_foreign_key(
        'fk_users_signup_reviewed_by',
        'users', 'users',
        ['signup_reviewed_by'], ['id'],
        ondelete='SET NULL'
    )
    
    # Update existing users to have approved status (backward compatibility)
    op.execute("UPDATE users SET signup_status = 'approved' WHERE signup_status = 'pending' AND is_active = true")


def downgrade() -> None:
    # Drop foreign key
    op.drop_constraint('fk_users_signup_reviewed_by', 'users', type_='foreignkey')
    
    # Drop index
    op.drop_index(op.f('ix_users_signup_status'), table_name='users')
    
    # Drop columns
    op.drop_column('users', 'signup_rejection_reason')
    op.drop_column('users', 'signup_reviewed_by')
    op.drop_column('users', 'signup_reviewed_at')
    op.drop_column('users', 'signup_submitted_at')
    op.drop_column('users', 'signup_status')
