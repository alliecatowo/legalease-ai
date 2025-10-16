"""Add discovery system tables

Revision ID: m9n8o7p6q5r4
Revises: f7g8h9i0j1k2
Create Date: 2025-10-15 16:54:55.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'm9n8o7p6q5r4'
down_revision: Union[str, Sequence[str], None] = 'f7g8h9i0j1k2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all discovery system tables."""

    # Create enums first using DO blocks for conditional creation
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE discoveryitemtype AS ENUM ('PHOTO', 'VIDEO', 'AUDIO', 'SOCIAL_POST', 'EMAIL', 'CALL_LOG', 'SMS');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE discoveryitemsource AS ENUM ('CELLEBRITE', 'PROSECUTOR', 'EVIDENCE', 'SURVEILLANCE', 'BODY_CAM');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE discoveryitemformfactor AS ENUM ('SHORT_FORM', 'LONG_FORM', 'SINGLE_ITEM');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE categorytype AS ENUM ('AUTO_GENERATED', 'MANUAL', 'CASE_SPECIFIC');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE calltype AS ENUM ('INCOMING', 'OUTGOING', 'MISSED', 'VOICEMAIL');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE importstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create categories table (independent, self-referential)
    op.execute("""
        CREATE TABLE categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            type categorytype NOT NULL,
            parent_category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for categories
    op.create_index('ix_categories_id', 'categories', ['id'])
    op.create_index('ix_categories_name', 'categories', ['name'], unique=True)
    op.create_index('ix_categories_type', 'categories', ['type'])
    op.create_index('ix_categories_parent_category_id', 'categories', ['parent_category_id'])

    # Create discovery_items table (depends on cases)
    op.execute("""
        CREATE TABLE discovery_items (
            id SERIAL PRIMARY KEY,
            case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            type discoveryitemtype NOT NULL,
            source discoveryitemsource NOT NULL,
            form_factor discoveryitemformfactor NOT NULL,
            original_filename VARCHAR(512) NOT NULL,
            file_path VARCHAR(1024) NOT NULL,
            item_metadata JSONB,
            processed BOOLEAN NOT NULL DEFAULT FALSE,
            importance_score FLOAT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT check_importance_score_range CHECK (importance_score IS NULL OR (importance_score >= 0.0 AND importance_score <= 1.0))
        )
    """)

    # Create indexes for discovery_items
    op.create_index('ix_discovery_items_id', 'discovery_items', ['id'])
    op.create_index('ix_discovery_items_case_id', 'discovery_items', ['case_id'])
    op.create_index('ix_discovery_items_type', 'discovery_items', ['type'])
    op.create_index('ix_discovery_items_source', 'discovery_items', ['source'])
    op.create_index('ix_discovery_items_form_factor', 'discovery_items', ['form_factor'])
    op.create_index('ix_discovery_items_processed', 'discovery_items', ['processed'])
    op.create_index('ix_discovery_items_importance_score', 'discovery_items', ['importance_score'])

    # Create discovery_item_categories association table (depends on discovery_items and categories)
    op.execute("""
        CREATE TABLE discovery_item_categories (
            discovery_item_id INTEGER NOT NULL REFERENCES discovery_items(id) ON DELETE CASCADE,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            confidence_score FLOAT,
            auto_generated BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (discovery_item_id, category_id),
            CONSTRAINT check_category_confidence_score_range CHECK (confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0))
        )
    """)

    # Create indexes for discovery_item_categories
    op.create_index('ix_discovery_item_categories_discovery_item_id', 'discovery_item_categories', ['discovery_item_id'])
    op.create_index('ix_discovery_item_categories_category_id', 'discovery_item_categories', ['category_id'])
    op.create_index('ix_discovery_item_categories_auto_generated', 'discovery_item_categories', ['auto_generated'])

    # Create visual_content table (depends on discovery_items)
    op.execute("""
        CREATE TABLE visual_content (
            id SERIAL PRIMARY KEY,
            discovery_item_id INTEGER NOT NULL REFERENCES discovery_items(id) ON DELETE CASCADE,
            frame_number INTEGER,
            timestamp_in_video FLOAT,
            vlm_caption TEXT,
            detected_objects JSONB,
            detected_scenes JSONB,
            detected_activities JSONB,
            sensitive_flags JSONB,
            is_meme BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for visual_content
    op.create_index('ix_visual_content_id', 'visual_content', ['id'])
    op.create_index('ix_visual_content_discovery_item_id', 'visual_content', ['discovery_item_id'])

    # Create video_summaries table (depends on discovery_items)
    op.execute("""
        CREATE TABLE video_summaries (
            id SERIAL PRIMARY KEY,
            discovery_item_id INTEGER NOT NULL UNIQUE REFERENCES discovery_items(id) ON DELETE CASCADE,
            comprehensive_summary TEXT,
            key_moments JSONB,
            visual_summary TEXT,
            audio_summary TEXT,
            importance_score FLOAT,
            flagged_content JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT check_video_importance_score_range CHECK (importance_score IS NULL OR (importance_score >= 0.0 AND importance_score <= 1.0))
        )
    """)

    # Create indexes for video_summaries
    op.create_index('ix_video_summaries_id', 'video_summaries', ['id'])
    op.create_index('ix_video_summaries_discovery_item_id', 'video_summaries', ['discovery_item_id'], unique=True)
    op.create_index('ix_video_summaries_importance_score', 'video_summaries', ['importance_score'])

    # Create social_media_posts table (depends on discovery_items)
    op.execute("""
        CREATE TABLE social_media_posts (
            id SERIAL PRIMARY KEY,
            discovery_item_id INTEGER NOT NULL UNIQUE REFERENCES discovery_items(id) ON DELETE CASCADE,
            platform VARCHAR(100) NOT NULL,
            author VARCHAR(255),
            post_text TEXT,
            post_timestamp TIMESTAMP,
            engagement_metrics JSONB,
            thread_id VARCHAR(255),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for social_media_posts
    op.create_index('ix_social_media_posts_id', 'social_media_posts', ['id'])
    op.create_index('ix_social_media_posts_discovery_item_id', 'social_media_posts', ['discovery_item_id'], unique=True)
    op.create_index('ix_social_media_posts_platform', 'social_media_posts', ['platform'])
    op.create_index('ix_social_media_posts_author', 'social_media_posts', ['author'])
    op.create_index('ix_social_media_posts_post_timestamp', 'social_media_posts', ['post_timestamp'])
    op.create_index('ix_social_media_posts_thread_id', 'social_media_posts', ['thread_id'])

    # Create email_messages table (depends on discovery_items)
    op.execute("""
        CREATE TABLE email_messages (
            id SERIAL PRIMARY KEY,
            discovery_item_id INTEGER NOT NULL UNIQUE REFERENCES discovery_items(id) ON DELETE CASCADE,
            sender VARCHAR(255) NOT NULL,
            recipients JSONB NOT NULL,
            subject VARCHAR(512),
            body_text TEXT,
            timestamp TIMESTAMP NOT NULL,
            attachments JSONB,
            thread_id VARCHAR(255),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for email_messages
    op.create_index('ix_email_messages_id', 'email_messages', ['id'])
    op.create_index('ix_email_messages_discovery_item_id', 'email_messages', ['discovery_item_id'], unique=True)
    op.create_index('ix_email_messages_sender', 'email_messages', ['sender'])
    op.create_index('ix_email_messages_subject', 'email_messages', ['subject'])
    op.create_index('ix_email_messages_timestamp', 'email_messages', ['timestamp'])
    op.create_index('ix_email_messages_thread_id', 'email_messages', ['thread_id'])

    # Create call_logs table (depends on discovery_items)
    op.execute("""
        CREATE TABLE call_logs (
            id SERIAL PRIMARY KEY,
            discovery_item_id INTEGER NOT NULL UNIQUE REFERENCES discovery_items(id) ON DELETE CASCADE,
            caller VARCHAR(255) NOT NULL,
            recipient VARCHAR(255) NOT NULL,
            duration INTEGER NOT NULL DEFAULT 0,
            timestamp TIMESTAMP NOT NULL,
            call_type calltype NOT NULL,
            associated_audio_id INTEGER REFERENCES discovery_items(id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for call_logs
    op.create_index('ix_call_logs_id', 'call_logs', ['id'])
    op.create_index('ix_call_logs_discovery_item_id', 'call_logs', ['discovery_item_id'], unique=True)
    op.create_index('ix_call_logs_caller', 'call_logs', ['caller'])
    op.create_index('ix_call_logs_recipient', 'call_logs', ['recipient'])
    op.create_index('ix_call_logs_timestamp', 'call_logs', ['timestamp'])
    op.create_index('ix_call_logs_call_type', 'call_logs', ['call_type'])
    op.create_index('ix_call_logs_associated_audio_id', 'call_logs', ['associated_audio_id'])

    # Create import_batches table (depends on cases)
    op.execute("""
        CREATE TABLE import_batches (
            id SERIAL PRIMARY KEY,
            case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            source_type VARCHAR(100) NOT NULL,
            total_items INTEGER NOT NULL DEFAULT 0,
            processed_items INTEGER NOT NULL DEFAULT 0,
            status importstatus NOT NULL DEFAULT 'PENDING',
            import_path VARCHAR(1024) NOT NULL,
            error_log TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    # Create indexes for import_batches
    op.create_index('ix_import_batches_id', 'import_batches', ['id'])
    op.create_index('ix_import_batches_case_id', 'import_batches', ['case_id'])
    op.create_index('ix_import_batches_source_type', 'import_batches', ['source_type'])
    op.create_index('ix_import_batches_status', 'import_batches', ['status'])


def downgrade() -> None:
    """Drop all discovery system tables."""

    # Drop tables in reverse order of creation to respect foreign key constraints
    op.drop_index('ix_import_batches_status', table_name='import_batches')
    op.drop_index('ix_import_batches_source_type', table_name='import_batches')
    op.drop_index('ix_import_batches_case_id', table_name='import_batches')
    op.drop_index('ix_import_batches_id', table_name='import_batches')
    op.drop_table('import_batches')

    op.drop_index('ix_call_logs_associated_audio_id', table_name='call_logs')
    op.drop_index('ix_call_logs_call_type', table_name='call_logs')
    op.drop_index('ix_call_logs_timestamp', table_name='call_logs')
    op.drop_index('ix_call_logs_recipient', table_name='call_logs')
    op.drop_index('ix_call_logs_caller', table_name='call_logs')
    op.drop_index('ix_call_logs_discovery_item_id', table_name='call_logs')
    op.drop_index('ix_call_logs_id', table_name='call_logs')
    op.drop_table('call_logs')

    op.drop_index('ix_email_messages_thread_id', table_name='email_messages')
    op.drop_index('ix_email_messages_timestamp', table_name='email_messages')
    op.drop_index('ix_email_messages_subject', table_name='email_messages')
    op.drop_index('ix_email_messages_sender', table_name='email_messages')
    op.drop_index('ix_email_messages_discovery_item_id', table_name='email_messages')
    op.drop_index('ix_email_messages_id', table_name='email_messages')
    op.drop_table('email_messages')

    op.drop_index('ix_social_media_posts_thread_id', table_name='social_media_posts')
    op.drop_index('ix_social_media_posts_post_timestamp', table_name='social_media_posts')
    op.drop_index('ix_social_media_posts_author', table_name='social_media_posts')
    op.drop_index('ix_social_media_posts_platform', table_name='social_media_posts')
    op.drop_index('ix_social_media_posts_discovery_item_id', table_name='social_media_posts')
    op.drop_index('ix_social_media_posts_id', table_name='social_media_posts')
    op.drop_table('social_media_posts')

    op.drop_index('ix_video_summaries_importance_score', table_name='video_summaries')
    op.drop_index('ix_video_summaries_discovery_item_id', table_name='video_summaries')
    op.drop_index('ix_video_summaries_id', table_name='video_summaries')
    op.drop_table('video_summaries')

    op.drop_index('ix_visual_content_discovery_item_id', table_name='visual_content')
    op.drop_index('ix_visual_content_id', table_name='visual_content')
    op.drop_table('visual_content')

    op.drop_index('ix_discovery_item_categories_auto_generated', table_name='discovery_item_categories')
    op.drop_index('ix_discovery_item_categories_category_id', table_name='discovery_item_categories')
    op.drop_index('ix_discovery_item_categories_discovery_item_id', table_name='discovery_item_categories')
    op.drop_table('discovery_item_categories')

    op.drop_index('ix_discovery_items_importance_score', table_name='discovery_items')
    op.drop_index('ix_discovery_items_processed', table_name='discovery_items')
    op.drop_index('ix_discovery_items_form_factor', table_name='discovery_items')
    op.drop_index('ix_discovery_items_source', table_name='discovery_items')
    op.drop_index('ix_discovery_items_type', table_name='discovery_items')
    op.drop_index('ix_discovery_items_case_id', table_name='discovery_items')
    op.drop_index('ix_discovery_items_id', table_name='discovery_items')
    op.drop_table('discovery_items')

    op.drop_index('ix_categories_parent_category_id', table_name='categories')
    op.drop_index('ix_categories_type', table_name='categories')
    op.drop_index('ix_categories_name', table_name='categories')
    op.drop_index('ix_categories_id', table_name='categories')
    op.drop_table('categories')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS importstatus')
    op.execute('DROP TYPE IF EXISTS calltype')
    op.execute('DROP TYPE IF EXISTS categorytype')
    op.execute('DROP TYPE IF EXISTS discoveryitemformfactor')
    op.execute('DROP TYPE IF EXISTS discoveryitemsource')
    op.execute('DROP TYPE IF EXISTS discoveryitemtype')
