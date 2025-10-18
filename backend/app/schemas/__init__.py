"""Pydantic schemas for request/response validation."""

from app.schemas.case import (
    CaseBase,
    CaseCreate,
    CaseUpdate,
    CaseResponse,
    CaseListItem,
    CaseListResponse,
    CaseStatusUpdate,
    CaseDeleteResponse,
)
from app.schemas.search import (
    SearchQuery,
    SearchResult,
    HybridSearchRequest,
    HybridSearchResponse,
    DocumentChunk,
    IndexRequest,
    IndexResponse,
)
from app.schemas.transcription import (
    TranscriptionCreate,
    TranscriptionResponse,
    TranscriptionListItem,
    TranscriptionListResponse,
    TranscriptionDeleteResponse,
    TranscriptionUploadResponse,
    TranscriptionSegment,
    SpeakerInfo,
    TranscriptionFormat,
)
from app.schemas.user import (
    AuditLogEntry,
    InviteUserRequest,
    TeamCreateRequest,
    TeamMembershipResponse,
    TeamSummary,
    UpdateActiveTeamRequest,
    UpdateUserProfileRequest,
    UserProfileResponse,
    UserPublicProfile,
)

__all__ = [
    # Case schemas
    "CaseBase",
    "CaseCreate",
    "CaseUpdate",
    "CaseResponse",
    "CaseListItem",
    "CaseListResponse",
    "CaseStatusUpdate",
    "CaseDeleteResponse",
    # Search schemas
    "SearchQuery",
    "SearchResult",
    "HybridSearchRequest",
    "HybridSearchResponse",
    "DocumentChunk",
    "IndexRequest",
    "IndexResponse",
    # Transcription schemas
    "TranscriptionCreate",
    "TranscriptionResponse",
    "TranscriptionListItem",
    "TranscriptionListResponse",
    "TranscriptionDeleteResponse",
    "TranscriptionUploadResponse",
    "TranscriptionSegment",
    "SpeakerInfo",
    "TranscriptionFormat",
    # User schemas
    "UserProfileResponse",
    "UserPublicProfile",
    "UpdateUserProfileRequest",
    "TeamSummary",
    "TeamMembershipResponse",
    "UpdateActiveTeamRequest",
    "TeamCreateRequest",
    "InviteUserRequest",
    "AuditLogEntry",
]
