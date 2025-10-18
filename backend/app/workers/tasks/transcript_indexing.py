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
    transcription_gid: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Index a transcription's segments into Qdrant for search.

    Args:
        transcription_gid: GID of the transcription to index
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

        # Step 1: Verify transcription exists using GID
        logger.info(f"Starting indexing for transcription {transcription_gid}")
        transcription = db.query(Transcription).filter(
            Transcription.gid == transcription_gid
        ).first()

        if not transcription:
            raise TranscriptIndexingError(f"Transcription with GID {transcription_gid} not found")

        # Step 2: Index segments
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Indexing transcript segments', 'progress': 20}
        )

        indexing_service = get_transcript_indexing_service()
        result = indexing_service.index_transcription(
            transcription_id=transcription.id,
            db=db,
            batch_size=batch_size,
        )

        logger.info(f"Indexing completed successfully for transcription {transcription_gid}")

        # Step 3: Return success result
        return {
            'status': 'completed',
            'transcription_gid': transcription_gid,
            'indexed_count': result.get('indexed_count', 0),
            'failed_count': result.get('failed_count', 0),
            'total_segments': result.get('total_segments', 0),
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Indexing failed for transcription {transcription_gid}: {str(e)}", exc_info=True)

        # Update task state
        self.update_state(
            state='FAILURE',
            meta={'status': f'Indexing failed: {str(e)}', 'error': str(e)}
        )

        return {
            'status': 'failed',
            'error': str(e),
            'transcription_gid': transcription_gid,
            'task_id': self.request.id
        }

    finally:
        db.close()


@celery_app.task(name="reindex_transcript", bind=True)
def reindex_transcript(
    self,
    transcription_gid: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Re-index a transcription (delete old index and create new).

    Useful when transcription has been re-processed or updated.

    Args:
        transcription_gid: GID of the transcription
        options: Optional configuration

    Returns:
        Dict containing reindexing status and results
    """
    db = SessionLocal()

    # Parse options with defaults
    options = options or {}
    batch_size = options.get("batch_size", 100)

    try:
        logger.info(f"Starting reindexing for transcription {transcription_gid}")

        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Reindexing transcript', 'progress': 0}
        )

        # Verify transcription exists using GID
        transcription = db.query(Transcription).filter(
            Transcription.gid == transcription_gid
        ).first()

        if not transcription:
            raise TranscriptIndexingError(f"Transcription with GID {transcription_gid} not found")

        # Reindex (delete + index)
        indexing_service = get_transcript_indexing_service()
        result = indexing_service.update_index(
            transcription_id=transcription.id,
            db=db,
            batch_size=batch_size,
        )

        logger.info(f"Reindexing completed successfully for transcription {transcription_gid}")

        return {
            'status': 'completed',
            'transcription_gid': transcription_gid,
            'indexed_count': result.get('indexed_count', 0),
            'failed_count': result.get('failed_count', 0),
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Reindexing failed for transcription {transcription_gid}: {str(e)}", exc_info=True)

        self.update_state(
            state='FAILURE',
            meta={'status': f'Reindexing failed: {str(e)}', 'error': str(e)}
        )

        return {
            'status': 'failed',
            'error': str(e),
            'transcription_gid': transcription_gid,
            'task_id': self.request.id
        }

    finally:
        db.close()


@celery_app.task(name="batch_index_transcripts", bind=True)
def batch_index_transcripts(
    self,
    transcription_gids: List[str],
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Batch index multiple transcriptions.

    Args:
        transcription_gids: List of transcription GIDs to index
        options: Optional configuration

    Returns:
        Dict containing batch indexing results
    """
    db = SessionLocal()

    # Parse options with defaults
    options = options or {}
    batch_size = options.get("batch_size", 100)

    try:
        logger.info(f"Starting batch indexing for {len(transcription_gids)} transcriptions")

        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={
                'status': f'Batch indexing {len(transcription_gids)} transcriptions',
                'progress': 0
            }
        )

        # Convert GIDs to UUIDs for the service layer
        transcriptions = db.query(Transcription).filter(
            Transcription.gid.in_(transcription_gids)
        ).all()
        transcription_ids = [t.id for t in transcriptions]

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
    case_gid: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Index all transcriptions for a case.

    Args:
        case_gid: GID of the case
        options: Optional configuration

    Returns:
        Dict containing indexing results
    """
    from app.models.case import Case
    db = SessionLocal()

    # Parse options with defaults
    options = options or {}
    batch_size = options.get("batch_size", 100)

    try:
        logger.info(f"Starting transcription indexing for case {case_gid}")

        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={'status': f'Indexing transcripts for case {case_gid}', 'progress': 0}
        )

        # Get case using GID
        case = db.query(Case).filter(Case.gid == case_gid).first()
        if not case:
            raise TranscriptIndexingError(f"Case with GID {case_gid} not found")

        # Index all case transcriptions
        indexing_service = get_transcript_indexing_service()
        result = indexing_service.index_case_transcriptions(
            case_id=case.id,
            db=db,
            batch_size=batch_size,
        )

        logger.info(f"Case transcription indexing completed for case {case_gid}")

        return {
            'status': 'completed',
            'case_gid': case_gid,
            'total_transcriptions': result.get('total_transcriptions', 0),
            'successful_transcriptions': result.get('successful_transcriptions', 0),
            'failed_transcriptions': result.get('failed_transcriptions', 0),
            'total_segments_indexed': result.get('total_segments_indexed', 0),
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Case transcription indexing failed for case {case_gid}: {str(e)}", exc_info=True)

        self.update_state(
            state='FAILURE',
            meta={'status': f'Case indexing failed: {str(e)}', 'error': str(e)}
        )

        return {
            'status': 'failed',
            'error': str(e),
            'case_gid': case_gid,
            'task_id': self.request.id
        }

    finally:
        db.close()


@celery_app.task(name="delete_transcript_from_index", bind=True)
def delete_transcript_from_index(
    self,
    transcription_gid: str
) -> Dict[str, Any]:
    """
    Delete a transcription from the search index.

    Args:
        transcription_gid: GID of the transcription

    Returns:
        Dict containing deletion status
    """
    db = SessionLocal()
    try:
        logger.info(f"Deleting transcription {transcription_gid} from index")

        # Get transcription using GID
        transcription = db.query(Transcription).filter(Transcription.gid == transcription_gid).first()
        if not transcription:
            raise TranscriptIndexingError(f"Transcription with GID {transcription_gid} not found")

        indexing_service = get_transcript_indexing_service()
        result = indexing_service.delete_from_index(transcription_id=transcription.id)

        return {
            'status': 'completed',
            'transcription_gid': transcription_gid,
            'deleted': result.get('deleted', False),
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Deletion failed for transcription {transcription_gid}: {str(e)}", exc_info=True)

        return {
            'status': 'failed',
            'error': str(e),
            'transcription_gid': transcription_gid,
            'task_id': self.request.id
        }
    finally:
        db.close()
