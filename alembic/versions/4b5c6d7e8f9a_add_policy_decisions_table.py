"""Add policy_decisions table for Policy Engine audit trail.

Revision ID: 4b5c6d7e8f9a
Revises: 3a7f8b9c1d2e
Create Date: 2025-01-05 21:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY


# revision identifiers, used by Alembic.
revision: str = '4b5c6d7e8f9a'
down_revision: Union[str, None] = 'e650a2d25272'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create policy_decisions table with CDM events support."""
    op.create_table(
        'policy_decisions',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Transaction identification
        sa.Column('transaction_id', sa.String(length=255), nullable=False),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        
        # Policy decision
        sa.Column('decision', sa.String(length=10), nullable=False),  # 'ALLOW', 'BLOCK', 'FLAG'
        sa.Column('rule_applied', sa.String(length=255), nullable=True),
        sa.Column('trace_id', sa.String(length=255), nullable=False),
        
        # Evaluation details
        sa.Column('trace', JSONB(), nullable=True),  # Full evaluation trace
        sa.Column('matched_rules', ARRAY(sa.String()), nullable=True),  # Array of matched rule names
        sa.Column('metadata', JSONB(), nullable=True),  # Additional context
        
        # CDM Events (for full CDM compliance)
        sa.Column('cdm_events', JSONB(), nullable=True),  # Full CDM PolicyEvaluation events
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        
        # Foreign keys to CreditNexus entities
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('loan_asset_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name='fk_policy_decisions_document_id'),
        # NOTE: loan_asset_id has NO ForeignKey because loan_assets uses SQLModel (separate table creation)
        # The loan_assets table may not exist when PolicyDecision is created
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_policy_decisions_user_id'),
    )
    
    # Create index for loan_asset_id (without FK constraint)
    op.create_index('idx_policy_decisions_loan_asset_id', 'policy_decisions', ['loan_asset_id'], unique=False)
    
    # Create indexes for fast queries
    op.create_index('idx_policy_decisions_transaction', 'policy_decisions', ['transaction_id'], unique=False)
    op.create_index('idx_policy_decisions_decision', 'policy_decisions', ['decision'], unique=False)
    op.create_index('idx_policy_decisions_created_at', 'policy_decisions', ['created_at'], unique=False)
    op.create_index('idx_policy_decisions_trace_id', 'policy_decisions', ['trace_id'], unique=True)


def downgrade() -> None:
    """Drop policy_decisions table and indexes."""
    op.drop_index('idx_policy_decisions_loan_asset_id', table_name='policy_decisions')
    op.drop_index('idx_policy_decisions_trace_id', table_name='policy_decisions')
    op.drop_index('idx_policy_decisions_created_at', table_name='policy_decisions')
    op.drop_index('idx_policy_decisions_decision', table_name='policy_decisions')
    op.drop_index('idx_policy_decisions_transaction', table_name='policy_decisions')
    op.drop_table('policy_decisions')








