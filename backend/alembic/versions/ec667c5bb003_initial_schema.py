"""Initial schema

Revision ID: ec667c5bb003
Revises:
Create Date: 2025-10-09 19:15:53.560489

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ec667c5bb003'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create cases table
    op.create_table(
        'cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('gid', sa.String(length=22), unique=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('case_number', sa.String(length=100), nullable=False),
        sa.Column('client', sa.String(length=255), nullable=False),
        sa.Column('matter_type', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('STAGING', 'PROCESSING', 'ACTIVE', 'UNLOADED', 'ARCHIVED',
                                    name='casestatus', native_enum=True, create_type=False),
                  nullable=False, server_default='STAGING'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('archived_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_number'),
        sa.UniqueConstraint('gid', name='uq_cases_gid')
    )
    op.create_index(op.f('ix_cases_gid'), 'cases', ['gid'], unique=False)
    op.create_index(op.f('ix_cases_name'), 'cases', ['name'], unique=False)
    op.create_index(op.f('ix_cases_case_number'), 'cases', ['case_number'], unique=False)
    op.create_index(op.f('ix_cases_client'), 'cases', ['client'], unique=False)
    op.create_index(op.f('ix_cases_status'), 'cases', ['status'], unique=False)

    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('gid', sa.String(length=22), unique=True, nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED',
                                    name='documentstatus', native_enum=True, create_type=False),
                  nullable=False, server_default='PENDING'),
        sa.Column('meta_data', sa.JSON(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gid', name='uq_documents_gid')
    )
    op.create_index(op.f('ix_documents_gid'), 'documents', ['gid'], unique=False)
    op.create_index(op.f('ix_documents_case_id'), 'documents', ['case_id'], unique=False)
    op.create_index(op.f('ix_documents_status'), 'documents', ['status'], unique=False)

    # Create chunks table
    op.create_table(
        'chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('gid', sa.String(length=22), unique=True, nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('chunk_type', sa.String(length=50), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('meta_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gid', name='uq_chunks_gid')
    )
    op.create_index(op.f('ix_chunks_gid'), 'chunks', ['gid'], unique=False)
    op.create_index(op.f('ix_chunks_document_id'), 'chunks', ['document_id'], unique=False)

    # Create entities table
    op.create_table(
        'entities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('gid', sa.String(length=22), unique=True, nullable=False),
        sa.Column('text', sa.String(length=255), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('meta_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gid', name='uq_entities_gid')
    )
    op.create_index(op.f('ix_entities_gid'), 'entities', ['gid'], unique=False)
    op.create_index(op.f('ix_entities_text'), 'entities', ['text'], unique=False)
    op.create_index(op.f('ix_entities_entity_type'), 'entities', ['entity_type'], unique=False)

    # Create document_entities association table
    op.create_table(
        'document_entities',
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('document_id', 'entity_id')
    )

    # Create transcriptions table
    op.create_table(
        'transcriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('gid', sa.String(length=22), unique=True, nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED',
                                    name='documentstatus', native_enum=True, create_type=False),
                  nullable=False, server_default='PENDING'),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('format', sa.String(length=50), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('speakers', sa.JSON(), nullable=True),
        sa.Column('segments', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('executive_summary', sa.Text(), nullable=True),
        sa.Column('key_moments', sa.JSON(), nullable=True),
        sa.Column('timeline', sa.JSON(), nullable=True),
        sa.Column('speaker_stats', sa.JSON(), nullable=True),
        sa.Column('action_items', sa.JSON(), nullable=True),
        sa.Column('topics', sa.JSON(), nullable=True),
        sa.Column('entities', sa.JSON(), nullable=True),
        sa.Column('summary_generated_at', sa.DateTime(), nullable=True),
        sa.Column('waveform_data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id'),
        sa.UniqueConstraint('gid', name='uq_transcriptions_gid')
    )
    op.create_index(op.f('ix_transcriptions_gid'), 'transcriptions', ['gid'], unique=False)
    op.create_index(op.f('ix_transcriptions_case_id'), 'transcriptions', ['case_id'], unique=False)
    op.create_index(op.f('ix_transcriptions_document_id'), 'transcriptions', ['document_id'], unique=True)

    # Create transcript_segments table
    op.create_table(
        'transcript_segments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('gid', sa.String(length=22), unique=True, nullable=False),
        sa.Column('transcript_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('segment_id', sa.String(length=36), nullable=False),
        sa.Column('is_key_moment', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('highlights', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['transcript_id'], ['transcriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('segment_id'),
        sa.UniqueConstraint('gid', name='uq_transcript_segments_gid')
    )
    op.create_index(op.f('ix_transcript_segments_gid'), 'transcript_segments', ['gid'], unique=False)
    op.create_index(op.f('ix_transcript_segments_transcript_id'), 'transcript_segments', ['transcript_id'], unique=False)
    op.create_index(op.f('ix_transcript_segments_segment_id'), 'transcript_segments', ['segment_id'], unique=True)

    # Create forensic_exports table
    op.create_table(
        'forensic_exports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('gid', sa.String(length=22), unique=True, nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column('summary_json', postgresql.JSONB(), nullable=True),
        sa.Column('export_options_json', postgresql.JSONB(), nullable=True),
        sa.Column('problems_json', postgresql.JSONB(), nullable=True),
        sa.Column('discovered_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_verified_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('folder_path'),
        sa.UniqueConstraint('gid', name='uq_forensic_exports_gid')
    )
    op.create_index(op.f('ix_forensic_exports_gid'), 'forensic_exports', ['gid'], unique=False)
    op.create_index(op.f('ix_forensic_exports_case_id'), 'forensic_exports', ['case_id'], unique=False)
    op.create_index(op.f('ix_forensic_exports_export_uuid'), 'forensic_exports', ['export_uuid'], unique=False)

    # Create processing_jobs table
    op.create_table(
        'processing_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('gid', sa.String(length=22), unique=True, nullable=False),
        sa.Column('job_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gid', name='uq_processing_jobs_gid')
    )
    op.create_index(op.f('ix_processing_jobs_gid'), 'processing_jobs', ['gid'], unique=False)
    op.create_index(op.f('ix_processing_jobs_job_type'), 'processing_jobs', ['job_type'], unique=False)
    op.create_index(op.f('ix_processing_jobs_status'), 'processing_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_processing_jobs_created_at'), 'processing_jobs', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order
    op.drop_index(op.f('ix_processing_jobs_created_at'), table_name='processing_jobs')
    op.drop_index(op.f('ix_processing_jobs_status'), table_name='processing_jobs')
    op.drop_index(op.f('ix_processing_jobs_job_type'), table_name='processing_jobs')
    op.drop_index(op.f('ix_processing_jobs_gid'), table_name='processing_jobs')
    op.drop_table('processing_jobs')

    op.drop_index(op.f('ix_forensic_exports_export_uuid'), table_name='forensic_exports')
    op.drop_index(op.f('ix_forensic_exports_case_id'), table_name='forensic_exports')
    op.drop_index(op.f('ix_forensic_exports_gid'), table_name='forensic_exports')
    op.drop_table('forensic_exports')

    op.drop_index(op.f('ix_transcript_segments_segment_id'), table_name='transcript_segments')
    op.drop_index(op.f('ix_transcript_segments_transcript_id'), table_name='transcript_segments')
    op.drop_index(op.f('ix_transcript_segments_gid'), table_name='transcript_segments')
    op.drop_table('transcript_segments')

    op.drop_index(op.f('ix_transcriptions_document_id'), table_name='transcriptions')
    op.drop_index(op.f('ix_transcriptions_case_id'), table_name='transcriptions')
    op.drop_index(op.f('ix_transcriptions_gid'), table_name='transcriptions')
    op.drop_table('transcriptions')

    op.drop_table('document_entities')

    op.drop_index(op.f('ix_entities_entity_type'), table_name='entities')
    op.drop_index(op.f('ix_entities_text'), table_name='entities')
    op.drop_index(op.f('ix_entities_gid'), table_name='entities')
    op.drop_table('entities')

    op.drop_index(op.f('ix_chunks_document_id'), table_name='chunks')
    op.drop_index(op.f('ix_chunks_gid'), table_name='chunks')
    op.drop_table('chunks')

    op.drop_index(op.f('ix_documents_status'), table_name='documents')
    op.drop_index(op.f('ix_documents_case_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_gid'), table_name='documents')
    op.drop_table('documents')

    op.drop_index(op.f('ix_cases_status'), table_name='cases')
    op.drop_index(op.f('ix_cases_client'), table_name='cases')
    op.drop_index(op.f('ix_cases_case_number'), table_name='cases')
    op.drop_index(op.f('ix_cases_name'), table_name='cases')
    op.drop_index(op.f('ix_cases_gid'), table_name='cases')
    op.drop_table('cases')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS documentstatus")
    op.execute("DROP TYPE IF EXISTS casestatus")
