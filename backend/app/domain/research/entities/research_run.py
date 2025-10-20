"""
ResearchRun entity for the Research domain.

Represents an AI-powered deep research session analyzing case evidence
to discover patterns, generate hypotheses, and produce a comprehensive dossier.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID


class ResearchPhase(str, Enum):
    """Phase of the research process."""

    INITIALIZING = "INITIALIZING"
    INDEXING = "INDEXING"
    SEARCHING = "SEARCHING"
    ANALYZING = "ANALYZING"
    HYPOTHESIS_GENERATION = "HYPOTHESIS_GENERATION"
    DOSSIER_GENERATION = "DOSSIER_GENERATION"
    COMPLETED = "COMPLETED"


class ResearchStatus(str, Enum):
    """Overall status of the research run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class ResearchRun:
    """
    ResearchRun entity representing a deep research session.

    A research run orchestrates the entire AI-powered investigation process,
    from initial query through evidence analysis to final dossier generation.

    Attributes:
        id: Unique identifier for the research run
        case_id: ID of the case being researched
        status: Current overall status
        phase: Current processing phase
        query: Research query or objective
        findings: List of finding IDs discovered during research
        dossier_path: Path to generated dossier document
        started_at: When research started
        completed_at: When research completed
        config: Configuration parameters for the research
        metadata: Additional metadata and intermediate results

    Example:
        >>> from datetime import datetime
        >>> from uuid import uuid4
        >>>
        >>> research = ResearchRun(
        ...     id=uuid4(),
        ...     case_id=uuid4(),
        ...     status=ResearchStatus.RUNNING,
        ...     phase=ResearchPhase.ANALYZING,
        ...     query="Identify timeline of communications regarding contract negotiation",
        ...     findings=[],
        ...     config={"max_findings": 50, "min_confidence": 0.7},
        ... )
        >>> research.advance_to_hypothesis_generation()
        >>> research.phase
        <ResearchPhase.HYPOTHESIS_GENERATION: 'HYPOTHESIS_GENERATION'>
    """

    id: UUID
    case_id: UUID
    status: ResearchStatus
    phase: ResearchPhase
    query: str
    findings: List[UUID]
    config: Dict[str, Any]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dossier_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        """Mark research as started."""
        self.status = ResearchStatus.RUNNING
        self.phase = ResearchPhase.INITIALIZING
        self.started_at = datetime.utcnow()

    def advance_to_indexing(self) -> None:
        """Advance to indexing phase."""
        self.phase = ResearchPhase.INDEXING

    def advance_to_searching(self) -> None:
        """Advance to searching phase."""
        self.phase = ResearchPhase.SEARCHING

    def advance_to_analyzing(self) -> None:
        """Advance to analyzing phase."""
        self.phase = ResearchPhase.ANALYZING

    def advance_to_hypothesis_generation(self) -> None:
        """Advance to hypothesis generation phase."""
        self.phase = ResearchPhase.HYPOTHESIS_GENERATION

    def advance_to_dossier_generation(self) -> None:
        """Advance to dossier generation phase."""
        self.phase = ResearchPhase.DOSSIER_GENERATION

    def mark_completed(self, dossier_path: str) -> None:
        """
        Mark research as completed.

        Args:
            dossier_path: Path to the generated dossier
        """
        self.status = ResearchStatus.COMPLETED
        self.phase = ResearchPhase.COMPLETED
        self.completed_at = datetime.utcnow()
        self.dossier_path = dossier_path

    def mark_failed(self, error: str) -> None:
        """
        Mark research as failed.

        Args:
            error: Error message
        """
        self.status = ResearchStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.metadata["error"] = error

    def cancel(self) -> None:
        """Cancel the research run."""
        self.status = ResearchStatus.CANCELLED
        self.completed_at = datetime.utcnow()

    def add_finding(self, finding_id: UUID) -> None:
        """
        Add a finding to the research.

        Args:
            finding_id: ID of the finding to add
        """
        if finding_id not in self.findings:
            self.findings.append(finding_id)

    def get_duration(self) -> Optional[float]:
        """
        Get research duration in seconds.

        Returns:
            Duration in seconds, or None if not completed
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def is_running(self) -> bool:
        """Check if research is currently running."""
        return self.status == ResearchStatus.RUNNING

    def is_completed(self) -> bool:
        """Check if research is completed."""
        return self.status == ResearchStatus.COMPLETED

    def __eq__(self, other: object) -> bool:
        """Research runs are equal if they have the same ID."""
        if not isinstance(other, ResearchRun):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on research run ID."""
        return hash(self.id)
