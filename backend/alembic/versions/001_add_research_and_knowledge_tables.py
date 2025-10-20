"""Add research and knowledge graph tables

Revision ID: 001_research_knowledge
Revises: a7280fc3181b
Create Date: 2025-10-19 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_research_knowledge'
down_revision: Union[str, Sequence[str], None] = 'a7280fc3181b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ========================================================================
    # Research Domain Tables
    # ========================================================================

    # Create research_runs table
    op.create_table(
        'research_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('phase', sa.String(length=50), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('dossier_path', sa.String(length=512), nullable=True),
        sa.Column('findings', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('config', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_research_runs_case_id'), 'research_runs', ['case_id'], unique=False)
    op.create_index(op.f('ix_research_runs_status'), 'research_runs', ['status'], unique=False)
    op.create_index('ix_research_runs_case_id_status', 'research_runs', ['case_id', 'status'], unique=False)
    op.create_index('ix_research_runs_started_at', 'research_runs', ['started_at'], unique=False)

    # Create findings table
    op.create_table(
        'findings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('research_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('finding_type', sa.String(length=50), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('relevance', sa.Float(), nullable=False),
        sa.Column('entities', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('citations', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('tags', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['research_run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_findings_research_run_id'), 'findings', ['research_run_id'], unique=False)
    op.create_index(op.f('ix_findings_finding_type'), 'findings', ['finding_type'], unique=False)
    op.create_index('ix_findings_research_run_type', 'findings', ['research_run_id', 'finding_type'], unique=False)
    op.create_index('ix_findings_confidence', 'findings', ['confidence'], unique=False)

    # Create hypotheses table
    op.create_table(
        'hypotheses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('research_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hypothesis_text', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('supporting_findings', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('contradicting_findings', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['research_run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hypotheses_research_run_id'), 'hypotheses', ['research_run_id'], unique=False)
    op.create_index('ix_hypotheses_confidence', 'hypotheses', ['confidence'], unique=False)

    # Create dossiers table
    op.create_table(
        'dossiers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('research_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('executive_summary', sa.Text(), nullable=False),
        sa.Column('citations_appendix', sa.Text(), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=False),
        sa.Column('sections', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['research_run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('research_run_id')
    )
    op.create_index(op.f('ix_dossiers_research_run_id'), 'dossiers', ['research_run_id'], unique=True)

    # ========================================================================
    # Knowledge Graph Domain Tables
    # ========================================================================

    # Create kg_entities table
    op.create_table(
        'kg_entities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('first_seen', sa.DateTime(), nullable=False),
        sa.Column('last_seen', sa.DateTime(), nullable=False),
        sa.Column('aliases', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('attributes', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('source_citations', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kg_entities_entity_type'), 'kg_entities', ['entity_type'], unique=False)
    op.create_index(op.f('ix_kg_entities_name'), 'kg_entities', ['name'], unique=False)
    op.create_index('ix_kg_entities_type_name', 'kg_entities', ['entity_type', 'name'], unique=False)
    op.create_index('ix_kg_entities_first_seen', 'kg_entities', ['first_seen'], unique=False)
    op.create_index('ix_kg_entities_last_seen', 'kg_entities', ['last_seen'], unique=False)

    # Create kg_events table
    op.create_table(
        'kg_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('participants', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('source_citations', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kg_events_event_type'), 'kg_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_kg_events_timestamp'), 'kg_events', ['timestamp'], unique=False)
    op.create_index('ix_kg_events_type_timestamp', 'kg_events', ['event_type', 'timestamp'], unique=False)

    # Create kg_relationships table
    op.create_table(
        'kg_relationships',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column('from_entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('to_entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False),
        sa.Column('strength', sa.Float(), nullable=False),
        sa.Column('temporal_start', sa.DateTime(), nullable=True),
        sa.Column('temporal_end', sa.DateTime(), nullable=True),
        sa.Column('source_citations', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['from_entity_id'], ['kg_entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_entity_id'], ['kg_entities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kg_relationships_from_entity_id'), 'kg_relationships', ['from_entity_id'], unique=False)
    op.create_index(op.f('ix_kg_relationships_to_entity_id'), 'kg_relationships', ['to_entity_id'], unique=False)
    op.create_index('ix_kg_relationships_from_to', 'kg_relationships', ['from_entity_id', 'to_entity_id'], unique=False)
    op.create_index('ix_kg_relationships_type', 'kg_relationships', ['relationship_type'], unique=False)
    op.create_index('ix_kg_relationships_strength', 'kg_relationships', ['strength'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""

    # Drop knowledge graph tables
    op.drop_index('ix_kg_relationships_strength', table_name='kg_relationships')
    op.drop_index('ix_kg_relationships_type', table_name='kg_relationships')
    op.drop_index('ix_kg_relationships_from_to', table_name='kg_relationships')
    op.drop_index(op.f('ix_kg_relationships_to_entity_id'), table_name='kg_relationships')
    op.drop_index(op.f('ix_kg_relationships_from_entity_id'), table_name='kg_relationships')
    op.drop_table('kg_relationships')

    op.drop_index('ix_kg_events_type_timestamp', table_name='kg_events')
    op.drop_index(op.f('ix_kg_events_timestamp'), table_name='kg_events')
    op.drop_index(op.f('ix_kg_events_event_type'), table_name='kg_events')
    op.drop_table('kg_events')

    op.drop_index('ix_kg_entities_last_seen', table_name='kg_entities')
    op.drop_index('ix_kg_entities_first_seen', table_name='kg_entities')
    op.drop_index('ix_kg_entities_type_name', table_name='kg_entities')
    op.drop_index(op.f('ix_kg_entities_name'), table_name='kg_entities')
    op.drop_index(op.f('ix_kg_entities_entity_type'), table_name='kg_entities')
    op.drop_table('kg_entities')

    # Drop research tables
    op.drop_index(op.f('ix_dossiers_research_run_id'), table_name='dossiers')
    op.drop_table('dossiers')

    op.drop_index('ix_hypotheses_confidence', table_name='hypotheses')
    op.drop_index(op.f('ix_hypotheses_research_run_id'), table_name='hypotheses')
    op.drop_table('hypotheses')

    op.drop_index('ix_findings_confidence', table_name='findings')
    op.drop_index('ix_findings_research_run_type', table_name='findings')
    op.drop_index(op.f('ix_findings_finding_type'), table_name='findings')
    op.drop_index(op.f('ix_findings_research_run_id'), table_name='findings')
    op.drop_table('findings')

    op.drop_index('ix_research_runs_started_at', table_name='research_runs')
    op.drop_index('ix_research_runs_case_id_status', table_name='research_runs')
    op.drop_index(op.f('ix_research_runs_status'), table_name='research_runs')
    op.drop_index(op.f('ix_research_runs_case_id'), table_name='research_runs')
    op.drop_table('research_runs')
