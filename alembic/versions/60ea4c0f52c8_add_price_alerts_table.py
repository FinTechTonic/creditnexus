"""add_price_alerts_table

Revision ID: 60ea4c0f52c8
Revises: c5bcf6b2ff35
Create Date: 2026-01-22 20:45:10.247642

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60ea4c0f52c8'
down_revision: Union[str, Sequence[str], None] = 'c5bcf6b2ff35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create price_alerts table for monitoring symbol price movements."""
    # Check if table already exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'price_alerts' not in existing_tables:
        op.create_table(
            'price_alerts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('symbol', sa.String(length=50), nullable=False),
            
            # Alert conditions
            sa.Column('alert_type', sa.String(length=20), nullable=False),
            sa.Column('target_price', sa.Numeric(precision=20, scale=8), nullable=True),
            sa.Column('change_percent', sa.Numeric(precision=5, scale=2), nullable=True),
            
            # Status
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('triggered_at', sa.DateTime(), nullable=True),
            sa.Column('triggered_price', sa.Numeric(precision=20, scale=8), nullable=True),
            
            # Notification settings
            sa.Column('notify_email', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('notify_in_app', sa.Boolean(), nullable=False, server_default='true'),
            
            # Metadata
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_price_alerts_user'),
        )
        
        # Create indexes for fast queries
        op.create_index('ix_price_alerts_user_id', 'price_alerts', ['user_id'])
        op.create_index('ix_price_alerts_symbol', 'price_alerts', ['symbol'])
        op.create_index('ix_price_alerts_alert_type', 'price_alerts', ['alert_type'])
        op.create_index('ix_price_alerts_is_active', 'price_alerts', ['is_active'])
        op.create_index('ix_price_alerts_triggered_at', 'price_alerts', ['triggered_at'])
        op.create_index('ix_price_alerts_created_at', 'price_alerts', ['created_at'])


def downgrade() -> None:
    """Drop price_alerts table and indexes."""
    op.drop_index('ix_price_alerts_created_at', table_name='price_alerts')
    op.drop_index('ix_price_alerts_triggered_at', table_name='price_alerts')
    op.drop_index('ix_price_alerts_is_active', table_name='price_alerts')
    op.drop_index('ix_price_alerts_alert_type', table_name='price_alerts')
    op.drop_index('ix_price_alerts_symbol', table_name='price_alerts')
    op.drop_index('ix_price_alerts_user_id', table_name='price_alerts')
    op.drop_table('price_alerts')
