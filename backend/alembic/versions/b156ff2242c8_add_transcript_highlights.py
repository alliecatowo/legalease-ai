"""add_transcript_highlights

Revision ID: b156ff2242c8
Revises: f7g8h9i0j1k2
Create Date: 2025-10-17 02:26:41.639840

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b156ff2242c8'
down_revision: Union[str, Sequence[str], None] = 'f7g8h9i0j1k2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add highlights column to transcript_segments."""
    # Only add the highlights column - skip all the discovery table drops
    # as those will be handled in a fresh DB reset
    op.add_column('transcript_segments', sa.Column('highlights', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema - Remove highlights column."""
    op.drop_column('transcript_segments', 'highlights')
