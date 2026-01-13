"""add_filing_signature_tables

Revision ID: dce6ef8935d6
Revises: f7363c9b1d79
Create Date: 2026-01-13 11:30:28.119224

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'dce6ef8935d6'
down_revision: Union[str, Sequence[str], None] = 'f7363c9b1d79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create document_signatures and document_filings tables."""
    
    # Create document_signatures table
    op.create_table(
        'document_signatures',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('generated_document_id', sa.Integer(), nullable=True),
        sa.Column('signature_provider', sa.String(length=50), nullable=False, server_default='digisigner'),
        sa.Column('signature_request_id', sa.String(length=255), nullable=False),
        sa.Column('signature_status', sa.String(length=50), nullable=False),
        sa.Column('signers', JSONB(), nullable=False),
        sa.Column('signature_provider_data', JSONB(), nullable=True),
        sa.Column('signed_document_url', sa.Text(), nullable=True),
        sa.Column('signed_document_path', sa.Text(), nullable=True),
        sa.Column('requested_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('signature_request_id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name='fk_document_signatures_document_id'),
        sa.ForeignKeyConstraint(['generated_document_id'], ['generated_documents.id'], name='fk_document_signatures_generated_document_id')
    )
    op.create_index('ix_document_signatures_document_id', 'document_signatures', ['document_id'])
    op.create_index('ix_document_signatures_generated_document_id', 'document_signatures', ['generated_document_id'])
    op.create_index('ix_document_signatures_signature_request_id', 'document_signatures', ['signature_request_id'], unique=True)
    op.create_index('ix_document_signatures_signature_status', 'document_signatures', ['signature_status'])
    
    # Create document_filings table
    op.create_table(
        'document_filings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('generated_document_id', sa.Integer(), nullable=True),
        sa.Column('deal_id', sa.Integer(), nullable=True),
        sa.Column('agreement_type', sa.String(length=100), nullable=False),
        sa.Column('jurisdiction', sa.String(length=50), nullable=False),
        sa.Column('filing_authority', sa.String(length=255), nullable=False),
        sa.Column('filing_system', sa.String(length=50), nullable=False),
        sa.Column('filing_reference', sa.String(length=255), nullable=True),
        sa.Column('filing_status', sa.String(length=50), nullable=False),
        sa.Column('filing_payload', JSONB(), nullable=True),
        sa.Column('filing_response', JSONB(), nullable=True),
        sa.Column('filing_url', sa.Text(), nullable=True),
        sa.Column('confirmation_url', sa.Text(), nullable=True),
        sa.Column('manual_submission_url', sa.Text(), nullable=True),
        sa.Column('submitted_by', sa.Integer(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('submission_notes', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('filed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('filing_reference'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name='fk_document_filings_document_id'),
        sa.ForeignKeyConstraint(['generated_document_id'], ['generated_documents.id'], name='fk_document_filings_generated_document_id'),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], name='fk_document_filings_deal_id'),
        sa.ForeignKeyConstraint(['submitted_by'], ['users.id'], name='fk_document_filings_submitted_by')
    )
    op.create_index('ix_document_filings_document_id', 'document_filings', ['document_id'])
    op.create_index('ix_document_filings_generated_document_id', 'document_filings', ['generated_document_id'])
    op.create_index('ix_document_filings_deal_id', 'document_filings', ['deal_id'])
    op.create_index('ix_document_filings_agreement_type', 'document_filings', ['agreement_type'])
    op.create_index('ix_document_filings_jurisdiction', 'document_filings', ['jurisdiction'])
    op.create_index('ix_document_filings_filing_status', 'document_filings', ['filing_status'])
    op.create_index('ix_document_filings_deadline', 'document_filings', ['deadline'])
    op.create_index('ix_document_filings_filing_reference', 'document_filings', ['filing_reference'], unique=True)


def downgrade() -> None:
    """Drop document_signatures and document_filings tables."""
    op.drop_index('ix_document_filings_filing_reference', table_name='document_filings')
    op.drop_index('ix_document_filings_deadline', table_name='document_filings')
    op.drop_index('ix_document_filings_filing_status', table_name='document_filings')
    op.drop_index('ix_document_filings_jurisdiction', table_name='document_filings')
    op.drop_index('ix_document_filings_agreement_type', table_name='document_filings')
    op.drop_index('ix_document_filings_deal_id', table_name='document_filings')
    op.drop_index('ix_document_filings_generated_document_id', table_name='document_filings')
    op.drop_index('ix_document_filings_document_id', table_name='document_filings')
    op.drop_table('document_filings')
    
    op.drop_index('ix_document_signatures_signature_status', table_name='document_signatures')
    op.drop_index('ix_document_signatures_signature_request_id', table_name='document_signatures')
    op.drop_index('ix_document_signatures_generated_document_id', table_name='document_signatures')
    op.drop_index('ix_document_signatures_document_id', table_name='document_signatures')
    op.drop_table('document_signatures')
