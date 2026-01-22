"""add_trade_executions_table

Revision ID: c5bcf6b2ff35
Revises: g2024dc_dc1
Create Date: 2026-01-22 20:40:05.281897

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'c5bcf6b2ff35'
down_revision: Union[str, Sequence[str], None] = 'g2024dc_dc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create trade_executions table for LMA trade storage and settlement lookup."""
    # Check if table already exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'trade_executions' not in existing_tables:
        op.create_table(
            'trade_executions',
            sa.Column('id', sa.Integer(), nullable=False),
            
            # Trade identification
            sa.Column('trade_id', sa.String(length=255), nullable=False, unique=True),
            
            # User and deal information
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('credit_agreement_id', sa.Integer(), nullable=True),
            sa.Column('facility_id', sa.String(length=255), nullable=True),
            
            # Trade details
            sa.Column('trade_price', sa.Numeric(precision=20, scale=8), nullable=True),
            sa.Column('trade_amount', sa.Numeric(precision=20, scale=2), nullable=True),
            sa.Column('settlement_date', sa.Date(), nullable=True),
            
            # Status tracking
            sa.Column('status', sa.String(length=50), nullable=False, server_default='executed'),
            
            # CDM event storage
            sa.Column('cdm_event', JSONB(), nullable=False),
            sa.Column('policy_decision', JSONB(), nullable=True),
            
            # Timestamps
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('settled_at', sa.DateTime(), nullable=True),
            
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_trade_executions_user'),
            sa.ForeignKeyConstraint(['credit_agreement_id'], ['deals.id'], name='fk_trade_executions_credit_agreement'),
        )
        
        # Create indexes for fast queries
        op.create_index('ix_trade_executions_trade_id', 'trade_executions', ['trade_id'], unique=True)
        op.create_index('ix_trade_executions_user_id', 'trade_executions', ['user_id'])
        op.create_index('ix_trade_executions_status', 'trade_executions', ['status'])
        op.create_index('ix_trade_executions_credit_agreement_id', 'trade_executions', ['credit_agreement_id'])
        op.create_index('ix_trade_executions_facility_id', 'trade_executions', ['facility_id'])
        op.create_index('ix_trade_executions_created_at', 'trade_executions', ['created_at'])


def downgrade() -> None:
    """Drop trade_executions table and indexes."""
    op.drop_index('ix_trade_executions_created_at', table_name='trade_executions')
    op.drop_index('ix_trade_executions_facility_id', table_name='trade_executions')
    op.drop_index('ix_trade_executions_credit_agreement_id', table_name='trade_executions')
    op.drop_index('ix_trade_executions_status', table_name='trade_executions')
    op.drop_index('ix_trade_executions_user_id', table_name='trade_executions')
    op.drop_index('ix_trade_executions_trade_id', table_name='trade_executions')
    op.drop_table('trade_executions')
