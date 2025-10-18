"""add username column to users table

Revision ID: 96b2dafae4c0
Revises: 5c3bf9d9f8a2
Create Date: 2025-10-18 02:55:06.610924

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96b2dafae4c0'
down_revision: Union[str, Sequence[str], None] = '5c3bf9d9f8a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add username column to users table
    op.add_column('users', sa.Column('username', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove username column from users table
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_column('users', 'username')
