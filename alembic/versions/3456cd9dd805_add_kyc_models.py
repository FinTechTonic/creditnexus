"""add kyc models

Revision ID: 3456cd9dd805
Revises: 2345bc8cc704
Create Date: 2026-01-28 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3456cd9dd805'
down_revision: Union[str, Sequence[str], None] = '2345bc8cc704'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add KYC verification, user licenses, and KYC documents tables."""
    # Create kyc_verifications table
    op.create_table('kyc_verifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('kyc_status', sa.String(length=50), nullable=False),
        sa.Column('kyc_level', sa.String(length=50), nullable=False),
        sa.Column('identity_verified', sa.Boolean(), nullable=False),
        sa.Column('address_verified', sa.Boolean(), nullable=False),
        sa.Column('document_verified', sa.Boolean(), nullable=False),
        sa.Column('license_verified', sa.Boolean(), nullable=False),
        sa.Column('sanctions_check_passed', sa.Boolean(), nullable=False),
        sa.Column('pep_check_passed', sa.Boolean(), nullable=False),
        sa.Column('verification_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('policy_evaluation_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('peoplehub_profile_id', sa.String(length=255), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_kyc_verifications_kyc_status'), 'kyc_verifications', ['kyc_status'], unique=False)

    # Create kyc_documents table
    op.create_table('kyc_documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('kyc_verification_id', sa.Integer(), nullable=True),
        sa.Column('document_type', sa.String(length=100), nullable=False),
        sa.Column('document_category', sa.String(length=100), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('verification_status', sa.String(length=50), nullable=False),
        sa.Column('extracted_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['kyc_verification_id'], ['kyc_verifications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kyc_documents_kyc_verification_id'), 'kyc_documents', ['kyc_verification_id'], unique=False)
    op.create_index(op.f('ix_kyc_documents_user_id'), 'kyc_documents', ['user_id'], unique=False)

    # Create user_licenses table
    op.create_table('user_licenses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('kyc_verification_id', sa.Integer(), nullable=True),
        sa.Column('license_type', sa.String(length=100), nullable=False),
        sa.Column('license_number', sa.String(length=255), nullable=False),
        sa.Column('license_category', sa.String(length=50), nullable=False),
        sa.Column('issuing_authority', sa.String(length=255), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=True),
        sa.Column('expiration_date', sa.Date(), nullable=True),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('verification_status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['kyc_verification_id'], ['kyc_verifications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_licenses_kyc_verification_id'), 'user_licenses', ['kyc_verification_id'], unique=False)
    op.create_index(op.f('ix_user_licenses_user_id'), 'user_licenses', ['user_id'], unique=False)


def downgrade() -> None:
    """Remove KYC verification, user licenses, and KYC documents tables."""
    op.drop_index(op.f('ix_user_licenses_user_id'), table_name='user_licenses')
    op.drop_index(op.f('ix_user_licenses_kyc_verification_id'), table_name='user_licenses')
    op.drop_table('user_licenses')
    op.drop_index(op.f('ix_kyc_documents_user_id'), table_name='kyc_documents')
    op.drop_index(op.f('ix_kyc_documents_kyc_verification_id'), table_name='kyc_documents')
    op.drop_table('kyc_documents')
    op.drop_index(op.f('ix_kyc_verifications_kyc_status'), table_name='kyc_verifications')
    op.drop_table('kyc_verifications')
