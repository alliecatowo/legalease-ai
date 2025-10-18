#!/usr/bin/env python3
"""
Script to queue indexing tasks for existing transcriptions.
Run this inside the worker container or with proper database access.
"""
from celery import Celery
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.transcription import Transcription

# Configure Celery
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
celery_app = Celery('legalease', broker=redis_url, backend=redis_url)

# Get all transcription GIDs from database
db = SessionLocal()
try:
    transcriptions = db.query(Transcription).all()
    transcription_gids = [t.gid for t in transcriptions]

    if not transcription_gids:
        print("No transcriptions found in database")
        sys.exit(0)

    print(f"Queueing indexing tasks for {len(transcription_gids)} transcriptions...")

    for trans_gid in transcription_gids:
        # Queue the indexing task (now uses GID strings)
        result = celery_app.send_task(
            'app.workers.tasks.transcript_indexing.index_transcript',
            args=[trans_gid]
        )
        print(f"  ✓ Queued indexing for transcription {trans_gid}, task ID: {result.id}")

    print(f"\n✅ Successfully queued {len(transcription_gids)} indexing tasks")
    print("Check worker logs to monitor progress:")
    print("  docker logs -f legalease-worker")
finally:
    db.close()
