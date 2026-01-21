"""add_orders_table

Revision ID: 8c92e21f2aa9
Revises: c80aa4258269
Create Date: 2026-01-20 18:45:53.239211

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '8c92e21f2aa9'
down_revision: Union[str, Sequence[str], None] = 'c80aa4258269'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create orders table for trading order management."""
    # Check if table already exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'orders' not in existing_tables:
        op.create_table(
            'orders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('order_id', sa.String(length=255), nullable=False, unique=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('symbol', sa.String(length=50), nullable=False),
            sa.Column('side', sa.String(length=10), nullable=False),
            sa.Column('order_type', sa.String(length=20), nullable=False),
            sa.Column('quantity', sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column('price', sa.Numeric(precision=20, scale=8), nullable=True),
            sa.Column('stop_price', sa.Numeric(precision=20, scale=8), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
            sa.Column('filled_quantity', sa.Numeric(precision=20, scale=8), nullable=False, server_default='0'),
            sa.Column('average_fill_price', sa.Numeric(precision=20, scale=8), nullable=True),
            sa.Column('commission', sa.Numeric(precision=20, scale=2), nullable=True),
            sa.Column('commission_currency', sa.String(length=3), nullable=False, server_default='USD'),
            sa.Column('trading_api', sa.String(length=50), nullable=True),
            sa.Column('trading_api_order_id', sa.String(length=255), nullable=True),
            sa.Column('trading_api_response', JSONB(), nullable=True),
            sa.Column('time_in_force', sa.String(length=20), nullable=False, server_default='day'),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('submitted_at', sa.DateTime(), nullable=True),
            sa.Column('filled_at', sa.DateTime(), nullable=True),
            sa.Column('cancelled_at', sa.DateTime(), nullable=True),
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.Column('order_metadata', JSONB(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_orders_user'),
        )
        
        # Create indexes
        op.create_index('ix_orders_order_id', 'orders', ['order_id'], unique=True)
        op.create_index('ix_orders_user_id', 'orders', ['user_id'])
        op.create_index('ix_orders_symbol', 'orders', ['symbol'])
        op.create_index('ix_orders_side', 'orders', ['side'])
        op.create_index('ix_orders_order_type', 'orders', ['order_type'])
        op.create_index('ix_orders_status', 'orders', ['status'])
        op.create_index('ix_orders_trading_api', 'orders', ['trading_api'])
        op.create_index('ix_orders_trading_api_order_id', 'orders', ['trading_api_order_id'])


def downgrade() -> None:
    """Drop orders table."""
    op.drop_index('ix_orders_trading_api_order_id', table_name='orders')
    op.drop_index('ix_orders_trading_api', table_name='orders')
    op.drop_index('ix_orders_status', table_name='orders')
    op.drop_index('ix_orders_order_type', table_name='orders')
    op.drop_index('ix_orders_side', table_name='orders')
    op.drop_index('ix_orders_symbol', table_name='orders')
    op.drop_index('ix_orders_user_id', table_name='orders')
    op.drop_index('ix_orders_order_id', table_name='orders')
    op.drop_table('orders')
