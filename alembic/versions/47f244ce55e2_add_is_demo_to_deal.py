"""add_is_demo_to_deal

Revision ID: 47f244ce55e2
Revises: 1e2d90fbb7c1
Create Date: 2026-01-11 22:12:56.092703

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = '47f244ce55e2'
down_revision: Union[str, Sequence[str], None] = '1e2d90fbb7c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_demo column to deals table."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = inspector.get_columns('deals')
    column_names = [col['name'] for col in columns]

    if 'is_demo' not in column_names:
        op.add_column('deals', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.text('false')))
        op.create_index(op.f('ix_deals_is_demo'), 'deals', ['is_demo'], unique=False)


def downgrade() -> None:
    """Remove is_demo column from deals table."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = inspector.get_columns('deals')
    column_names = [col['name'] for col in columns]

    if 'is_demo' in column_names:
        op.drop_index(op.f('ix_deals_is_demo'), table_name='deals')
        op.drop_column('deals', 'is_demo')

