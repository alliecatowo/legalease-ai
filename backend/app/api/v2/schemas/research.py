"""
Pydantic schemas for research-related API requests and responses.

This module defines all data models for the API v2 research endpoints,
providing type safety, validation, and OpenAPI documentation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# ==================== Request Schemas ====================

class StartResearchRequest(BaseModel):
    """
    Request to start a new deep research workflow.

    Example:
        {
            "case_id": "01234567890123456789ab",
            "query": "Identify timeline of communications regarding contract negotiation",
            "defense_theory": "Client acted in good faith based on available information"
        }
    """

    case_id: str = Field(..., description="Case GID (22-char base62 string)")
    query: Optional[str] = Field(
        None,
        description="Specific research question or objective to investigate",
        example="Identify all communications between parties regarding the disputed contract"
    )
    defense_theory: Optional[str] = Field(
        None,
        description="Defense theory to support or challenge",
        example="Client acted in good faith based on incomplete information"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional configuration parameters for the research workflow"
    )


# ==================== Response Schemas ====================

class StartResearchResponse(BaseModel):
    """
    Response from starting a new research workflow.

    Contains the research run ID and URLs for monitoring progress.
    """

    research_run_id: str = Field(..., description="Unique identifier for this research run")
    workflow_id: str = Field(..., description="Temporal workflow ID for internal tracking")
    message: str = Field(..., description="Confirmation message")
    status_url: str = Field(..., description="URL to poll for research status")
    websocket_url: str = Field(..., description="WebSocket URL for real-time updates")

    class Config:
        json_schema_extra = {
            "example": {
                "research_run_id": "research_01234567890123456789",
                "workflow_id": "deep-research-01234567890123456789",
                "message": "Research workflow started successfully",
                "status_url": "/api/v2/research/research_01234567890123456789/status",
                "websocket_url": "/api/v2/research/research_01234567890123456789/stream"
            }
        }


class ResearchStatus(str, Enum):
    """Research run status enum."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ResearchPhase(str, Enum):
    """Research workflow phase enum."""

    INITIALIZING = "INITIALIZING"
    DISCOVERY = "DISCOVERY"
    PLANNING = "PLANNING"
    DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"
    TRANSCRIPT_ANALYSIS = "TRANSCRIPT_ANALYSIS"
    COMMUNICATION_ANALYSIS = "COMMUNICATION_ANALYSIS"
    CORRELATION = "CORRELATION"
    SYNTHESIS = "SYNTHESIS"
    REPORT_GENERATION = "REPORT_GENERATION"
    COMPLETED = "COMPLETED"


class ResearchStatusResponse(BaseModel):
    """
    Current status of a research run.

    Provides detailed information about workflow progress, findings, and timing.
    """

    research_run_id: str = Field(..., description="Unique identifier for this research run")
    case_id: str = Field(..., description="Case GID being researched")
    workflow_id: str = Field(..., description="Temporal workflow ID")
    status: ResearchStatus = Field(..., description="Overall research status")
    phase: ResearchPhase = Field(..., description="Current processing phase")
    progress_pct: float = Field(..., ge=0.0, le=100.0, description="Progress percentage (0-100)")
    query: Optional[str] = Field(None, description="Research query if provided")
    defense_theory: Optional[str] = Field(None, description="Defense theory if provided")
    findings_count: int = Field(0, description="Number of findings discovered so far")
    citations_count: int = Field(0, description="Number of citations collected")
    current_activity: Optional[str] = Field(None, description="Current activity being executed")
    is_paused: bool = Field(False, description="Whether the workflow is paused")
    started_at: Optional[datetime] = Field(None, description="When research started")
    completed_at: Optional[datetime] = Field(None, description="When research completed")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")

    class Config:
        json_schema_extra = {
            "example": {
                "research_run_id": "research_01234567890123456789",
                "case_id": "01234567890123456789ab",
                "workflow_id": "deep-research-01234567890123456789",
                "status": "RUNNING",
                "phase": "DOCUMENT_ANALYSIS",
                "progress_pct": 45.0,
                "query": "Identify timeline of communications",
                "defense_theory": None,
                "findings_count": 23,
                "citations_count": 67,
                "current_activity": "run_document_analysis",
                "is_paused": False,
                "started_at": "2024-01-15T10:30:00Z",
                "completed_at": None,
                "estimated_completion": "2024-01-15T12:00:00Z",
                "errors": []
            }
        }


class ActionResponse(BaseModel):
    """Response from an action (pause, resume, cancel)."""

    research_run_id: str = Field(..., description="Research run ID")
    action: str = Field(..., description="Action performed (pause, resume, cancel)")
    status: str = Field(..., description="New status after action")
    message: str = Field(..., description="Confirmation message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When action was performed")


# ==================== Findings Schemas ====================

class FindingType(str, Enum):
    """Type of research finding."""

    FACT = "FACT"
    PATTERN = "PATTERN"
    ANOMALY = "ANOMALY"
    RELATIONSHIP = "RELATIONSHIP"
    TIMELINE_EVENT = "TIMELINE_EVENT"
    CONTRADICTION = "CONTRADICTION"
    CORROBORATION = "CORROBORATION"
    GAP = "GAP"


class EntityReference(BaseModel):
    """Reference to an entity mentioned in a finding."""

    id: str = Field(..., description="Entity ID")
    type: str = Field(..., description="Entity type (person, organization, location, etc.)")
    name: str = Field(..., description="Entity name")


