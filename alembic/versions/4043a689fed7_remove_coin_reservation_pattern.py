"""remove_coin_reservation_pattern

Revision ID: 4043a689fed7
Revises: cfb0149dda68
Create Date: 2025-12-07 16:52:16.576945

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4043a689fed7'
down_revision: Union[str, Sequence[str], None] = 'cfb0149dda68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove coin reservation pattern columns.

    Switch from reserve-then-charge to immediate deduction with refund pattern.
    This simplifies the codebase and aligns with industry standards (OpenAI, Stripe, etc.)
    """
    # Drop reservation columns from chats table
    op.drop_column('chats', 'reservation_expires_at')
    op.drop_column('chats', 'reserved_coins')

    # Drop payment_status from insight_generation_jobs (no longer needed)
    op.drop_column('insight_generation_jobs', 'payment_status')


def downgrade() -> None:
    """Restore coin reservation pattern (for rollback only)."""
    # Re-add columns if rollback is needed
    op.add_column('chats', sa.Column('reserved_coins', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('chats', sa.Column('reservation_expires_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('insight_generation_jobs', sa.Column('payment_status', sa.String(), nullable=True))
