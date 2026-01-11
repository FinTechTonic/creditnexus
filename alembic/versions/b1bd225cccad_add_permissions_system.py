"""add_permissions_system

Revision ID: b1bd225cccad
Revises: dcf895ebe666
Create Date: 2026-01-09 13:59:25.423529

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'b1bd225cccad'
down_revision: Union[str, Sequence[str], None] = 'dcf895ebe666'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add permission system: permissions column, permission_definitions table, role_permissions junction table."""
    
    # Check if tables already exist
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    # Add permissions JSONB column to users table
    if 'users' in tables:
        # Check if column already exists
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'permissions' not in columns:
            op.add_column('users', sa.Column('permissions', JSONB(), nullable=True))
            op.create_index('ix_users_permissions', 'users', ['permissions'], postgresql_using='gin')
    
    # Create permission_definitions table
    if 'permission_definitions' not in tables:
        op.create_table(
            'permission_definitions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False, unique=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('category', sa.String(length=50), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_permission_definitions_name', 'permission_definitions', ['name'], unique=True)
        op.create_index('ix_permission_definitions_category', 'permission_definitions', ['category'])
    
    # Create role_permissions junction table
    if 'role_permissions' not in tables:
        op.create_table(
            'role_permissions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('role', sa.String(length=50), nullable=False),
            sa.Column('permission_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['permission_id'], ['permission_definitions.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('role', 'permission_id', name='uq_role_permission'),
        )
        op.create_index('ix_role_permissions_role', 'role_permissions', ['role'])
        op.create_index('ix_role_permissions_permission_id', 'role_permissions', ['permission_id'])


def downgrade() -> None:
    """Remove permission system tables and columns."""
    
    # Drop role_permissions table
    op.drop_index('ix_role_permissions_permission_id', table_name='role_permissions')
    op.drop_index('ix_role_permissions_role', table_name='role_permissions')
    op.drop_table('role_permissions')
    
    # Drop permission_definitions table
    op.drop_index('ix_permission_definitions_category', table_name='permission_definitions')
    op.drop_index('ix_permission_definitions_name', table_name='permission_definitions')
    op.drop_table('permission_definitions')
    
    # Remove permissions column from users table
    op.drop_index('ix_users_permissions', table_name='users')
    op.drop_column('users', 'permissions')
