"""
Workers Module

Celery task queue configuration and tasks.
"""
from app.workers.celery_app import celery_app

__all__ = ["celery_app"]