class CitationReference(BaseModel):
    """Reference to a citation supporting a finding."""

    id: str = Field(..., description="Citation ID")
    evidence_id: str = Field(..., description="ID of source evidence")
    evidence_type: str = Field(..., description="Type of evidence (document, transcript, etc.)")
    excerpt: str = Field(..., description="Relevant excerpt from evidence")
    locator: str = Field(..., description="Human-readable locator (e.g., 'Page 5, para 3')")
    page_number: Optional[int] = Field(None, description="Page number if applicable")
    timestamp: Optional[str] = Field(None, description="Timestamp if applicable (for transcripts)")


class FindingResponse(BaseModel):
    """A single research finding with supporting citations."""

    id: str = Field(..., description="Finding ID")
    finding_type: FindingType = Field(..., description="Type of finding")
    text: str = Field(..., description="Human-readable description of the finding")
    significance: Optional[str] = Field(None, description="Why this finding matters")
    entities: List[EntityReference] = Field(default_factory=list, description="Entities referenced in this finding")
    citations: List[CitationReference] = Field(default_factory=list, description="Citations supporting this finding")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Relevance to research query (0.0-1.0)")
    tags: List[str] = Field(default_factory=list, description="Categorical tags for organization")
    created_at: datetime = Field(..., description="When the finding was discovered")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class FindingsResponse(BaseModel):
    """Paginated list of research findings."""

    findings: List[FindingResponse] = Field(..., description="List of findings")
    total: int = Field(..., description="Total number of findings matching filters")
    limit: int = Field(..., description="Maximum findings per page")
    offset: int = Field(..., description="Offset for pagination")

    class Config:
        json_schema_extra = {
            "example": {
                "findings": [
                    {
                        "id": "finding_abc123",
                        "finding_type": "FACT",
                        "text": "John Doe signed the contract on 2024-03-15 at 2:30 PM",
                        "significance": "Establishes timeline of contract execution",
                        "entities": [
                            {"id": "person_123", "type": "person", "name": "John Doe"}
                        ],
                        "citations": [
                            {
                                "id": "citation_xyz",
                                "evidence_id": "doc_456",
                                "evidence_type": "document",
                                "excerpt": "Signed by John Doe on March 15, 2024 at 14:30",
                                "locator": "Page 5, paragraph 3",
                                "page_number": 5,
                                "timestamp": None
                            }
                        ],
                        "confidence": 0.95,
                        "relevance": 0.88,
                        "tags": ["contract", "signature", "timeline"],
                        "created_at": "2024-01-15T11:23:45Z",
                        "metadata": {}
                    }
                ],
                "total": 47,
                "limit": 100,
                "offset": 0
            }
        }


# ==================== Dossier Schemas ====================

class DossierSectionResponse(BaseModel):
    """A section in the research dossier."""

    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content (markdown formatted)")
    subsections: List['DossierSectionResponse'] = Field(default_factory=list, description="Nested subsections")
    findings_count: int = Field(0, description="Number of findings in this section")


class DossierResponse(BaseModel):
    """Complete research dossier."""

    research_run_id: str = Field(..., description="Research run ID")
    case_id: str = Field(..., description="Case GID")
    title: str = Field(..., description="Dossier title")
    executive_summary: str = Field(..., description="Executive summary of findings")
    sections: List[DossierSectionResponse] = Field(..., description="Dossier sections")
    findings_count: int = Field(..., description="Total findings included")
    citations_count: int = Field(..., description="Total citations included")
    contradictions_count: int = Field(0, description="Number of contradictions detected")
    timeline_events_count: int = Field(0, description="Number of timeline events")
    generated_at: datetime = Field(..., description="When the dossier was generated")
    file_path: Optional[str] = Field(None, description="Path to downloadable dossier file")

    class Config:
        json_schema_extra = {
            "example": {
                "research_run_id": "research_01234567890123456789",
                "case_id": "01234567890123456789ab",
                "title": "Deep Research Dossier: Contract Dispute Analysis",
                "executive_summary": "This research identified 47 key findings...",
                "sections": [
                    {
                        "title": "Timeline of Events",
                        "content": "The following timeline was reconstructed...",
                        "subsections": [],
                        "findings_count": 12
                    }
                ],
                "findings_count": 47,
                "citations_count": 128,
                "contradictions_count": 3,
                "timeline_events_count": 15,
                "generated_at": "2024-01-15T12:30:00Z",
                "file_path": "/dossiers/research_01234567890123456789.pdf"
            }
        }


# ==================== List Schemas ====================

class ResearchRunListItem(BaseModel):
    """Summary item for research run list."""

    research_run_id: str = Field(..., description="Research run ID")
    case_id: str = Field(..., description="Case GID")
    status: ResearchStatus = Field(..., description="Current status")
    phase: ResearchPhase = Field(..., description="Current phase")
    query: Optional[str] = Field(None, description="Research query if provided")
    findings_count: int = Field(0, description="Number of findings")
    started_at: datetime = Field(..., description="When research started")
    completed_at: Optional[datetime] = Field(None, description="When research completed")


class ResearchRunListResponse(BaseModel):
    """Paginated list of research runs for a case."""

    research_runs: List[ResearchRunListItem] = Field(..., description="List of research runs")
    total: int = Field(..., description="Total number of research runs for this case")
    limit: int = Field(..., description="Maximum items per page")
    offset: int = Field(..., description="Offset for pagination")


# Enable forward references for recursive models
DossierSectionResponse.model_rebuild()
