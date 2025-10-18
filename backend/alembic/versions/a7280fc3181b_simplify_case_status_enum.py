"""simplify_case_status_enum

Revision ID: a7280fc3181b
Revises: ec667c5bb003
Create Date: 2025-10-18 08:47:36.349170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7280fc3181b'
down_revision: Union[str, Sequence[str], None] = 'ec667c5bb003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Simplify case status enum: ACTIVE, CLOSED, ARCHIVED."""
    # Step 1: Drop default and convert column to text temporarily
    op.execute("ALTER TABLE cases ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE cases ALTER COLUMN status TYPE text")

    # Step 2: Migrate data to new status values
    op.execute("""
        UPDATE cases
        SET status = 'ACTIVE'
        WHERE status IN ('STAGING', 'PROCESSING')
    """)

    op.execute("""
        UPDATE cases
        SET status = 'CLOSED'
        WHERE status = 'UNLOADED'
    """)

    # Step 3: Drop old enum and create new one
    op.execute("DROP TYPE IF EXISTS casestatus")
    op.execute("CREATE TYPE casestatus AS ENUM ('ACTIVE', 'CLOSED', 'ARCHIVED')")

    # Step 4: Convert column back to enum with new type and restore default
    op.execute("""
        ALTER TABLE cases
        ALTER COLUMN status TYPE casestatus
        USING status::casestatus
    """)
    op.execute("ALTER TABLE cases ALTER COLUMN status SET DEFAULT 'ACTIVE'::casestatus")


def downgrade() -> None:
    """Restore old case status enum."""
    # Recreate old enum
    op.execute("ALTER TYPE casestatus RENAME TO casestatus_new")
    op.execute("CREATE TYPE casestatus AS ENUM ('STAGING', 'PROCESSING', 'ACTIVE', 'UNLOADED', 'ARCHIVED')")

    # Map new statuses back to old
    op.execute("""
        UPDATE cases
        SET status = 'STAGING'::text
        WHERE status::text = 'ACTIVE'
    """)

    op.execute("""
        UPDATE cases
        SET status = 'UNLOADED'::text
        WHERE status::text = 'CLOSED'
    """)

    op.execute("""
        ALTER TABLE cases
        ALTER COLUMN status TYPE casestatus
        USING status::text::casestatus
    """)
    op.execute("DROP TYPE casestatus_new")
