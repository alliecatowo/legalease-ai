"""
Transcript Indexing Tasks

Celery tasks for indexing transcription segments into Qdrant for search.
"""
import logging
from typing import Dict, Any, Optional, List

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.transcript_indexing_service import get_transcript_indexing_service
from app.models.transcription import Transcription

logger = logging.getLogger(__name__)


class TranscriptIndexingError(Exception):
    """Custom exception for transcript indexing errors."""
    pass


@celery_app.task(name="index_transcript", bind=True)
def index_transcript(
    self,
    transcription_id: int,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Index a transcription's segments into Qdrant for search.

    Args:
        transcription_id: ID of the transcription to index
        options: Optional dict containing configuration:
            - batch_size: Number of points to upload per batch

    Returns:
        Dict containing indexing status and results
    """
    db = SessionLocal()

    # Parse options with defaults
    options = options or {}
    batch_size = options.get("batch_size", 100)

    try:
        # Update task state to STARTED
        self.update_state(
            state='STARTED',
            meta={'status': 'Initializing transcript indexing', 'progress': 0}
        )

        # Step 1: Verify transcription exists
        logger.info(f"Starting indexing for transcription {transcription_id}")
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()

        if not transcription:
            raise TranscriptIndexingError(f"Transcription {transcription_id} not found")

        # Step 2: Index segments
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Indexing transcript segments', 'progress': 20}
        )

        indexing_service = get_transcript_indexing_service()
        result = indexing_service.index_transcription(
            transcription_id=transcription_id,
            db=db,
            batch_size=batch_size,
        )

        logger.info(f"Indexing completed successfully for transcription {transcription_id}")

        # Step 3: Return success result
        return {
            'status': 'completed',
            'transcription_id': transcription_id,
            'indexed_count': result.get('indexed_count', 0),
            'failed_count': result.get('failed_count', 0),
            'total_segments': result.get('total_segments', 0),
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Indexing failed for transcription {transcription_id}: {str(e)}", exc_info=True)

        # Update task state
        self.update_state(
            state='FAILURE',
            meta={'status': f'Indexing failed: {str(e)}', 'error': str(e)}
        )

        return {
            'status': 'failed',
            'error': str(e),
            'transcription_id': transcription_id,
            'task_id': self.request.id
        }

    finally:
        db.close()


@celery_app.task(name="reindex_transcript", bind=True)
def reindex_transcript(
    self,
    transcription_id: int,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Re-index a transcription (delete old index and create new).

    Useful when transcription has been re-processed or updated.

    Args:
        transcription_id: ID of the transcription
        options: Optional configuration

    Returns:
        Dict containing reindexing status and results
    """
    db = SessionLocal()

    # Parse options with defaults
    options = options or {}
    batch_size = options.get("batch_size", 100)

    try:
        logger.info(f"Starting reindexing for transcription {transcription_id}")

        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Reindexing transcript', 'progress': 0}
        )

        # Verify transcription exists
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()

        if not transcription:
            raise TranscriptIndexingError(f"Transcription {transcription_id} not found")

        # Reindex (delete + index)
        indexing_service = get_transcript_indexing_service()
        result = indexing_service.update_index(
            transcription_id=transcription_id,
            db=db,
            batch_size=batch_size,
        )

        logger.info(f"Reindexing completed successfully for transcription {transcription_id}")

        return {
            'status': 'completed',
            'transcription_id': transcription_id,
            'indexed_count': result.get('indexed_count', 0),
            'failed_count': result.get('failed_count', 0),
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Reindexing failed for transcription {transcription_id}: {str(e)}", exc_info=True)

        self.update_state(
            state='FAILURE',
            meta={'status': f'Reindexing failed: {str(e)}', 'error': str(e)}
        )

        return {
            'status': 'failed',
            'error': str(e),
            'transcription_id': transcription_id,
            'task_id': self.request.id
        }

    finally:
        db.close()


@celery_app.task(name="batch_index_transcripts", bind=True)
def batch_index_transcripts(
    self,
    transcription_ids: List[int],
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Batch index multiple transcriptions.

    Args:
        transcription_ids: List of transcription IDs to index
        options: Optional configuration

    Returns:
        Dict containing batch indexing results
    """
    db = SessionLocal()

    # Parse options with defaults
    options = options or {}
    batch_size = options.get("batch_size", 100)

    try:
        logger.info(f"Starting batch indexing for {len(transcription_ids)} transcriptions")

        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={
                'status': f'Batch indexing {len(transcription_ids)} transcriptions',
                'progress': 0
            }
        )

        # Batch index
        indexing_service = get_transcript_indexing_service()
        result = indexing_service.batch_index(
            transcription_ids=transcription_ids,
            db=db,
            batch_size=batch_size,
        )

        logger.info(f"Batch indexing completed: {result['successful_transcriptions']} succeeded, {result['failed_transcriptions']} failed")

        return {
            'status': 'completed',
            'total_transcriptions': result.get('total_transcriptions', 0),
            'successful_transcriptions': result.get('successful_transcriptions', 0),
            'failed_transcriptions': result.get('failed_transcriptions', 0),
            'total_segments_indexed': result.get('total_segments_indexed', 0),
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Batch indexing failed: {str(e)}", exc_info=True)

        self.update_state(
            state='FAILURE',
            meta={'status': f'Batch indexing failed: {str(e)}', 'error': str(e)}
        )

        return {
            'status': 'failed',
            'error': str(e),
            'task_id': self.request.id
        }

    finally:
        db.close()


@celery_app.task(name="index_case_transcripts", bind=True)
def index_case_transcripts(
    self,
    case_id: int,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Index all transcriptions for a case.

    Args:
        case_id: ID of the case
        options: Optional configuration

    Returns:
        Dict containing indexing results
    """
    db = SessionLocal()

    # Parse options with defaults
    options = options or {}
    batch_size = options.get("batch_size", 100)

    try:
        logger.info(f"Starting transcription indexing for case {case_id}")

        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={'status': f'Indexing transcripts for case {case_id}', 'progress': 0}
        )

        # Index all case transcriptions
        indexing_service = get_transcript_indexing_service()
        result = indexing_service.index_case_transcriptions(
            case_id=case_id,
            db=db,
            batch_size=batch_size,
        )

        logger.info(f"Case transcription indexing completed for case {case_id}")

        return {
            'status': 'completed',
            'case_id': case_id,
            'total_transcriptions': result.get('total_transcriptions', 0),
            'successful_transcriptions': result.get('successful_transcriptions', 0),
            'failed_transcriptions': result.get('failed_transcriptions', 0),
            'total_segments_indexed': result.get('total_segments_indexed', 0),
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Case transcription indexing failed for case {case_id}: {str(e)}", exc_info=True)

        self.update_state(
            state='FAILURE',
            meta={'status': f'Case indexing failed: {str(e)}', 'error': str(e)}
        )

        return {
            'status': 'failed',
            'error': str(e),
            'case_id': case_id,
            'task_id': self.request.id
        }

    finally:
        db.close()


@celery_app.task(name="delete_transcript_from_index", bind=True)
def delete_transcript_from_index(
    self,
    transcription_id: int
) -> Dict[str, Any]:
    """
    Delete a transcription from the search index.

    Args:
        transcription_id: ID of the transcription

    Returns:
        Dict containing deletion status
    """
    try:
        logger.info(f"Deleting transcription {transcription_id} from index")

        indexing_service = get_transcript_indexing_service()
        result = indexing_service.delete_from_index(transcription_id=transcription_id)

        return {
            'status': 'completed',
            'transcription_id': transcription_id,
            'deleted': result.get('deleted', False),
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Deletion failed for transcription {transcription_id}: {str(e)}", exc_info=True)

        return {
            'status': 'failed',
            'error': str(e),
            'transcription_id': transcription_id,
            'task_id': self.request.id
        }
