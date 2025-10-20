"""
Pydantic schemas for evidence-related API requests and responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.shared.types.enums import EvidenceType, ChunkType


class SearchEvidenceRequest(BaseModel):
    """
    Request schema for hybrid evidence search.

    Combines BM25 keyword search with semantic vector search using
    Reciprocal Rank Fusion.
    """

    query: str = Field(..., min_length=2, description="Search query text")
    case_ids: Optional[List[UUID]] = Field(None, description="Filter by case IDs")
    evidence_types: Optional[List[EvidenceType]] = Field(
        None,
        description="Filter by evidence types (DOCUMENT, TRANSCRIPT, COMMUNICATION)"
    )
    chunk_types: Optional[List[ChunkType]] = Field(
        None,
        description="Filter by chunk types (SUMMARY, SECTION, MICROBLOCK, etc.)"
    )
    speaker_filter: Optional[List[str]] = Field(
        None,
        description="Filter by speaker names (for transcripts)"
    )
    date_range: Optional[Tuple[datetime, datetime]] = Field(
        None,
        description="Filter by date range (start, end)"
    )
    top_k: int = Field(
        20,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )
    score_threshold: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score threshold"
    )
    search_mode: str = Field(
        "HYBRID",
        description="Search mode: HYBRID, KEYWORD_ONLY, or SEMANTIC_ONLY"
    )

    @field_validator("search_mode")
    @classmethod
    def validate_search_mode(cls, v: str) -> str:
        """Validate search mode."""
        valid_modes = {"HYBRID", "KEYWORD_ONLY", "SEMANTIC_ONLY"}
        if v not in valid_modes:
            raise ValueError(f"search_mode must be one of {valid_modes}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "contract breach damages",
                "case_ids": ["123e4567-e89b-12d3-a456-426614174000"],
                "evidence_types": ["DOCUMENT", "TRANSCRIPT"],
                "chunk_types": ["SECTION", "MICROBLOCK"],
                "speaker_filter": ["John Doe", "Jane Smith"],
                "top_k": 20,
                "score_threshold": 0.3,
                "search_mode": "HYBRID"
            }
        }
    }


class SearchResultSchema(BaseModel):
    """
    Individual search result with relevance scoring and metadata.
    """

    chunk_id: UUID = Field(..., description="Unique chunk identifier")
    source_id: UUID = Field(..., description="Source evidence ID (document, transcript, etc.)")
    source_type: EvidenceType = Field(..., description="Type of source evidence")
    text: str = Field(..., description="Text content of the chunk")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")
    match_type: str = Field(..., description="Type of match (keyword, semantic, hybrid)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    locator: Dict[str, Any] = Field(
        default_factory=dict,
        description="Location information (page, paragraph, timestamp, etc.)"
    )
    highlights: List[str] = Field(
        default_factory=list,
        description="Highlighted text snippets showing matches"
    )

    @classmethod
    def from_dto(cls, dto: Any) -> "SearchResultSchema":
        """
        Create schema from DTO (Data Transfer Object).

        Args:
            dto: Search result DTO from application layer

        Returns:
            SearchResultSchema instance
        """
        return cls(
            chunk_id=dto.chunk_id,
            source_id=dto.source_id,
            source_type=dto.source_type,
            text=dto.text,
            score=dto.score,
            match_type=dto.match_type,
            metadata=dto.metadata,
            locator=dto.locator,
            highlights=dto.highlights,
        )

    model_config = {
        "json_schema_extra": {
            "example": {
                "chunk_id": "123e4567-e89b-12d3-a456-426614174001",
                "source_id": "123e4567-e89b-12d3-a456-426614174002",
                "source_type": "DOCUMENT",
                "text": "The parties agreed to the contract terms on March 15, 2024...",
                "score": 0.87,
                "match_type": "hybrid",
                "metadata": {
                    "document_name": "Contract_Agreement.pdf",
                    "page_count": 25,
                    "file_size": 1024000
                },
                "locator": {
                    "page": 5,
                    "paragraph": 2,
                    "start_char": 120,
                    "end_char": 450
                },
                "highlights": [
                    "...agreed to the <mark>contract</mark> terms...",
                    "...breach of contract on March 20..."
                ]
            }
        }
    }


class SearchEvidenceResponse(BaseModel):
    """
    Response schema for evidence search results.
    """

    results: List[SearchResultSchema] = Field(
        default_factory=list,
        description="List of search results ranked by relevance"
    )
    total_found: int = Field(..., ge=0, description="Total number of results found")
    search_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Search execution metadata (timing, scores, filters applied)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [],
                "total_found": 42,
                "search_metadata": {
                    "search_time_ms": 127,
                    "bm25_results": 30,
                    "semantic_results": 25,
                    "fusion_method": "rrf",
                    "filters_applied": ["case_ids", "evidence_types"]
                }
            }
        }
    }


class ProcessEvidenceRequest(BaseModel):
    """
    Request schema for processing new evidence.
    """

    evidence_id: UUID = Field(..., description="ID of evidence to process")
    evidence_type: EvidenceType = Field(..., description="Type of evidence")
    force_reindex: bool = Field(
        False,
        description="Force reindexing even if already processed"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "evidence_id": "123e4567-e89b-12d3-a456-426614174000",
                "evidence_type": "DOCUMENT",
                "force_reindex": False
            }
        }
    }


class ProcessEvidenceResponse(BaseModel):
    """
    Response schema for evidence processing.
    """

    message: str = Field(..., description="Status message")
    evidence_id: UUID = Field(..., description="ID of evidence being processed")
    chunks_indexed: int = Field(..., ge=0, description="Number of chunks indexed")
    processing_started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Processing start timestamp"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Evidence processing started",
                "evidence_id": "123e4567-e89b-12d3-a456-426614174000",
                "chunks_indexed": 150,
                "processing_started_at": "2024-10-19T12:30:00Z"
            }
        }
    }


class DocumentDetailResponse(BaseModel):
    """
    Detailed document information.
    """

    id: UUID
    filename: str
    file_path: str
    mime_type: str
    size: int
    page_count: Optional[int] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    status: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    case_id: UUID
    chunk_count: Optional[int] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "Contract_Agreement.pdf",
                "file_path": "cases/case-123/documents/Contract_Agreement.pdf",
                "mime_type": "application/pdf",
                "size": 1024000,
                "page_count": 25,
                "uploaded_at": "2024-10-19T10:00:00Z",
                "processed_at": "2024-10-19T10:05:00Z",
                "status": "processed",
                "metadata": {
                    "author": "Legal Team",
                    "created_date": "2024-03-15"
                },
                "case_id": "123e4567-e89b-12d3-a456-426614174099",
                "chunk_count": 150
            }
        }
    }


class TranscriptDetailResponse(BaseModel):
    """
    Detailed transcript information.
    """

    id: UUID
    filename: str
    audio_file_path: Optional[str] = None
    transcript_file_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    uploaded_at: datetime
    transcribed_at: Optional[datetime] = None
    status: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    case_id: UUID
    segment_count: Optional[int] = None
    speaker_count: Optional[int] = None
    speakers: List[str] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "Deposition_2024-03-15.mp3",
                "audio_file_path": "cases/case-123/audio/Deposition_2024-03-15.mp3",
                "transcript_file_path": "cases/case-123/transcripts/Deposition_2024-03-15.json",
                "duration_seconds": 3600.5,
                "uploaded_at": "2024-10-19T10:00:00Z",
                "transcribed_at": "2024-10-19T10:30:00Z",
                "status": "transcribed",
                "metadata": {
                    "location": "Attorney's Office",
                    "date": "2024-03-15"
                },
                "case_id": "123e4567-e89b-12d3-a456-426614174099",
                "segment_count": 450,
                "speaker_count": 3,
                "speakers": ["John Doe", "Jane Smith", "Attorney Johnson"]
            }
        }
    }


class CommunicationDetailResponse(BaseModel):
    """
    Detailed communication (email/message) information.
    """

    id: UUID
    subject: Optional[str] = None
    sender: str
    recipients: List[str] = Field(default_factory=list)
    cc: List[str] = Field(default_factory=list)
    bcc: List[str] = Field(default_factory=list)
    sent_at: datetime
    received_at: Optional[datetime] = None
    body: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    case_id: UUID
    thread_id: Optional[UUID] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "subject": "RE: Contract Amendment",
                "sender": "john.doe@company.com",
                "recipients": ["jane.smith@company.com"],
                "cc": ["legal@company.com"],
                "bcc": [],
                "sent_at": "2024-03-15T14:30:00Z",
                "received_at": "2024-03-15T14:30:05Z",
                "body": "Please review the attached contract amendment...",
                "attachments": [
                    {"filename": "amendment.pdf", "size": 102400}
                ],
                "metadata": {
                    "message_id": "abc123@mail.company.com",
                    "in_reply_to": "xyz789@mail.company.com"
                },
                "case_id": "123e4567-e89b-12d3-a456-426614174099",
                "thread_id": "123e4567-e89b-12d3-a456-426614174098"
            }
        }
    }
