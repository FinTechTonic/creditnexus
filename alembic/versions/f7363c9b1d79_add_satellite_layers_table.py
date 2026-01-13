"""add_satellite_layers_table

Revision ID: f7363c9b1d79
Revises: 3c27a125f86c
Create Date: 2026-01-13 09:43:11.175076

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'f7363c9b1d79'
down_revision: Union[str, Sequence[str], None] = '3c27a125f86c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add satellite_layers table."""
    op.create_table(
        'satellite_layers',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('loan_asset_id', sa.Integer(), nullable=False),
        sa.Column('layer_type', sa.String(length=50), nullable=False),
        sa.Column('band_number', sa.String(length=10), nullable=True),
        sa.Column('file_path', sa.String(length=1000), nullable=False),
        sa.Column('metadata', JSONB(), nullable=True),
        sa.Column('resolution', sa.Integer(), nullable=True),
        sa.Column('bounds_north', sa.Numeric(10, 7), nullable=True),
        sa.Column('bounds_south', sa.Numeric(10, 7), nullable=True),
        sa.Column('bounds_east', sa.Numeric(10, 7), nullable=True),
        sa.Column('bounds_west', sa.Numeric(10, 7), nullable=True),
        sa.Column('crs', sa.String(length=50), server_default='EPSG:4326', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_satellite_layers_loan_asset_id', 'satellite_layers', ['loan_asset_id'])
    op.create_index('ix_satellite_layers_layer_type', 'satellite_layers', ['layer_type'])
    op.create_index('ix_satellite_layers_created_at', 'satellite_layers', ['created_at'])


def downgrade() -> None:
    """Downgrade schema - remove satellite_layers table."""
    op.drop_index('ix_satellite_layers_created_at', table_name='satellite_layers')
    op.drop_index('ix_satellite_layers_layer_type', table_name='satellite_layers')
    op.drop_index('ix_satellite_layers_loan_asset_id', table_name='satellite_layers')
    op.drop_table('satellite_layers')
