"""add_forensic_exports_table

Revision ID: y64ulr87fwpa
Revises: h9i0j1k2l3m4
Create Date: 2025-10-17 05:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'y64ulr87fwpa'
down_revision: Union[str, Sequence[str], None] = 'h9i0j1k2l3m4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add forensic_exports table."""
    op.create_table(
        'forensic_exports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('folder_path', sa.String(length=1024), nullable=False),
        sa.Column('folder_name', sa.String(length=512), nullable=True),
        sa.Column('export_uuid', sa.String(length=36), nullable=True),
        sa.Column('axiom_version', sa.String(length=50), nullable=True),
        sa.Column('total_records', sa.Integer(), nullable=True),
        sa.Column('exported_records', sa.Integer(), nullable=True),
        sa.Column('num_attachments', sa.Integer(), nullable=True),
        sa.Column('export_start_date', sa.DateTime(), nullable=True),
        sa.Column('export_end_date', sa.DateTime(), nullable=True),
        sa.Column('export_duration', sa.String(length=50), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('export_status', sa.String(length=50), nullable=True),
        sa.Column('case_directory', sa.String(length=512), nullable=True),
        sa.Column('case_storage_location', sa.String(length=256), nullable=True),
        sa.Column('summary_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('export_options_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('problems_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('discovered_at', sa.DateTime(), nullable=False),
        sa.Column('last_verified_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('folder_path')
    )
    op.create_index(op.f('ix_forensic_exports_id'), 'forensic_exports', ['id'], unique=False)
    op.create_index(op.f('ix_forensic_exports_case_id'), 'forensic_exports', ['case_id'], unique=False)
    op.create_index(op.f('ix_forensic_exports_export_uuid'), 'forensic_exports', ['export_uuid'], unique=False)


def downgrade() -> None:
    """Downgrade schema - Remove forensic_exports table."""
    op.drop_index(op.f('ix_forensic_exports_export_uuid'), table_name='forensic_exports')
    op.drop_index(op.f('ix_forensic_exports_case_id'), table_name='forensic_exports')
    op.drop_index(op.f('ix_forensic_exports_id'), table_name='forensic_exports')
    op.drop_table('forensic_exports')
