"""add_user_admin_fields_and_preferences

Revision ID: a93a1d19006b
Revises: 60ea4c0f52c8
Create Date: 2026-01-26 20:32:30.029628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a93a1d19006b'
down_revision: Union[str, Sequence[str], None] = '60ea4c0f52c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add admin fields and preferences to users table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'users' in existing_tables:
        cols = [c["name"] for c in inspector.get_columns("users")]
        
        # Add is_instance_admin column
        if 'is_instance_admin' not in cols:
            op.add_column('users', sa.Column('is_instance_admin', sa.Boolean(), nullable=False, server_default='false'))
            op.create_index('ix_users_is_instance_admin', 'users', ['is_instance_admin'])
        
        # Add organization_role column
        if 'organization_role' not in cols:
            op.add_column('users', sa.Column('organization_role', sa.String(length=50), nullable=True))
            op.create_index('ix_users_organization_role', 'users', ['organization_role'])
        
        # Add preferences column (JSONB)
        if 'preferences' not in cols:
            from sqlalchemy.dialects.postgresql import JSONB
            op.add_column('users', sa.Column('preferences', JSONB(), nullable=True))
        
        # Add api_keys column (JSONB)
        if 'api_keys' not in cols:
            from sqlalchemy.dialects.postgresql import JSONB
            op.add_column('users', sa.Column('api_keys', JSONB(), nullable=True))


def downgrade() -> None:
    """Remove admin fields and preferences from users table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'users' in existing_tables:
        cols = [c["name"] for c in inspector.get_columns("users")]
        
        # Remove api_keys column
        if 'api_keys' in cols:
            try:
                op.drop_column('users', 'api_keys')
            except Exception:
                pass
        
        # Remove preferences column
        if 'preferences' in cols:
            try:
                op.drop_column('users', 'preferences')
            except Exception:
                pass
        
        # Remove organization_role column
        if 'organization_role' in cols:
            try:
                op.drop_index('ix_users_organization_role', table_name='users')
                op.drop_column('users', 'organization_role')
            except Exception:
                pass
        
        # Remove is_instance_admin column
        if 'is_instance_admin' in cols:
            try:
                op.drop_index('ix_users_is_instance_admin', table_name='users')
                op.drop_column('users', 'is_instance_admin')
            except Exception:
                pass
