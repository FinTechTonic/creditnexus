"""add_green_finance_assessment_model

Revision ID: e81cf5457d2d
Revises: 47f244ce55e2
Create Date: 2026-01-11 23:48:51.426795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'e81cf5457d2d'
down_revision: Union[str, Sequence[str], None] = '47f244ce55e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add green finance fields to loan_assets table
    op.add_column('loan_assets', sa.Column('location_type', sa.String(length=50), nullable=True))
    op.add_column('loan_assets', sa.Column('air_quality_index', sa.Float(), nullable=True))
    op.add_column('loan_assets', sa.Column('composite_sustainability_score', sa.Float(), nullable=True))
    op.add_column('loan_assets', sa.Column('green_finance_metrics', JSONB(), nullable=True))
    
    # Create green_finance_assessments table
    op.create_table(
        'green_finance_assessments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.String(length=255), nullable=False),
        sa.Column('deal_id', sa.Integer(), nullable=True),
        sa.Column('loan_asset_id', sa.Integer(), nullable=True),
        sa.Column('location_lat', sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column('location_lon', sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column('location_type', sa.String(length=50), nullable=True),
        sa.Column('location_confidence', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('environmental_metrics', JSONB(), nullable=True),
        sa.Column('urban_activity_metrics', JSONB(), nullable=True),
        sa.Column('sustainability_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('sustainability_components', JSONB(), nullable=True),
        sa.Column('sdg_alignment', JSONB(), nullable=True),
        sa.Column('policy_decisions', JSONB(), nullable=True),
        sa.Column('cdm_events', JSONB(), nullable=True),
        sa.Column('assessed_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ),
        sa.ForeignKeyConstraint(['loan_asset_id'], ['loan_assets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_green_finance_assessments_deal_id'), 'green_finance_assessments', ['deal_id'], unique=False)
    op.create_index(op.f('ix_green_finance_assessments_loan_asset_id'), 'green_finance_assessments', ['loan_asset_id'], unique=False)
    op.create_index(op.f('ix_green_finance_assessments_transaction_id'), 'green_finance_assessments', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_green_finance_assessments_assessed_at'), 'green_finance_assessments', ['assessed_at'], unique=False)


def downgrade() -> None:
    # Drop green_finance_assessments table
    op.drop_index(op.f('ix_green_finance_assessments_assessed_at'), table_name='green_finance_assessments')
    op.drop_index(op.f('ix_green_finance_assessments_transaction_id'), table_name='green_finance_assessments')
    op.drop_index(op.f('ix_green_finance_assessments_loan_asset_id'), table_name='green_finance_assessments')
    op.drop_index(op.f('ix_green_finance_assessments_deal_id'), table_name='green_finance_assessments')
    op.drop_table('green_finance_assessments')
    
    # Remove green finance fields from loan_assets table
    op.drop_column('loan_assets', 'green_finance_metrics')
    op.drop_column('loan_assets', 'composite_sustainability_score')
    op.drop_column('loan_assets', 'air_quality_index')
    op.drop_column('loan_assets', 'location_type')
