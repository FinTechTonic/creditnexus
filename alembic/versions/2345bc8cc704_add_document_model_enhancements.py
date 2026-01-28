"""add document model enhancements

Revision ID: 2345bc8cc704
Revises: 1245cc8cc703
Create Date: 2026-01-28 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2345bc8cc704'
down_revision: Union[str, Sequence[str], None] = '1245cc8cc703'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add document model enhancement fields to documents table."""
    op.add_column('documents', sa.Column('classification', sa.String(length=50), nullable=True))
    op.add_column('documents', sa.Column('status', sa.String(length=50), server_default='draft', nullable=False))
    op.add_column('documents', sa.Column('retention_policy', sa.String(length=100), nullable=True))
    op.add_column('documents', sa.Column('retention_expires_at', sa.DateTime(), nullable=True))
    op.add_column('documents', sa.Column('parent_document_id', sa.Integer(), nullable=True))
    op.add_column('documents', sa.Column('compliance_status', sa.String(length=50), server_default='pending', nullable=False))
    op.add_column('documents', sa.Column('regulatory_check_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    op.create_foreign_key('fk_documents_parent_document_id', 'documents', 'documents', ['parent_document_id'], ['id'])
    
    op.create_index(op.f('ix_documents_classification'), 'documents', ['classification'], unique=False)
    op.create_index(op.f('ix_documents_status'), 'documents', ['status'], unique=False)
    op.create_index(op.f('ix_documents_parent_document_id'), 'documents', ['parent_document_id'], unique=False)
    op.create_index(op.f('ix_documents_compliance_status'), 'documents', ['compliance_status'], unique=False)


def downgrade() -> None:
    """Remove document model enhancement fields from documents table."""
    op.drop_index(op.f('ix_documents_compliance_status'), table_name='documents')
    op.drop_index(op.f('ix_documents_parent_document_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_status'), table_name='documents')
    op.drop_index(op.f('ix_documents_classification'), table_name='documents')
    
    op.drop_constraint('fk_documents_parent_document_id', 'documents', type_='foreignkey')
    
    op.drop_column('documents', 'regulatory_check_metadata')
    op.drop_column('documents', 'compliance_status')
    op.drop_column('documents', 'parent_document_id')
    op.drop_column('documents', 'retention_expires_at')
    op.drop_column('documents', 'retention_policy')
    op.drop_column('documents', 'status')
    op.drop_column('documents', 'classification')
