"""add_policy_editor_tables

Revision ID: 928e94cec841
Revises: 413e2bd62d87
Create Date: 2026-01-09 16:49:14.576703

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '928e94cec841'
down_revision: Union[str, Sequence[str], None] = '413e2bd62d87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy.dialects import postgresql
    
    # Create policies table
    op.create_table(
        'policies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rules_yaml', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='draft', nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_policies_name'), 'policies', ['name'], unique=False)
    op.create_index(op.f('ix_policies_category'), 'policies', ['category'], unique=False)
    op.create_index(op.f('ix_policies_status'), 'policies', ['status'], unique=False)
    op.create_index(op.f('ix_policies_deleted_at'), 'policies', ['deleted_at'], unique=False)
    
    # Create policy_versions table
    op.create_table(
        'policy_versions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('rules_yaml', sa.Text(), nullable=False),
        sa.Column('changes_summary', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_policy_versions_policy_id'), 'policy_versions', ['policy_id'], unique=False)
    
    # Create policy_approvals table
    op.create_table(
        'policy_approvals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('approved_by', sa.Integer(), nullable=False),
        sa.Column('approved_at', sa.DateTime(), nullable=False),
        sa.Column('approval_status', sa.String(length=50), nullable=False),
        sa.Column('approval_comment', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_policy_approvals_policy_id'), 'policy_approvals', ['policy_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_policy_approvals_policy_id'), table_name='policy_approvals')
    op.drop_table('policy_approvals')
    op.drop_index(op.f('ix_policy_versions_policy_id'), table_name='policy_versions')
    op.drop_table('policy_versions')
    op.drop_index(op.f('ix_policies_deleted_at'), table_name='policies')
    op.drop_index(op.f('ix_policies_status'), table_name='policies')
    op.drop_index(op.f('ix_policies_category'), table_name='policies')
    op.drop_index(op.f('ix_policies_name'), table_name='policies')
    op.drop_table('policies')
