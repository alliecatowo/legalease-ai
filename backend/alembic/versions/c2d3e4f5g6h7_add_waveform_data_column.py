"""add_waveform_data_column

Revision ID: c2d3e4f5g6h7
Revises: b156ff2242c8
Create Date: 2025-10-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5g6h7'
down_revision: Union[str, Sequence[str], None] = 'b156ff2242c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add waveform_data column to transcriptions."""
    op.add_column('transcriptions', sa.Column('waveform_data', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema - Remove waveform_data column."""
    op.drop_column('transcriptions', 'waveform_data')
