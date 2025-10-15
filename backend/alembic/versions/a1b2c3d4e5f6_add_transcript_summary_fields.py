"""Add transcript summary fields

Revision ID: a1b2c3d4e5f6
Revises: ec667c5bb003
Create Date: 2025-10-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'ec667c5bb003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add summary and analysis fields to transcriptions table."""
    # Add executive summary field
    op.add_column('transcriptions',
        sa.Column('executive_summary', sa.Text(), nullable=True))

    # Add key moments field
    op.add_column('transcriptions',
        sa.Column('key_moments', sa.JSON(), nullable=True))

    # Add timeline field
    op.add_column('transcriptions',
        sa.Column('timeline', sa.JSON(), nullable=True))

    # Add speaker statistics field
    op.add_column('transcriptions',
        sa.Column('speaker_stats', sa.JSON(), nullable=True))

    # Add action items field
    op.add_column('transcriptions',
        sa.Column('action_items', sa.JSON(), nullable=True))

    # Add topics field
    op.add_column('transcriptions',
        sa.Column('topics', sa.JSON(), nullable=True))

    # Add entities field
    op.add_column('transcriptions',
        sa.Column('entities', sa.JSON(), nullable=True))

    # Add summary generation timestamp
    op.add_column('transcriptions',
        sa.Column('summary_generated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove summary and analysis fields from transcriptions table."""
    op.drop_column('transcriptions', 'summary_generated_at')
    op.drop_column('transcriptions', 'entities')
    op.drop_column('transcriptions', 'topics')
    op.drop_column('transcriptions', 'action_items')
    op.drop_column('transcriptions', 'speaker_stats')
    op.drop_column('transcriptions', 'timeline')
    op.drop_column('transcriptions', 'key_moments')
    op.drop_column('transcriptions', 'executive_summary')
