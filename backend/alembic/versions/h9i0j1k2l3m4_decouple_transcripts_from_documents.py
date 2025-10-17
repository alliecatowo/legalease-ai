"""Decouple transcripts from documents (Option 2 architecture)

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2025-10-16 21:00:00.000000

This migration transforms transcriptions into a standalone entity with direct
case_id foreign key, removing the dependency on the documents table.

Migration steps:
1. Add new columns to transcriptions table (case_id, filename, file_path, etc.)
2. Backfill data from documents table
3. Make case_id and required fields NOT NULL
4. Add FK constraint and indices
5. Rename transcript_segments.transcription_id -> transcript_id
6. Drop document_id FK and column (after code is updated)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'h9i0j1k2l3m4'
down_revision: Union[str, Sequence[str], None] = 'b156ff2242c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Decouple transcriptions from documents by adding direct case_id FK
    and copying document metadata fields into transcriptions table.
    """

    # Step 1: Add new columns to transcriptions table (initially nullable for backfill)
    print("Step 1: Adding new columns to transcriptions table...")

    op.add_column(
        'transcriptions',
        sa.Column('case_id', sa.Integer(), nullable=True)
    )
    op.add_column(
        'transcriptions',
        sa.Column('filename', sa.String(length=255), nullable=True)
    )
    op.add_column(
        'transcriptions',
        sa.Column('file_path', sa.String(length=512), nullable=True)
    )
    op.add_column(
        'transcriptions',
        sa.Column('mime_type', sa.String(length=100), nullable=True)
    )
    op.add_column(
        'transcriptions',
        sa.Column('size', sa.BigInteger(), nullable=True)
    )
    op.add_column(
        'transcriptions',
        sa.Column(
            'status',
            sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='documentstatus', native_enum=True),
            nullable=True
        )
    )
    op.add_column(
        'transcriptions',
        sa.Column('uploaded_at', sa.DateTime(), nullable=True)
    )

    # Step 2: Backfill data from documents table
    print("Step 2: Backfilling data from documents table...")

    op.execute("""
        UPDATE transcriptions t
        SET
            case_id = d.case_id,
            filename = d.filename,
            file_path = d.file_path,
            mime_type = d.mime_type,
            size = d.size,
            status = d.status,
            uploaded_at = d.uploaded_at
        FROM documents d
        WHERE t.document_id = d.id
    """)

    # Step 3: Make case_id and required fields NOT NULL
    print("Step 3: Making required fields NOT NULL...")

    op.alter_column('transcriptions', 'case_id', nullable=False)
    op.alter_column('transcriptions', 'filename', nullable=False)
    op.alter_column('transcriptions', 'file_path', nullable=False)
    op.alter_column('transcriptions', 'size', nullable=False)
    op.alter_column('transcriptions', 'status', nullable=False)
    op.alter_column('transcriptions', 'uploaded_at', nullable=False)
    # mime_type remains nullable (some formats might not have it)

    # Step 4: Add FK constraint and indices
    print("Step 4: Adding FK constraint and indices...")

    op.create_foreign_key(
        'fk_transcriptions_case_id',
        'transcriptions',
        'cases',
        ['case_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_index('ix_transcriptions_case_id', 'transcriptions', ['case_id'])
    op.create_index('ix_transcriptions_status', 'transcriptions', ['status'])
    op.create_index('ix_transcriptions_filename', 'transcriptions', ['filename'])

    # Step 5: Rename transcript_segments.transcription_id -> transcript_id for clarity
    print("Step 5: Renaming transcript_segments.transcription_id -> transcript_id...")

    # Drop existing FK constraint
    op.drop_constraint('transcript_segments_transcription_id_fkey', 'transcript_segments', type_='foreignkey')
    op.drop_index('ix_transcript_segments_transcription_id', table_name='transcript_segments')

    # Rename the column
    op.alter_column('transcript_segments', 'transcription_id', new_column_name='transcript_id')

    # Recreate FK constraint with new name
    op.create_foreign_key(
        'fk_transcript_segments_transcript_id',
        'transcript_segments',
        'transcriptions',
        ['transcript_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_index('ix_transcript_segments_transcript_id', 'transcript_segments', ['transcript_id'])

    # Step 6: Make document_id nullable (will be dropped in future migration after code is updated)
    print("Step 6: Making document_id nullable for backward compatibility...")

    # First drop the unique constraint
    op.drop_constraint('transcriptions_document_id_key', 'transcriptions', type_='unique')

    # Make document_id nullable
    op.alter_column('transcriptions', 'document_id', nullable=True)

    print("Migration complete! Transcriptions are now decoupled from documents.")
    print("Note: document_id column remains for backward compatibility and will be dropped in a future migration.")


def downgrade() -> None:
    """
    Reverse the decoupling by removing new fields and restoring document_id dependency.

    WARNING: This downgrade assumes document records still exist for all transcriptions.
    If documents have been deleted, this downgrade may fail or result in data loss.
    """

    print("Downgrading: Re-coupling transcriptions to documents...")

    # Step 6 (reverse): Restore document_id NOT NULL and unique constraint
    print("Step 6 (reverse): Restoring document_id constraints...")

    # Verify all transcriptions have document_id before making it NOT NULL
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM transcriptions WHERE document_id IS NULL) THEN
                RAISE EXCEPTION 'Cannot downgrade: Some transcriptions have NULL document_id';
            END IF;
        END $$;
    """)

    op.alter_column('transcriptions', 'document_id', nullable=False)
    op.create_unique_constraint('transcriptions_document_id_key', 'transcriptions', ['document_id'])

    # Step 5 (reverse): Rename transcript_segments.transcript_id -> transcription_id
    print("Step 5 (reverse): Renaming transcript_segments.transcript_id -> transcription_id...")

    op.drop_constraint('fk_transcript_segments_transcript_id', 'transcript_segments', type_='foreignkey')
    op.drop_index('ix_transcript_segments_transcript_id', table_name='transcript_segments')

    op.alter_column('transcript_segments', 'transcript_id', new_column_name='transcription_id')

    op.create_foreign_key(
        'transcript_segments_transcription_id_fkey',
        'transcript_segments',
        'transcriptions',
        ['transcription_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_index('ix_transcript_segments_transcription_id', 'transcript_segments', ['transcription_id'])

    # Step 4 (reverse): Drop FK constraint and indices
    print("Step 4 (reverse): Dropping FK constraint and indices...")

    op.drop_index('ix_transcriptions_filename', table_name='transcriptions')
    op.drop_index('ix_transcriptions_status', table_name='transcriptions')
    op.drop_index('ix_transcriptions_case_id', table_name='transcriptions')
    op.drop_constraint('fk_transcriptions_case_id', 'transcriptions', type_='foreignkey')

    # Step 3 (reverse): No action needed (columns will be dropped in next step)

    # Step 2 (reverse): No action needed (data backfill cannot be reversed)

    # Step 1 (reverse): Drop new columns from transcriptions table
    print("Step 1 (reverse): Dropping new columns from transcriptions table...")

    op.drop_column('transcriptions', 'uploaded_at')
    op.drop_column('transcriptions', 'status')
    op.drop_column('transcriptions', 'size')
    op.drop_column('transcriptions', 'mime_type')
    op.drop_column('transcriptions', 'file_path')
    op.drop_column('transcriptions', 'filename')
    op.drop_column('transcriptions', 'case_id')

    print("Downgrade complete! Transcriptions are re-coupled to documents.")
