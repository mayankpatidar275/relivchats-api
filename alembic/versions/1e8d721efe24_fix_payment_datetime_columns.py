"""fix_payment_datetime_columns

Revision ID: 1e8d721efe24
Revises: 4043a689fed7
Create Date: 2026-01-03 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1e8d721efe24'
down_revision: Union[str, Sequence[str], None] = '4043a689fed7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add timezone=True to datetime columns."""
    # Fix payment_orders columns
    op.alter_column('payment_orders', 'completed_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)

    op.alter_column('payment_orders', 'webhook_received_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)

    # Fix payment_refunds processed_at column
    op.alter_column('payment_refunds', 'processed_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema - remove timezone from datetime columns."""
    # Revert payment_refunds
    op.alter_column('payment_refunds', 'processed_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)

    # Revert payment_orders columns
    op.alter_column('payment_orders', 'webhook_received_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)

    op.alter_column('payment_orders', 'completed_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
