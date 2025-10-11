"""
Summarization Tasks

Celery tasks for transcript summarization and analysis using Ollama LLM.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.transcription import Transcription
from app.services.transcript_summarization import TranscriptSummarizer

logger = logging.getLogger(__name__)


class SummarizationError(Exception):
    """Custom exception for summarization errors."""
    pass


@celery_app.task(name="summarize_transcript", bind=True)
def summarize_transcript(
    self,
    transcription_id: int,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive summary and analysis for a transcript.

    Uses local Ollama LLM (7B models) to generate:
    - Executive summary (200-300 words)
    - Key moments (top 10-15 important moments)
    - Timeline (chronological events)
    - Speaker statistics (speaking time, word count)
    - Action items (decisions, agreements, follow-ups)
    - Topics and entities (parties, dates, legal terms, citations)

    Args:
        transcription_id: ID of the transcription to summarize
        options: Optional dict containing configuration:
            - components: List of components to generate (default: all)
            - model: Ollama model to use (default: from settings)
            - regenerate: Force regeneration even if summary exists

    Returns:
        Dict containing summarization status and results
    """
    db = SessionLocal()

    # Parse options with defaults
    options = options or {}
    components = options.get("components")  # None = all components
    model = options.get("model")  # None = use default from settings
    regenerate = options.get("regenerate", False)

    try:
        # Update task state to STARTED
        self.update_state(
            state='STARTED',
            meta={'status': 'Initializing summarization', 'progress': 0}
        )

        # Step 1: Get transcription from database
        logger.info(f"Starting summarization for transcription {transcription_id}")
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()

        if not transcription:
            raise SummarizationError(f"Transcription {transcription_id} not found")

        # Check if summary already exists
        if not regenerate and transcription.summary_generated_at:
            logger.info(f"Summary already exists for transcription {transcription_id}, skipping")
            return {
                'status': 'skipped',
                'transcription_id': transcription_id,
                'message': 'Summary already exists. Use regenerate=True to force regeneration.',
                'summary_generated_at': transcription.summary_generated_at.isoformat()
            }

        # Get segments
        segments = transcription.segments
        if not segments:
            raise SummarizationError("Transcription has no segments")

        # Step 2: Prepare metadata
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Preparing metadata', 'progress': 10}
        )

        metadata = {}
        if transcription.document:
            if transcription.document.case:
                metadata['case_name'] = transcription.document.case.name
                metadata['case_number'] = transcription.document.case.case_number
            metadata['filename'] = transcription.document.filename
            metadata['uploaded_at'] = transcription.document.uploaded_at.isoformat()

        if transcription.duration:
            metadata['duration_seconds'] = transcription.duration

        # Step 3: Generate summary using TranscriptSummarizer
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Generating comprehensive analysis', 'progress': 20}
        )

        logger.info(f"Generating summary with components: {components or 'all'}")

        # Use async summarization in a sync context
        import asyncio

        async def run_summarization():
            async with TranscriptSummarizer(model=model) as summarizer:
                return await summarizer.generate_full_analysis(
                    segments=segments,
                    metadata=metadata,
                    include_components=components
                )

        # Run async function in sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        analysis_result = loop.run_until_complete(run_summarization())

        # Step 4: Extract results
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Saving analysis results', 'progress': 90}
        )

        analysis = analysis_result.get('analysis', {})

        # Update transcription record
        transcription.executive_summary = analysis.get('executive_summary')
        transcription.key_moments = analysis.get('key_moments')
        transcription.timeline = analysis.get('timeline')
        transcription.speaker_stats = analysis.get('speaker_stats')
        transcription.action_items = analysis.get('action_items')
        transcription.topics = analysis.get('topics')
        transcription.entities = analysis.get('entities')
        transcription.summary_generated_at = datetime.utcnow()

        db.commit()

        logger.info(f"Summarization completed successfully for transcription {transcription_id}")

        # Step 5: Return success result
        return {
            'status': 'completed',
            'transcription_id': transcription_id,
            'summary_generated_at': transcription.summary_generated_at.isoformat(),
            'components_generated': list(analysis.keys()),
            'statistics': {
                'key_moments_count': len(analysis.get('key_moments', [])),
                'timeline_events_count': len(analysis.get('timeline', [])),
                'action_items_count': len(analysis.get('action_items', [])),
                'topics_count': len(analysis.get('topics', [])),
                'speakers_analyzed': len(analysis.get('speaker_stats', {}))
            },
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Summarization failed for transcription {transcription_id}: {str(e)}", exc_info=True)

        # Update task state
        self.update_state(
            state='FAILURE',
            meta={'status': f'Summarization failed: {str(e)}', 'error': str(e)}
        )

        return {
            'status': 'failed',
            'error': str(e),
            'transcription_id': transcription_id,
            'task_id': self.request.id
        }

    finally:
        db.close()


@celery_app.task(name="regenerate_summary", bind=True)
def regenerate_summary(
    self,
    transcription_id: int,
    components: Optional[list] = None
) -> Dict[str, Any]:
    """
    Regenerate specific components of a transcript summary.

    Useful for updating only certain parts of the analysis.

    Args:
        transcription_id: ID of the transcription
        components: List of components to regenerate (default: all)

    Returns:
        Dict containing regeneration status and results
    """
    return summarize_transcript(
        self,
        transcription_id,
        options={
            'components': components,
            'regenerate': True
        }
    )


@celery_app.task(name="batch_summarize_transcripts", bind=True)
def batch_summarize_transcripts(
    self,
    transcription_ids: list[int],
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Batch summarize multiple transcriptions.

    Useful for processing multiple transcriptions at once.

    Args:
        transcription_ids: List of transcription IDs to summarize
        options: Optional configuration (passed to each summarize_transcript call)

    Returns:
        Dict containing batch summarization results
    """
    logger.info(f"Starting batch summarization for {len(transcription_ids)} transcriptions")

    results = {
        'total': len(transcription_ids),
        'completed': 0,
        'failed': 0,
        'skipped': 0,
        'details': []
    }

    for idx, transcription_id in enumerate(transcription_ids):
        # Update progress
        progress = int((idx / len(transcription_ids)) * 100)
        self.update_state(
            state='PROCESSING',
            meta={
                'status': f'Processing transcription {idx + 1}/{len(transcription_ids)}',
                'progress': progress
            }
        )

        try:
            # Summarize this transcription
            result = summarize_transcript(
                self,
                transcription_id,
                options=options
            )

            # Track results
            status = result.get('status', 'unknown')
            if status == 'completed':
                results['completed'] += 1
            elif status == 'failed':
                results['failed'] += 1
            elif status == 'skipped':
                results['skipped'] += 1

            results['details'].append({
                'transcription_id': transcription_id,
                'status': status,
                'result': result
            })

        except Exception as e:
            logger.error(f"Failed to summarize transcription {transcription_id}: {e}")
            results['failed'] += 1
            results['details'].append({
                'transcription_id': transcription_id,
                'status': 'failed',
                'error': str(e)
            })

    logger.info(f"Batch summarization completed: {results['completed']} succeeded, {results['failed']} failed, {results['skipped']} skipped")

    return results


@celery_app.task(name="quick_summary", bind=True)
def quick_summary(
    self,
    transcription_id: int
) -> Dict[str, Any]:
    """
    Generate just the executive summary (fast, minimal analysis).

    Useful when you need a quick overview without full analysis.

    Args:
        transcription_id: ID of the transcription

    Returns:
        Dict containing executive summary
    """
    db = SessionLocal()

    try:
        logger.info(f"Generating quick summary for transcription {transcription_id}")

        # Get transcription
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()

        if not transcription:
            raise SummarizationError(f"Transcription {transcription_id} not found")

        segments = transcription.segments
        if not segments:
            raise SummarizationError("Transcription has no segments")

        # Prepare minimal metadata
        metadata = {}
        if transcription.document and transcription.document.case:
            metadata['case_name'] = transcription.document.case.name

        # Generate only executive summary
        import asyncio
        from app.services.transcript_summarization import quick_summary as quick_summary_func

        async def run_quick_summary():
            return await quick_summary_func(segments, metadata)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        summary = loop.run_until_complete(run_quick_summary())

        # Update only executive summary
        transcription.executive_summary = summary
        transcription.summary_generated_at = datetime.utcnow()
        db.commit()

        return {
            'status': 'completed',
            'transcription_id': transcription_id,
            'executive_summary': summary,
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Quick summary failed for transcription {transcription_id}: {e}")
        return {
            'status': 'failed',
            'error': str(e),
            'transcription_id': transcription_id,
            'task_id': self.request.id
        }

    finally:
        db.close()
