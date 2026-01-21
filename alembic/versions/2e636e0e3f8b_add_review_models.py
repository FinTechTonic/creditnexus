"""add_review_models

Revision ID: 2e636e0e3f8b
Revises: c80aa4258269
Create Date: 2026-01-20 19:48:48.113499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '2e636e0e3f8b'
down_revision: Union[str, Sequence[str], None] = 'c80aa4258269'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create review_comments and review_assignments tables."""
    # Check if tables already exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Review Comments table
    if 'review_comments' not in existing_tables:
        op.create_table(
            'review_comments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('document_id', sa.Integer(), nullable=False),
            sa.Column('version_id', sa.Integer(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('comment_text', sa.Text(), nullable=False),
            sa.Column('comment_type', sa.String(length=20), nullable=False, server_default='general'),
            sa.Column('target_field', sa.String(length=255), nullable=True),
            sa.Column('target_range', JSONB(), nullable=True),
            sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('resolved_by', sa.Integer(), nullable=True),
            sa.Column('resolved_at', sa.DateTime(), nullable=True),
            sa.Column('parent_comment_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name='fk_review_comments_document', ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['version_id'], ['document_versions.id'], name='fk_review_comments_version', ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_review_comments_user'),
            sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], name='fk_review_comments_resolver'),
            sa.ForeignKeyConstraint(['parent_comment_id'], ['review_comments.id'], name='fk_review_comments_parent', ondelete='CASCADE'),
        )
        
        # Create indexes
        op.create_index('ix_review_comments_document_id', 'review_comments', ['document_id'])
        op.create_index('ix_review_comments_version_id', 'review_comments', ['version_id'])
        op.create_index('ix_review_comments_user_id', 'review_comments', ['user_id'])
        op.create_index('ix_review_comments_comment_type', 'review_comments', ['comment_type'])
        op.create_index('ix_review_comments_target_field', 'review_comments', ['target_field'])
        op.create_index('ix_review_comments_resolved', 'review_comments', ['resolved'])
        op.create_index('ix_review_comments_parent_comment_id', 'review_comments', ['parent_comment_id'])
    
    # Review Assignments table
    if 'review_assignments' not in existing_tables:
        op.create_table(
            'review_assignments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('document_id', sa.Integer(), nullable=False),
            sa.Column('workflow_id', sa.Integer(), nullable=True),
            sa.Column('reviewer_id', sa.Integer(), nullable=False),
            sa.Column('assigned_by', sa.Integer(), nullable=False),
            sa.Column('assigned_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('due_date', sa.DateTime(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('review_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name='fk_review_assignments_document', ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], name='fk_review_assignments_workflow', ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], name='fk_review_assignments_reviewer'),
            sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], name='fk_review_assignments_assigner'),
        )
        
        # Create indexes
        op.create_index('ix_review_assignments_document_id', 'review_assignments', ['document_id'])
        op.create_index('ix_review_assignments_workflow_id', 'review_assignments', ['workflow_id'])
        op.create_index('ix_review_assignments_reviewer_id', 'review_assignments', ['reviewer_id'])
        op.create_index('ix_review_assignments_assigned_by', 'review_assignments', ['assigned_by'])
        op.create_index('ix_review_assignments_due_date', 'review_assignments', ['due_date'])
        op.create_index('ix_review_assignments_status', 'review_assignments', ['status'])


def downgrade() -> None:
    """Drop review_comments and review_assignments tables."""
    op.drop_index('ix_review_assignments_status', table_name='review_assignments')
    op.drop_index('ix_review_assignments_due_date', table_name='review_assignments')
    op.drop_index('ix_review_assignments_assigned_by', table_name='review_assignments')
    op.drop_index('ix_review_assignments_reviewer_id', table_name='review_assignments')
    op.drop_index('ix_review_assignments_workflow_id', table_name='review_assignments')
    op.drop_index('ix_review_assignments_document_id', table_name='review_assignments')
    op.drop_table('review_assignments')
    
    op.drop_index('ix_review_comments_parent_comment_id', table_name='review_comments')
    op.drop_index('ix_review_comments_resolved', table_name='review_comments')
    op.drop_index('ix_review_comments_target_field', table_name='review_comments')
    op.drop_index('ix_review_comments_comment_type', table_name='review_comments')
    op.drop_index('ix_review_comments_user_id', table_name='review_comments')
    op.drop_index('ix_review_comments_version_id', table_name='review_comments')
    op.drop_index('ix_review_comments_document_id', table_name='review_comments')
    op.drop_table('review_comments')
