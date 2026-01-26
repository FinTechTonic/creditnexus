"""add_deal_signature_documentation_tracking

Revision ID: 7d47d1a7fd1b
Revises: a93a1d19006b
Create Date: 2026-01-26 20:40:34.791948

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d47d1a7fd1b'
down_revision: Union[str, Sequence[str], None] = 'a93a1d19006b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add signature, documentation, and compliance tracking fields to deals table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'deals' in existing_tables:
        cols = [c["name"] for c in inspector.get_columns("deals")]
        
        # Add signature tracking columns
        if 'required_signatures' not in cols:
            from sqlalchemy.dialects.postgresql import JSONB
            op.add_column('deals', sa.Column('required_signatures', JSONB(), nullable=True))
        
        if 'completed_signatures' not in cols:
            from sqlalchemy.dialects.postgresql import JSONB
            op.add_column('deals', sa.Column('completed_signatures', JSONB(), nullable=True))
        
        if 'signature_status' not in cols:
            op.add_column('deals', sa.Column('signature_status', sa.String(length=50), nullable=True))
            op.create_index('ix_deals_signature_status', 'deals', ['signature_status'])
        
        if 'signature_progress' not in cols:
            op.add_column('deals', sa.Column('signature_progress', sa.Integer(), nullable=False, server_default='0'))
        
        if 'signature_deadline' not in cols:
            op.add_column('deals', sa.Column('signature_deadline', sa.DateTime(), nullable=True))
            op.create_index('ix_deals_signature_deadline', 'deals', ['signature_deadline'])
        
        # Add documentation tracking columns
        if 'required_documents' not in cols:
            from sqlalchemy.dialects.postgresql import JSONB
            op.add_column('deals', sa.Column('required_documents', JSONB(), nullable=True))
        
        if 'completed_documents' not in cols:
            from sqlalchemy.dialects.postgresql import JSONB
            op.add_column('deals', sa.Column('completed_documents', JSONB(), nullable=True))
        
        if 'documentation_status' not in cols:
            op.add_column('deals', sa.Column('documentation_status', sa.String(length=50), nullable=True))
            op.create_index('ix_deals_documentation_status', 'deals', ['documentation_status'])
        
        if 'documentation_progress' not in cols:
            op.add_column('deals', sa.Column('documentation_progress', sa.Integer(), nullable=False, server_default='0'))
        
        if 'documentation_deadline' not in cols:
            op.add_column('deals', sa.Column('documentation_deadline', sa.DateTime(), nullable=True))
            op.create_index('ix_deals_documentation_deadline', 'deals', ['documentation_deadline'])
        
        # Add compliance tracking columns
        if 'compliance_status' not in cols:
            op.add_column('deals', sa.Column('compliance_status', sa.String(length=50), nullable=True))
            op.create_index('ix_deals_compliance_status', 'deals', ['compliance_status'])
        
        if 'compliance_notes' not in cols:
            op.add_column('deals', sa.Column('compliance_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove signature, documentation, and compliance tracking fields from deals table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'deals' in existing_tables:
        cols = [c["name"] for c in inspector.get_columns("deals")]
        
        # Remove compliance tracking columns
        if 'compliance_notes' in cols:
            try:
                op.drop_column('deals', 'compliance_notes')
            except Exception:
                pass
        
        if 'compliance_status' in cols:
            try:
                op.drop_index('ix_deals_compliance_status', table_name='deals')
                op.drop_column('deals', 'compliance_status')
            except Exception:
                pass
        
        # Remove documentation tracking columns
        if 'documentation_deadline' in cols:
            try:
                op.drop_index('ix_deals_documentation_deadline', table_name='deals')
                op.drop_column('deals', 'documentation_deadline')
            except Exception:
                pass
        
        if 'documentation_progress' in cols:
            try:
                op.drop_column('deals', 'documentation_progress')
            except Exception:
                pass
        
        if 'documentation_status' in cols:
            try:
                op.drop_index('ix_deals_documentation_status', table_name='deals')
                op.drop_column('deals', 'documentation_status')
            except Exception:
                pass
        
        if 'completed_documents' in cols:
            try:
                op.drop_column('deals', 'completed_documents')
            except Exception:
                pass
        
        if 'required_documents' in cols:
            try:
                op.drop_column('deals', 'required_documents')
            except Exception:
                pass
        
        # Remove signature tracking columns
        if 'signature_deadline' in cols:
            try:
                op.drop_index('ix_deals_signature_deadline', table_name='deals')
                op.drop_column('deals', 'signature_deadline')
            except Exception:
                pass
        
        if 'signature_progress' in cols:
            try:
                op.drop_column('deals', 'signature_progress')
            except Exception:
                pass
        
        if 'signature_status' in cols:
            try:
                op.drop_index('ix_deals_signature_status', table_name='deals')
                op.drop_column('deals', 'signature_status')
            except Exception:
                pass
        
        if 'completed_signatures' in cols:
            try:
                op.drop_column('deals', 'completed_signatures')
            except Exception:
                pass
        
        if 'required_signatures' in cols:
            try:
                op.drop_column('deals', 'required_signatures')
            except Exception:
                pass
