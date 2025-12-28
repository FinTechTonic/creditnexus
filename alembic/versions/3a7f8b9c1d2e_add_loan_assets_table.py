"""Add loan_assets table for Ground Truth Protocol.

Revision ID: 3a7f8b9c1d2e
Revises: 98d797286ba1
Create Date: 2024-12-28 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '3a7f8b9c1d2e'
down_revision = '98d797286ba1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension if available (optional)
    # Uncomment if you have pgvector installed:
    # op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    op.create_table(
        'loan_assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('loan_id', sa.String(length=255), nullable=False),
        
        # Legal Reality
        sa.Column('original_text', sa.Text(), nullable=True),
        sa.Column('legal_vector', JSONB(), nullable=True),
        
        # Physical Reality
        sa.Column('geo_lat', sa.Float(), nullable=True),
        sa.Column('geo_lon', sa.Float(), nullable=True),
        sa.Column('collateral_address', sa.String(length=500), nullable=True),
        sa.Column('satellite_snapshot_url', sa.String(length=1000), nullable=True),
        sa.Column('geo_vector', JSONB(), nullable=True),
        
        # SPT Data
        sa.Column('spt_data', JSONB(), nullable=True),
        
        # Verification State
        sa.Column('last_verified_score', sa.Float(), nullable=True),
        sa.Column('spt_threshold', sa.Float(), server_default='0.8', nullable=True),
        sa.Column('risk_status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('base_interest_rate', sa.Float(), server_default='5.0', nullable=True),
        sa.Column('current_interest_rate', sa.Float(), server_default='5.0', nullable=True),
        sa.Column('penalty_bps', sa.Float(), server_default='50.0', nullable=True),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_verified_at', sa.DateTime(), nullable=True),
        sa.Column('verification_error', sa.Text(), nullable=True),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on loan_id for fast lookups
    op.create_index('ix_loan_assets_loan_id', 'loan_assets', ['loan_id'], unique=False)
    
    # Create index on risk_status for filtering
    op.create_index('ix_loan_assets_risk_status', 'loan_assets', ['risk_status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_loan_assets_risk_status', table_name='loan_assets')
    op.drop_index('ix_loan_assets_loan_id', table_name='loan_assets')
    op.drop_table('loan_assets')
