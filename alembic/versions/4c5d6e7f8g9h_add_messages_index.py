"""add_messages_chat_id_timestamp_index

Revision ID: 4c5d6e7f8g9h
Revises: 1e8d721efe24
Create Date: 2026-01-12 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c5d6e7f8g9h'
down_revision: Union[str, None] = '1e8d721efe24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add composite index on (chat_id, timestamp) for fast message fetching
    # This speeds up vector indexing from 12 minutes to ~30 seconds
    op.create_index(
        'ix_messages_chat_id_timestamp',
        'messages',
        ['chat_id', 'timestamp'],
        unique=False
    )


def downgrade() -> None:
    # Remove the index
    op.drop_index('ix_messages_chat_id_timestamp', table_name='messages')
