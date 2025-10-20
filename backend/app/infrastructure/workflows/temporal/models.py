"""
Temporal workflow data models.

Pydantic models for all workflow inputs, outputs, and intermediate results.
These models define the contracts between workflow phases and activities.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# ==================== Workflow Inputs/Outputs ====================

class ResearchWorkflowInput(BaseModel):
    """Input parameters for starting a deep research workflow."""

    research_run_id: str = Field(..., description="Unique ID for this research run")
    case_id: str = Field(..., description="UUID of the case being researched")
    query: Optional[str] = Field(None, description="Optional research query or objective")
    defense_theory: Optional[str] = Field(None, description="Optional defense theory to investigate")
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration parameters for the research"
    )


class ResearchWorkflowOutput(BaseModel):
    """Output from a completed deep research workflow."""

    research_run_id: str
    status: str = Field(..., description="Final status: COMPLETED, FAILED, or CANCELLED")
    dossier_path: Optional[str] = Field(None, description="Path to generated dossier document")
    findings_count: int = Field(0, description="Number of findings discovered")
    citations_count: int = Field(0, description="Number of citations included")
    error: Optional[str] = Field(None, description="Error message if failed")
    duration_seconds: Optional[float] = Field(None, description="Total workflow duration")


# ==================== Phase Results ====================

class EvidenceItem(BaseModel):
    """Metadata about a piece of evidence in the case."""

    id: str
    type: str = Field(..., description="document, transcript, communication, or forensic_report")
    title: str
    source_path: Optional[str] = None
    chunk_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CaseMap(BaseModel):
    """Map of all evidence in the case."""

    documents: List[EvidenceItem] = Field(default_factory=list)
    transcripts: List[EvidenceItem] = Field(default_factory=list)
    communications: List[EvidenceItem] = Field(default_factory=list)
    forensic_reports: List[EvidenceItem] = Field(default_factory=list)
    total_chunks: int = 0
    indexed_at: Optional[datetime] = None


class DiscoveryResult(BaseModel):
    """Result from the discovery/case cartography phase."""

    research_run_id: str
    case_id: str
    case_map: CaseMap
    discovery_summary: str = Field(..., description="AI-generated summary of available evidence")
    recommended_search_strategies: List[str] = Field(
        default_factory=list,
        description="AI-recommended search approaches"
    )
    completed_at: datetime


class SearchStrategy(BaseModel):
    """A search strategy for a specific evidence type."""

    evidence_type: str = Field(..., description="document, transcript, or communication")
    queries: List[str] = Field(..., description="Search queries to execute")
    focus_areas: List[str] = Field(default_factory=list, description="Areas to focus on")
    expected_finding_count: int = Field(10, description="Expected number of findings")


class PlanningResult(BaseModel):
    """Result from the planning phase."""

    research_run_id: str
    case_id: str
    query: Optional[str]
    defense_theory: Optional[str]
    search_strategies: List[SearchStrategy]
    has_documents: bool = False
    has_transcripts: bool = False
    has_communications: bool = False
    estimated_duration_minutes: int = Field(30, description="Estimated time to complete")
    completed_at: datetime


class Finding(BaseModel):
    """A single research finding."""

    id: str
    finding_type: str = Field(..., description="fact, pattern, contradiction, timeline_event")
    content: str = Field(..., description="The actual finding content")
    significance: str = Field(..., description="Why this finding matters")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    source_evidence_ids: List[str] = Field(default_factory=list)
    citation_ids: List[str] = Field(default_factory=list)
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    """A citation to evidence supporting a finding."""

    id: str
    evidence_id: str = Field(..., description="ID of source evidence")
    evidence_type: str = Field(..., description="Type of evidence")
    chunk_id: Optional[str] = None
    excerpt: str = Field(..., description="Relevant excerpt from evidence")
    page_number: Optional[int] = None
    timestamp: Optional[str] = None
    locator: str = Field(..., description="Human-readable locator (e.g., 'Page 5, para 3')")


class DocumentAnalysisResult(BaseModel):
    """Result from document analysis activity."""

    research_run_id: str
    findings: List[Finding] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    documents_analyzed: int = 0
    chunks_analyzed: int = 0
    completed_at: datetime


class TranscriptAnalysisResult(BaseModel):
    """Result from transcript analysis activity."""

    research_run_id: str
    findings: List[Finding] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    transcripts_analyzed: int = 0
    chunks_analyzed: int = 0
    completed_at: datetime


class CommunicationAnalysisResult(BaseModel):
    """Result from communication analysis activity."""

    research_run_id: str
    findings: List[Finding] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    communications_analyzed: int = 0
    chunks_analyzed: int = 0
    completed_at: datetime


class KnowledgeGraphNode(BaseModel):
    """A node in the knowledge graph."""

    id: str
    type: str = Field(..., description="person, organization, event, document, concept")
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphRelationship(BaseModel):
    """A relationship in the knowledge graph."""

    id: str
    source_id: str
    target_id: str
    type: str = Field(..., description="mentioned_in, contradicts, supports, related_to")
    properties: Dict[str, Any] = Field(default_factory=dict)


class TimelineEvent(BaseModel):
    """An event in the case timeline."""

    id: str
    timestamp: datetime
    event_type: str = Field(..., description="communication, filing, meeting, transaction")
    description: str
    participants: List[str] = Field(default_factory=list)
    source_evidence_ids: List[str] = Field(default_factory=list)
    significance: str


class Contradiction(BaseModel):
    """A detected contradiction between pieces of evidence."""

    id: str
    description: str
    evidence_a_id: str
    evidence_b_id: str
    contradiction_type: str = Field(..., description="factual, timeline, attribution")
    severity: str = Field(..., description="low, medium, high, critical")
    resolution_notes: Optional[str] = None


class CorrelationResult(BaseModel):
    """Result from correlation phase."""

    research_run_id: str
    all_findings: List[Finding]
    all_citations: List[Citation]
    knowledge_graph_nodes: List[KnowledgeGraphNode]
    knowledge_graph_relationships: List[KnowledgeGraphRelationship]
    timeline: List[TimelineEvent]
    contradictions: List[Contradiction]
    key_patterns: List[str] = Field(default_factory=list, description="Detected patterns")
    completed_at: datetime


class DossierSection(BaseModel):
    """A section in the final dossier."""

    title: str
    content: str
    subsections: List['DossierSection'] = Field(default_factory=list)
    findings: List[str] = Field(default_factory=list, description="Finding IDs in this section")


class Dossier(BaseModel):
    """The final research dossier."""

    research_run_id: str
    case_id: str
    title: str
    executive_summary: str
    sections: List[DossierSection]
    findings: List[Finding]
    citations: List[Citation]
    timeline: List[TimelineEvent]
    contradictions: List[Contradiction]
    appendices: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==================== Activity Progress Updates ====================

class ActivityProgress(BaseModel):
    """Progress update from a long-running activity."""

    activity_name: str
    phase: str
    progress_pct: float = Field(..., ge=0.0, le=100.0)
    current_operation: str
    items_processed: int = 0
    items_total: int = 0
    findings_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ==================== Workflow Status ====================

class WorkflowPhase(str, Enum):
    """Current phase of the workflow."""

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
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowStatus(BaseModel):
    """Current status of a workflow execution."""

    research_run_id: str
    phase: WorkflowPhase
    progress_pct: float = Field(0.0, ge=0.0, le=100.0)
    current_activity: Optional[str] = None
    findings_count: int = 0
    citations_count: int = 0
    is_paused: bool = False
    is_cancelled: bool = False
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
