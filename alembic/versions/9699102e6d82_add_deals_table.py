"""add_deals_table

Revision ID: 9699102e6d82
Revises: 9dd89d7b0201
Create Date: 2026-01-09 14:28:45.695359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '9699102e6d82'
down_revision: Union[str, Sequence[str], None] = 'b1bd225cccad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add deals table and deal_id foreign key to documents table."""
    
    # Check if tables already exist
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    # Create deals table
    if 'deals' not in tables:
        op.create_table(
            'deals',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('deal_id', sa.String(length=255), nullable=False, unique=True),
            sa.Column('applicant_id', sa.Integer(), nullable=False),
            sa.Column('application_id', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
            sa.Column('deal_type', sa.String(length=50), nullable=True),
            sa.Column('deal_data', JSONB(), nullable=True),
            sa.Column('folder_path', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['applicant_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        )
        op.create_index('ix_deals_deal_id', 'deals', ['deal_id'], unique=True)
        op.create_index('ix_deals_applicant_id', 'deals', ['applicant_id'], unique=False)
        op.create_index('ix_deals_application_id', 'deals', ['application_id'], unique=False)
        op.create_index('ix_deals_status', 'deals', ['status'], unique=False)
        op.create_index('ix_deals_deal_type', 'deals', ['deal_type'], unique=False)
    
    # Add deal_id foreign key to documents table
    if 'documents' in tables:
        columns = [col['name'] for col in inspector.get_columns('documents')]
        if 'deal_id' not in columns:
            op.add_column('documents', sa.Column('deal_id', sa.Integer(), nullable=True))
            op.create_foreign_key('fk_documents_deal_id', 'documents', 'deals', ['deal_id'], ['id'], ondelete='SET NULL')
            op.create_index('ix_documents_deal_id', 'documents', ['deal_id'], unique=False)
    
    # Create deal_notes table
    if 'deal_notes' not in tables:
        op.create_table(
            'deal_notes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('deal_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('note_type', sa.String(length=50), nullable=True),
            sa.Column('metadata', JSONB(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        )
        op.create_index('ix_deal_notes_deal_id', 'deal_notes', ['deal_id'], unique=False)
        op.create_index('ix_deal_notes_user_id', 'deal_notes', ['user_id'], unique=False)


def downgrade() -> None:
    """Remove deals table and deal_id column from documents."""
    
    # Check if tables exist
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    # Remove deal_id from documents table
    if 'documents' in tables:
        columns = [col['name'] for col in inspector.get_columns('documents')]
        if 'deal_id' in columns:
            op.drop_constraint('fk_documents_deal_id', 'documents', type_='foreignkey')
            op.drop_index('ix_documents_deal_id', table_name='documents')
            op.drop_column('documents', 'deal_id')
    
    # Drop deal_notes table
    if 'deal_notes' in tables:
        op.drop_index('ix_deal_notes_user_id', table_name='deal_notes')
        op.drop_index('ix_deal_notes_deal_id', table_name='deal_notes')
        op.drop_table('deal_notes')
    
    # Drop deals table
    if 'deals' in tables:
        op.drop_index('ix_deals_deal_type', table_name='deals')
        op.drop_index('ix_deals_status', table_name='deals')
        op.drop_index('ix_deals_application_id', table_name='deals')
        op.drop_index('ix_deals_applicant_id', table_name='deals')
        op.drop_index('ix_deals_deal_id', table_name='deals')
        op.drop_table('deals')
