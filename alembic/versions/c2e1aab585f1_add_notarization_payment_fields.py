"""add_notarization_payment_fields

Revision ID: c2e1aab585f1
Revises: dce6ef8935d6
Create Date: 2026-01-13 13:05:36.074153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2e1aab585f1'
down_revision: Union[str, Sequence[str], None] = 'dce6ef8935d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add payment fields to notarization_records
    op.add_column('notarization_records', sa.Column('payment_event_id', sa.Integer(), nullable=True))
    op.add_column('notarization_records', sa.Column('payment_status', sa.String(20), nullable=True))
    op.add_column('notarization_records', sa.Column('payment_transaction_hash', sa.String(255), nullable=True))
    op.create_foreign_key('fk_notarization_payment_event', 'notarization_records', 'payment_events', ['payment_event_id'], ['id'])
    op.create_index('ix_notarization_records_payment_event_id', 'notarization_records', ['payment_event_id'])
    
    # Add notarization link to payment_events
    op.add_column('payment_events', sa.Column('related_notarization_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_payment_notarization', 'payment_events', 'notarization_records', ['related_notarization_id'], ['id'])
    op.create_index('ix_payment_events_related_notarization_id', 'payment_events', ['related_notarization_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_payment_events_related_notarization_id', table_name='payment_events')
    op.drop_constraint('fk_payment_notarization', 'payment_events', type_='foreignkey')
    op.drop_column('payment_events', 'related_notarization_id')
    
    op.drop_index('ix_notarization_records_payment_event_id', table_name='notarization_records')
    op.drop_constraint('fk_notarization_payment_event', 'notarization_records', type_='foreignkey')
    op.drop_column('notarization_records', 'payment_transaction_hash')
    op.drop_column('notarization_records', 'payment_status')
    op.drop_column('notarization_records', 'payment_event_id')
