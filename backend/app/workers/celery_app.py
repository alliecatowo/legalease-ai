"""
Celery Application Configuration
"""
from celery import Celery
from kombu import Queue

from app.core.config import settings

# Create Celery app instance
celery_app = Celery(
    "legalease",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.document_processing",
        "app.workers.tasks.transcription",
        "app.workers.tasks.transcript_indexing",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # Task result settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    # Task queues
    task_queues=(
        Queue("documents", routing_key="documents"),
        Queue("transcription", routing_key="transcription"),
        Queue("ai", routing_key="ai"),
    ),

    # Default queue
    task_default_queue="documents",
    task_default_exchange="legalease",
    task_default_routing_key="documents",

    # Task routing
    task_routes={
        "process_document": {"queue": "documents"},
        "generate_document": {"queue": "documents"},
        "transcribe_audio": {"queue": "transcription"},
        "process_transcription": {"queue": "transcription"},
        "extract_entities": {"queue": "ai"},
        "analyze_document": {"queue": "ai"},
    },

    # Beat schedule (for periodic tasks - can be configured later)
    beat_schedule={},

    # Worker settings
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks to prevent memory leaks
    worker_disable_rate_limits=False,

    # Monitoring
    task_track_started=True,
    task_send_sent_event=True,
)


# Optional: Add event handlers
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f"Request: {self.request!r}")
