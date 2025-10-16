"""Database models for LegalEase."""

from app.core.database import Base
from app.models.case import Case, CaseStatus
from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk
from app.models.entity import Entity, document_entities
from app.models.transcription import Transcription
from app.models.processing_job import ProcessingJob
from app.models.discovery_item import (
    DiscoveryItem,
    DiscoveryItemType,
    DiscoveryItemSource,
    DiscoveryItemFormFactor
)
from app.models.visual_content import VisualContent
from app.models.video_summary import VideoSummary
from app.models.category import Category, CategoryType
from app.models.discovery_item_category import DiscoveryItemCategory
from app.models.social_media_post import SocialMediaPost
from app.models.email_message import EmailMessage
from app.models.call_log import CallLog, CallType
from app.models.import_batch import ImportBatch, ImportStatus

# Export all models for easier imports
__all__ = [
    "Base",
    "Case",
    "CaseStatus",
    "Document",
    "DocumentStatus",
    "Chunk",
    "Entity",
    "document_entities",
    "Transcription",
    "ProcessingJob",
    "DiscoveryItem",
    "DiscoveryItemType",
    "DiscoveryItemSource",
    "DiscoveryItemFormFactor",
    "VisualContent",
    "VideoSummary",
    "Category",
    "CategoryType",
    "DiscoveryItemCategory",
    "SocialMediaPost",
    "EmailMessage",
    "CallLog",
    "CallType",
    "ImportBatch",
    "ImportStatus",
]
