"""add_demo_data_tracking

Revision ID: 1e2d90fbb7c1
Revises: cb70003e8b8c
Create Date: 2026-01-10 22:05:43.789271

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '1e2d90fbb7c1'
down_revision: Union[str, Sequence[str], None] = 'cb70003e8b8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Create demo_seeding_status table if it doesn't exist
    table_created = False
    if 'demo_seeding_status' not in existing_tables:
        op.create_table(
            'demo_seeding_status',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('stage', sa.String(50), nullable=False),
            sa.Column('progress', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'),
            sa.Column('total', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('current', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('errors', sa.JSON(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id')
        )
        table_created = True
    
    # Create indexes for demo_seeding_status if they don't exist
    if table_created:
        # Table was just created, so indexes don't exist yet - create them
        op.create_index(op.f('ix_demo_seeding_status_stage'), 'demo_seeding_status', ['stage'], unique=False)
        op.create_index(op.f('ix_demo_seeding_status_status'), 'demo_seeding_status', ['status'], unique=False)
    else:
        # Table exists, check which indexes are missing
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('demo_seeding_status')]
        if 'ix_demo_seeding_status_stage' not in existing_indexes:
            op.create_index(op.f('ix_demo_seeding_status_stage'), 'demo_seeding_status', ['stage'], unique=False)
        if 'ix_demo_seeding_status_status' not in existing_indexes:
            op.create_index(op.f('ix_demo_seeding_status_status'), 'demo_seeding_status', ['status'], unique=False)
    
    # Add is_demo column to deals table if it doesn't exist
    if 'deals' in existing_tables:
        deals_columns = [col['name'] for col in inspector.get_columns('deals')]
        if 'is_demo' not in deals_columns:
            op.add_column('deals', sa.Column('is_demo', sa.Boolean(), nullable=True, server_default='false'))
    else:
        op.add_column('deals', sa.Column('is_demo', sa.Boolean(), nullable=True, server_default='false'))
    
    # Add is_demo column to documents table if it doesn't exist
    if 'documents' in existing_tables:
        documents_columns = [col['name'] for col in inspector.get_columns('documents')]
        if 'is_demo' not in documents_columns:
            op.add_column('documents', sa.Column('is_demo', sa.Boolean(), nullable=True, server_default='false'))
    else:
        op.add_column('documents', sa.Column('is_demo', sa.Boolean(), nullable=True, server_default='false'))
    
    # Create indexes for filtering demo data if they don't exist
    if 'deals' in existing_tables:
        deals_indexes = [idx['name'] for idx in inspector.get_indexes('deals')]
        if 'ix_deals_is_demo' not in deals_indexes:
            op.create_index(op.f('ix_deals_is_demo'), 'deals', ['is_demo'], unique=False)
    
    if 'documents' in existing_tables:
        documents_indexes = [idx['name'] for idx in inspector.get_indexes('documents')]
        if 'ix_documents_is_demo' not in documents_indexes:
            op.create_index(op.f('ix_documents_is_demo'), 'documents', ['is_demo'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index(op.f('ix_documents_is_demo'), table_name='documents')
    op.drop_index(op.f('ix_deals_is_demo'), table_name='deals')
    
    # Drop columns
    op.drop_column('documents', 'is_demo')
    op.drop_column('deals', 'is_demo')
    
    # Drop indexes for demo_seeding_status
    op.drop_index(op.f('ix_demo_seeding_status_status'), table_name='demo_seeding_status')
    op.drop_index(op.f('ix_demo_seeding_status_stage'), table_name='demo_seeding_status')
    
    # Drop demo_seeding_status table
    op.drop_table('demo_seeding_status')
