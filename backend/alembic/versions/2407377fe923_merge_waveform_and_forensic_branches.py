"""merge waveform and forensic branches

Revision ID: 2407377fe923
Revises: c2d3e4f5g6h7, y64ulr87fwpa
Create Date: 2025-10-17 18:29:51.756361

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2407377fe923'
down_revision: Union[str, Sequence[str], None] = ('c2d3e4f5g6h7', 'y64ulr87fwpa')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
