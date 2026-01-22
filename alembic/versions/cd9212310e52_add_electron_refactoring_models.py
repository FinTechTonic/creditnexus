"""add_electron_refactoring_models

Revision ID: cd9212310e52
Revises: e7307c446383
Create Date: 2026-01-17 15:17:21.826489

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'cd9212310e52'
down_revision: Union[str, Sequence[str], None] = 'e7307c446383'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Electron refactoring models: verified implementations, subscriptions, commissions, and user updates."""
    
    # ========================================================================
    # Add columns to users table
    # ========================================================================
    op.add_column('users', sa.Column('organization_identifier', sa.Text(), nullable=True))
    op.create_index('ix_users_organization_identifier', 'users', ['organization_identifier'])
    op.add_column('users', sa.Column('subscription_tier', sa.String(length=20), nullable=False, server_default='free'))
    
    # ========================================================================
    # Create verified_implementations table
    # ========================================================================
    op.create_table(
        'verified_implementations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=True),
        sa.Column('api_secret_encrypted', sa.Text(), nullable=True),
        sa.Column('base_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('configuration', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # ========================================================================
    # Create user_implementation_connections table
    # ========================================================================
    op.create_table(
        'user_implementation_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('implementation_id', sa.Integer(), nullable=False),
        sa.Column('connection_data', JSONB(), nullable=True),  # EncryptedJSON stored as JSONB
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_implementation_connections_user_id'),
        sa.ForeignKeyConstraint(['implementation_id'], ['verified_implementations.id'], name='fk_user_implementation_connections_implementation_id')
    )
    op.create_index('ix_user_implementation_connections_user_id', 'user_implementation_connections', ['user_id'])
    
    # ========================================================================
    # Create user_subscriptions table
    # ========================================================================
    op.create_table(
        'user_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tier', sa.String(length=20), nullable=False),
        sa.Column('subscription_type', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('auto_renew', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_subscriptions_user_id'),
        sa.ForeignKeyConstraint(['payment_id'], ['payment_events.id'], name='fk_user_subscriptions_payment_id')
    )
    op.create_index('ix_user_subscriptions_user_id', 'user_subscriptions', ['user_id'])
    
    # ========================================================================
    # Create subscription_usage table
    # ========================================================================
    op.create_table(
        'subscription_usage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('feature', sa.String(length=50), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('billing_period_start', sa.DateTime(), nullable=False),
        sa.Column('billing_period_end', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_subscription_usage_user_id'),
        sa.ForeignKeyConstraint(['subscription_id'], ['user_subscriptions.id'], name='fk_subscription_usage_subscription_id')
    )
    op.create_index('ix_subscription_usage_user_id', 'subscription_usage', ['user_id'])
    
    # ========================================================================
    # Create commission_configs table
    # ========================================================================
    op.create_table(
        'commission_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('fee_type', sa.String(length=20), nullable=False),
        sa.Column('fee_value', sa.Numeric(10, 4), nullable=False),
        sa.Column('min_fee', sa.Numeric(19, 4), nullable=True),
        sa.Column('max_fee', sa.Numeric(19, 4), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('applies_to', JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ========================================================================
    # Create commission_charges table
    # ========================================================================
    op.create_table(
        'commission_charges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.String(length=255), nullable=False),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(19, 4), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('payer_id', sa.Integer(), nullable=True),
        sa.Column('calculation_details', JSONB(), nullable=True),
        sa.Column('payment_event_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['config_id'], ['commission_configs.id'], name='fk_commission_charges_config_id'),
        sa.ForeignKeyConstraint(['payer_id'], ['users.id'], name='fk_commission_charges_payer_id'),
        sa.ForeignKeyConstraint(['payment_event_id'], ['payment_events.id'], name='fk_commission_charges_payment_event_id')
    )
    op.create_index('ix_commission_charges_transaction_id', 'commission_charges', ['transaction_id'])


def downgrade() -> None:
    """Revert Electron refactoring models."""
    
    # Drop tables in reverse order
    op.drop_index('ix_commission_charges_transaction_id', table_name='commission_charges')
    op.drop_table('commission_charges')
    op.drop_table('commission_configs')
    op.drop_index('ix_subscription_usage_user_id', table_name='subscription_usage')
    op.drop_table('subscription_usage')
    op.drop_index('ix_user_subscriptions_user_id', table_name='user_subscriptions')
    op.drop_table('user_subscriptions')
    op.drop_index('ix_user_implementation_connections_user_id', table_name='user_implementation_connections')
    op.drop_table('user_implementation_connections')
    op.drop_table('verified_implementations')
    
    # Remove columns from users table
    op.drop_index('ix_users_organization_identifier', table_name='users')
    op.drop_column('users', 'organization_identifier')
    op.drop_column('users', 'subscription_tier')
