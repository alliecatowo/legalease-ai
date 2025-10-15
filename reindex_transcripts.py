#!/usr/bin/env python3
"""
Script to queue indexing tasks for existing transcriptions.
Run this inside the worker container.
"""
from celery import Celery
import os

# Configure Celery
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
celery_app = Celery('legalease', broker=redis_url, backend=redis_url)

# Transcription IDs to index
transcription_ids = [1, 2, 3]

print(f"Queueing indexing tasks for {len(transcription_ids)} transcriptions...")

for trans_id in transcription_ids:
    # Queue the indexing task
    result = celery_app.send_task(
        'app.workers.tasks.transcript_indexing.index_transcript',
        args=[trans_id]
    )
    print(f"  ✓ Queued indexing for transcription {trans_id}, task ID: {result.id}")

print(f"\n✅ Successfully queued {len(transcription_ids)} indexing tasks")
print("Check worker logs to monitor progress:")
print("  docker logs -f legalease-worker")
