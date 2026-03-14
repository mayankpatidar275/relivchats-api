"""encrypt sensitive columns

Revision ID: b7e2f9a3c1d5
Revises: 4c5d6e7f8g9h
Create Date: 2026-03-14

Changes JSON columns that now use EncryptedJSON to TEXT, since encrypted
values are strings and cannot be stored in a JSON column.

  chats.chat_metadata        JSON  → TEXT
  message_chunks.chunk_metadata JSON → TEXT
  insights.content           JSON  → TEXT

The EncryptedText/EncryptedJSON TypeDecorators handle encryption on write and
decryption on read transparently. Existing plaintext rows are returned as-is
and will be encrypted on their next write (graceful migration).

NOTE: If you have dev data you want to preserve, existing rows will remain
readable. If you want a clean start, truncate the affected tables manually
after running this migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7e2f9a3c1d5'
down_revision: Union[str, Sequence[str], None] = '4c5d6e7f8g9h'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cast existing JSON values to their text representation.
    # PostgreSQL's ::text cast on a JSON column produces a valid JSON string,
    # so EncryptedJSON's fallback (json.loads) will still parse old rows correctly.
    op.alter_column(
        'chats', 'chat_metadata',
        type_=sa.Text(),
        postgresql_using='chat_metadata::text',
        existing_nullable=True,
    )
    op.alter_column(
        'message_chunks', 'chunk_metadata',
        type_=sa.Text(),
        postgresql_using='chunk_metadata::text',
        existing_nullable=True,
    )
    op.alter_column(
        'insights', 'content',
        type_=sa.Text(),
        postgresql_using='content::text',
        existing_nullable=True,
    )


def downgrade() -> None:
    # Cast text values back to JSON.
    # Note: encrypted rows written after the upgrade will NOT be parseable as
    # JSON — downgrade is only safe if no encrypted rows exist yet.
    op.alter_column(
        'insights', 'content',
        type_=sa.JSON(),
        postgresql_using='content::json',
        existing_nullable=True,
    )
    op.alter_column(
        'message_chunks', 'chunk_metadata',
        type_=sa.JSON(),
        postgresql_using='chunk_metadata::json',
        existing_nullable=True,
    )
    op.alter_column(
        'chats', 'chat_metadata',
        type_=sa.JSON(),
        postgresql_using='chat_metadata::json',
        existing_nullable=True,
    )
