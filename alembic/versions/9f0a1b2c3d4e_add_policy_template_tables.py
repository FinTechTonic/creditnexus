"""Add policy template tables

Revision ID: 9f0a1b2c3d4e
Revises: 928e94cec841
Create Date: 2024-12-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9f0a1b2c3d4e'
down_revision = '928e94cec841'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    # Create policy_templates table
    if 'policy_templates' not in tables:
        op.create_table(
            'policy_templates',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('category', sa.String(length=100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('rules_yaml', sa.Text(), nullable=False),
            sa.Column('use_case', sa.String(length=255), nullable=True),
            sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('is_system_template', sa.Boolean(), default=False, nullable=False),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
    
    # Create indexes if they don't exist
    if 'policy_templates' in tables:
        indexes = [idx['name'] for idx in inspector.get_indexes('policy_templates')]
    else:
        indexes = []
    
    if 'ix_policy_templates_category' not in indexes:
        op.create_index(op.f('ix_policy_templates_category'), 'policy_templates', ['category'], unique=False)
    if 'ix_policy_templates_use_case' not in indexes:
        op.create_index(op.f('ix_policy_templates_use_case'), 'policy_templates', ['use_case'], unique=False)
    if 'ix_policy_templates_is_system_template' not in indexes:
        op.create_index(op.f('ix_policy_templates_is_system_template'), 'policy_templates', ['is_system_template'], unique=False)


def downgrade() -> None:
    # Check if table exists before dropping
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'policy_templates' in tables:
        indexes = [idx['name'] for idx in inspector.get_indexes('policy_templates')]
        
        if 'ix_policy_templates_is_system_template' in indexes:
            op.drop_index(op.f('ix_policy_templates_is_system_template'), table_name='policy_templates')
        if 'ix_policy_templates_use_case' in indexes:
            op.drop_index(op.f('ix_policy_templates_use_case'), table_name='policy_templates')
        if 'ix_policy_templates_category' in indexes:
            op.drop_index(op.f('ix_policy_templates_category'), table_name='policy_templates')
        
        op.drop_table('policy_templates')
