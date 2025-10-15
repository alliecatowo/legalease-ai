"""Add transcript segment key moments

Revision ID: f7g8h9i0j1k2
Revises: a1b2c3d4e5f6
Create Date: 2025-10-11 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7g8h9i0j1k2'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create transcript_segments table for tracking key moments."""
    op.create_table(
        'transcript_segments',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('transcription_id', sa.Integer(), nullable=False),
        sa.Column('segment_id', sa.String(length=36), nullable=False),
        sa.Column('is_key_moment', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['transcription_id'], ['transcriptions.id'], ondelete='CASCADE'),
    )

    # Create indexes for performance
    op.create_index('ix_transcript_segments_id', 'transcript_segments', ['id'])
    op.create_index('ix_transcript_segments_transcription_id', 'transcript_segments', ['transcription_id'])
    op.create_index('ix_transcript_segments_segment_id', 'transcript_segments', ['segment_id'], unique=True)


def downgrade() -> None:
    """Drop transcript_segments table."""
    op.drop_index('ix_transcript_segments_segment_id', table_name='transcript_segments')
    op.drop_index('ix_transcript_segments_transcription_id', table_name='transcript_segments')
    op.drop_index('ix_transcript_segments_id', table_name='transcript_segments')
    op.drop_table('transcript_segments')
