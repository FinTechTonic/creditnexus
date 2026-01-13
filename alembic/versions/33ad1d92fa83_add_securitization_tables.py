"""add_securitization_tables

Revision ID: 33ad1d92fa83
Revises: c2e1aab585f1
Create Date: 2026-01-13 13:06:29.216863

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '33ad1d92fa83'
down_revision: Union[str, Sequence[str], None] = 'c2e1aab585f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create securitization tables."""
    # Check if tables already exist (for cases where they were created manually)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Securitization Pool
    if 'securitization_pools' not in existing_tables:
        op.create_table(
            'securitization_pools',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('pool_id', sa.String(length=255), nullable=False, unique=True),
            sa.Column('pool_name', sa.String(length=255), nullable=False),
            sa.Column('pool_type', sa.String(length=50), nullable=False),  # 'ABS', 'CLO', 'MBS', etc.
            sa.Column('originator_id', sa.Integer(), nullable=True),
            sa.Column('trustee_id', sa.Integer(), nullable=True),
            sa.Column('total_pool_value', sa.Numeric(precision=20, scale=2), nullable=False),
            sa.Column('currency', sa.String(length=3), nullable=False),
            sa.Column('cdm_payload', JSONB(), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False),  # 'draft', 'pending_notarization', 'notarized', 'filed', 'active'
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('notarized_at', sa.DateTime(), nullable=True),
            sa.Column('filed_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['originator_id'], ['users.id'], name='fk_securitization_pool_originator'),
            sa.ForeignKeyConstraint(['trustee_id'], ['users.id'], name='fk_securitization_pool_trustee'),
        )
        op.create_index('idx_securitization_pools_pool_id', 'securitization_pools', ['pool_id'], unique=True)
        op.create_index('idx_securitization_pools_status', 'securitization_pools', ['status'])
    else:
        # Table exists, but ensure indexes exist (use raw SQL to avoid transaction issues)
        conn = op.get_bind()
        # Check if pool_id column exists before creating index
        result = conn.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'securitization_pools' 
            AND column_name = 'pool_id'
        """))
        if result.fetchone() is not None:
            result = conn.execute(sa.text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'securitization_pools' 
                AND indexname = 'idx_securitization_pools_pool_id'
            """))
            if result.fetchone() is None:
                op.create_index('idx_securitization_pools_pool_id', 'securitization_pools', ['pool_id'], unique=True)
        
        # Check if status column exists before creating index
        result = conn.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'securitization_pools' 
            AND column_name = 'status'
        """))
        if result.fetchone() is not None:
            result = conn.execute(sa.text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'securitization_pools' 
                AND indexname = 'idx_securitization_pools_status'
            """))
            if result.fetchone() is None:
                op.create_index('idx_securitization_pools_status', 'securitization_pools', ['status'])
    
    # Securitization Tranche
    if 'securitization_tranches' not in existing_tables:
        op.create_table(
            'securitization_tranches',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('pool_id', sa.Integer(), nullable=False),
            sa.Column('tranche_name', sa.String(length=255), nullable=False),
            sa.Column('tranche_class', sa.String(length=50), nullable=False),  # 'Senior', 'Mezzanine', 'Equity'
            sa.Column('tranche_size', sa.Numeric(precision=20, scale=2), nullable=False),
            sa.Column('interest_rate', sa.Numeric(precision=10, scale=4), nullable=False),
            sa.Column('risk_rating', sa.String(length=10), nullable=True),  # 'AAA', 'AA', 'A', 'BBB', etc.
            sa.Column('payment_priority', sa.Integer(), nullable=False),  # Lower = higher priority
            sa.Column('cdm_tranche_data', JSONB(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['pool_id'], ['securitization_pools.id'], name='fk_securitization_tranche_pool', ondelete='CASCADE'),
        )
        op.create_index('idx_securitization_tranches_pool_id', 'securitization_tranches', ['pool_id'])
    else:
        # Table exists, but ensure indexes exist (use raw SQL to avoid transaction issues)
        conn = op.get_bind()
        # Check if pool_id column exists before creating index
        result = conn.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'securitization_tranches' 
            AND column_name = 'pool_id'
        """))
        if result.fetchone() is not None:
            result = conn.execute(sa.text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'securitization_tranches' 
                AND indexname = 'idx_securitization_tranches_pool_id'
            """))
            if result.fetchone() is None:
                op.create_index('idx_securitization_tranches_pool_id', 'securitization_tranches', ['pool_id'])
    
    # Pool Asset (Many-to-Many: Pools <-> Deals/Loans)
    if 'securitization_pool_assets' not in existing_tables:
        op.create_table(
            'securitization_pool_assets',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('pool_id', sa.Integer(), nullable=False),
            sa.Column('deal_id', sa.Integer(), nullable=True),
            sa.Column('loan_asset_id', sa.Integer(), nullable=True),
            sa.Column('asset_type', sa.String(length=50), nullable=False),  # 'deal', 'loan_asset'
            sa.Column('allocation_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column('allocation_amount', sa.Numeric(precision=20, scale=2), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['pool_id'], ['securitization_pools.id'], name='fk_securitization_pool_asset_pool', ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], name='fk_securitization_pool_asset_deal'),
            sa.ForeignKeyConstraint(['loan_asset_id'], ['loan_assets.id'], name='fk_securitization_pool_asset_loan'),
            sa.UniqueConstraint('pool_id', 'deal_id', 'loan_asset_id', name='uq_securitization_pool_assets'),
        )
        op.create_index('idx_securitization_pool_assets_pool_id', 'securitization_pool_assets', ['pool_id'])
        op.create_index('idx_securitization_pool_assets_deal_id', 'securitization_pool_assets', ['deal_id'])
        op.create_index('idx_securitization_pool_assets_loan_asset_id', 'securitization_pool_assets', ['loan_asset_id'])
    else:
        # Table exists, but ensure indexes exist (use raw SQL to avoid transaction issues)
        conn = op.get_bind()
        # Check if pool_id column exists before creating index
        result = conn.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'securitization_pool_assets' 
            AND column_name = 'pool_id'
        """))
        if result.fetchone() is not None:
            result = conn.execute(sa.text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'securitization_pool_assets' 
                AND indexname = 'idx_securitization_pool_assets_pool_id'
            """))
            if result.fetchone() is None:
                op.create_index('idx_securitization_pool_assets_pool_id', 'securitization_pool_assets', ['pool_id'])
        
        # Check if deal_id column exists before creating index
        result = conn.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'securitization_pool_assets' 
            AND column_name = 'deal_id'
        """))
        if result.fetchone() is not None:
            result = conn.execute(sa.text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'securitization_pool_assets' 
                AND indexname = 'idx_securitization_pool_assets_deal_id'
            """))
            if result.fetchone() is None:
                op.create_index('idx_securitization_pool_assets_deal_id', 'securitization_pool_assets', ['deal_id'])
        
        # Check if loan_asset_id column exists before creating index
        result = conn.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'securitization_pool_assets' 
            AND column_name = 'loan_asset_id'
        """))
        if result.fetchone() is not None:
            result = conn.execute(sa.text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'securitization_pool_assets' 
                AND indexname = 'idx_securitization_pool_assets_loan_asset_id'
            """))
            if result.fetchone() is None:
                op.create_index('idx_securitization_pool_assets_loan_asset_id', 'securitization_pool_assets', ['loan_asset_id'])
    
    # Regulatory Filing
    if 'regulatory_filings' not in existing_tables:
        op.create_table(
            'regulatory_filings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('pool_id', sa.Integer(), nullable=False),
            sa.Column('filing_type', sa.String(length=50), nullable=False),  # 'SEC_10D', 'PROSPECTUS', 'PSA', 'TRUST_AGREEMENT'
            sa.Column('filing_body', sa.String(length=100), nullable=False),  # 'SEC', 'FINRA', etc.
            sa.Column('filing_number', sa.String(length=255), nullable=True),
            sa.Column('filing_status', sa.String(length=50), nullable=False),  # 'pending', 'submitted', 'accepted', 'rejected'
            sa.Column('document_path', sa.String(length=500), nullable=True),
            sa.Column('submitted_at', sa.DateTime(), nullable=True),
            sa.Column('accepted_at', sa.DateTime(), nullable=True),
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['pool_id'], ['securitization_pools.id'], name='fk_regulatory_filing_pool', ondelete='CASCADE'),
        )
        op.create_index('idx_regulatory_filings_pool_id', 'regulatory_filings', ['pool_id'])
        op.create_index('idx_regulatory_filings_status', 'regulatory_filings', ['filing_status'])
    else:
        # Table exists, but ensure indexes exist (use raw SQL to avoid transaction issues)
        conn = op.get_bind()
        # Check if pool_id column exists before creating index
        result = conn.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'regulatory_filings' 
            AND column_name = 'pool_id'
        """))
        if result.fetchone() is not None:
            result = conn.execute(sa.text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'regulatory_filings' 
                AND indexname = 'idx_regulatory_filings_pool_id'
            """))
            if result.fetchone() is None:
                op.create_index('idx_regulatory_filings_pool_id', 'regulatory_filings', ['pool_id'])
        
        # Check if filing_status column exists before creating index
        result = conn.execute(sa.text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'regulatory_filings' 
            AND column_name = 'filing_status'
        """))
        if result.fetchone() is not None:
            result = conn.execute(sa.text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'regulatory_filings' 
                AND indexname = 'idx_regulatory_filings_status'
            """))
            if result.fetchone() is None:
                op.create_index('idx_regulatory_filings_status', 'regulatory_filings', ['filing_status'])
    
    # Add securitization_pool_id to notarization_records (if column doesn't exist)
    # Only proceed if securitization_pools table exists
    if 'securitization_pools' in existing_tables and 'notarization_records' in existing_tables:
        # Use raw SQL to check for column existence (avoids transaction issues)
        conn = op.get_bind()
        result = conn.execute(sa.text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'notarization_records' 
            AND column_name = 'securitization_pool_id'
        """))
        column_exists = result.fetchone() is not None
        
        if not column_exists:
            op.add_column('notarization_records', sa.Column('securitization_pool_id', sa.Integer(), nullable=True))
        
        # Check for foreign key existence using raw SQL
        result = conn.execute(sa.text("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'notarization_records' 
            AND constraint_name = 'fk_notarization_securitization_pool'
            AND constraint_type = 'FOREIGN KEY'
        """))
        fk_exists = result.fetchone() is not None
        
        if not fk_exists:
            op.create_foreign_key('fk_notarization_securitization_pool', 'notarization_records', 'securitization_pools', ['securitization_pool_id'], ['id'])
        
        # Check for index existence using raw SQL
        result = conn.execute(sa.text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'notarization_records' 
            AND indexname = 'idx_notarization_records_securitization_pool_id'
        """))
        index_exists = result.fetchone() is not None
        
        if not index_exists:
            op.create_index('idx_notarization_records_securitization_pool_id', 'notarization_records', ['securitization_pool_id'])


def downgrade() -> None:
    """Drop securitization tables."""
    op.drop_index('idx_notarization_records_securitization_pool_id', table_name='notarization_records')
    op.drop_constraint('fk_notarization_securitization_pool', 'notarization_records', type_='foreignkey')
    op.drop_column('notarization_records', 'securitization_pool_id')
    
    op.drop_index('idx_regulatory_filings_status', table_name='regulatory_filings')
    op.drop_index('idx_regulatory_filings_pool_id', table_name='regulatory_filings')
    op.drop_table('regulatory_filings')
    
    op.drop_index('idx_securitization_pool_assets_loan_asset_id', table_name='securitization_pool_assets')
    op.drop_index('idx_securitization_pool_assets_deal_id', table_name='securitization_pool_assets')
    op.drop_index('idx_securitization_pool_assets_pool_id', table_name='securitization_pool_assets')
    op.drop_table('securitization_pool_assets')
    
    op.drop_index('idx_securitization_tranches_pool_id', table_name='securitization_tranches')
    op.drop_table('securitization_tranches')
    
    op.drop_index('idx_securitization_pools_status', table_name='securitization_pools')
    op.drop_index('idx_securitization_pools_pool_id', table_name='securitization_pools')
    op.drop_table('securitization_pools')
