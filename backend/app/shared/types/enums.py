"""
Domain enumerations for the application.

This module defines all enums used across the domain layer to ensure
consistent values and type safety.

Example:
    >>> evidence = EvidenceType.DOCUMENT
    >>> assert evidence.value == "DOCUMENT"

    >>> phase = ResearchPhase.ANALYSIS
    >>> print(phase.description)
    Analyzing findings and identifying patterns
"""

from enum import Enum


class EvidenceType(str, Enum):
    """
    Types of evidence that can be processed in the system.

    Evidence types determine how content is processed, indexed,
    and presented in the legal case management system.
    """

    DOCUMENT = "DOCUMENT"
    """Written documents (PDFs, Word files, etc.)"""

    TRANSCRIPT = "TRANSCRIPT"
    """Audio/video transcriptions with speaker identification"""

    COMMUNICATION = "COMMUNICATION"
    """Emails, messages, correspondence"""

    FORENSIC_REPORT = "FORENSIC_REPORT"
    """Forensic analysis reports and exports"""

    IMAGE = "IMAGE"
    """Photographic evidence"""

    VIDEO = "VIDEO"
    """Video recordings"""

    @property
    def description(self) -> str:
        """Get human-readable description of the evidence type."""
        descriptions = {
            self.DOCUMENT: "Written documents and files",
            self.TRANSCRIPT: "Audio/video transcriptions",
            self.COMMUNICATION: "Emails and messages",
            self.FORENSIC_REPORT: "Forensic analysis reports",
            self.IMAGE: "Photographic evidence",
            self.VIDEO: "Video recordings",
        }
        return descriptions[self]


class ResearchPhase(str, Enum):
    """
    Phases of the deep research pipeline.

    Research progresses through these phases sequentially,
    from initial discovery to final synthesis.
    """

    DISCOVERY = "DISCOVERY"
    """Initial discovery of relevant information"""

    PLANNING = "PLANNING"
    """Planning research strategy and approach"""

    ANALYSIS = "ANALYSIS"
    """Analyzing findings and identifying patterns"""

    CORRELATION = "CORRELATION"
    """Correlating findings across sources"""

    SYNTHESIS = "SYNTHESIS"
    """Synthesizing final insights and conclusions"""

    COMPLETED = "COMPLETED"
    """Research successfully completed"""

    FAILED = "FAILED"
    """Research failed or was aborted"""

    @property
    def description(self) -> str:
        """Get human-readable description of the phase."""
        descriptions = {
            self.DISCOVERY: "Discovering relevant information",
            self.PLANNING: "Planning research strategy",
            self.ANALYSIS: "Analyzing findings and patterns",
            self.CORRELATION: "Correlating findings across sources",
            self.SYNTHESIS: "Synthesizing final insights",
            self.COMPLETED: "Research completed successfully",
            self.FAILED: "Research failed or aborted",
        }
        return descriptions[self]

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal phase (completed or failed)."""
        return self in (self.COMPLETED, self.FAILED)

    @property
    def progress_percentage(self) -> int:
        """Get approximate progress percentage for this phase."""
        progress_map = {
            self.DISCOVERY: 10,
            self.PLANNING: 25,
            self.ANALYSIS: 50,
            self.CORRELATION: 75,
            self.SYNTHESIS: 90,
            self.COMPLETED: 100,
            self.FAILED: 0,
        }
        return progress_map[self]


class ResearchStatus(str, Enum):
    """
    Status of a research run execution.

    This tracks the operational state of the research process,
    independent of which phase it's in.
    """

    PENDING = "PENDING"
    """Research queued but not started"""

    RUNNING = "RUNNING"
    """Research currently executing"""

    PAUSED = "PAUSED"
    """Research temporarily paused"""

    COMPLETED = "COMPLETED"
    """Research finished successfully"""

    FAILED = "FAILED"
    """Research failed with errors"""

    CANCELLED = "CANCELLED"
    """Research cancelled by user"""

    @property
    def description(self) -> str:
        """Get human-readable description of the status."""
        descriptions = {
            self.PENDING: "Waiting to start",
            self.RUNNING: "Currently running",
            self.PAUSED: "Temporarily paused",
            self.COMPLETED: "Completed successfully",
            self.FAILED: "Failed with errors",
            self.CANCELLED: "Cancelled by user",
        }
        return descriptions[self]

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal status."""
        return self in (self.COMPLETED, self.FAILED, self.CANCELLED)

    @property
    def is_active(self) -> bool:
        """Check if research is actively running."""
        return self == self.RUNNING


class FindingType(str, Enum):
    """
    Types of findings discovered during research.

    Findings are categorized to help with analysis and presentation.
    """

    FACT = "FACT"
    """Factual statement or data point"""

    QUOTE = "QUOTE"
    """Direct quotation from source"""

    OBSERVATION = "OBSERVATION"
    """Analytical observation or insight"""

    CONTRADICTION = "CONTRADICTION"
    """Contradiction or inconsistency found"""

    GAP = "GAP"
    """Information gap or missing evidence"""

    @property
    def description(self) -> str:
        """Get human-readable description of the finding type."""
        descriptions = {
            self.FACT: "Factual statement or data",
            self.QUOTE: "Direct quotation",
            self.OBSERVATION: "Analytical observation",
            self.CONTRADICTION: "Contradiction or inconsistency",
            self.GAP: "Information gap",
        }
        return descriptions[self]

    @property
    def icon(self) -> str:
        """Get icon representation for UI display."""
        icons = {
            self.FACT: "📊",
            self.QUOTE: "💬",
            self.OBSERVATION: "🔍",
            self.CONTRADICTION: "⚠️",
            self.GAP: "❓",
        }
        return icons[self]


class EntityType(str, Enum):
    """
    Types of entities extracted from documents.

    These align with standard NER (Named Entity Recognition)
    categories used in NLP processing.
    """

    PERSON = "PERSON"
    """Person name"""

    ORGANIZATION = "ORGANIZATION"
    """Organization or company name"""

    LOCATION = "LOCATION"
    """Geographic location"""

    DATE = "DATE"
    """Date or time reference"""

    MONEY = "MONEY"
    """Monetary amount"""

    OBJECT = "OBJECT"
    """Physical object or item"""

    CONCEPT = "CONCEPT"
    """Abstract concept or topic"""

    EVENT = "EVENT"
    """Event or occurrence"""

    LAW = "LAW"
    """Legal statute or regulation"""

    CASE = "CASE"
    """Legal case reference"""

    @property
    def description(self) -> str:
        """Get human-readable description of the entity type."""
        descriptions = {
            self.PERSON: "Person or individual",
            self.ORGANIZATION: "Organization or company",
            self.LOCATION: "Geographic location",
            self.DATE: "Date or time",
            self.MONEY: "Monetary amount",
            self.OBJECT: "Physical object",
            self.CONCEPT: "Abstract concept",
            self.EVENT: "Event or occurrence",
            self.LAW: "Legal statute or regulation",
            self.CASE: "Legal case reference",
        }
        return descriptions[self]


class RelationshipType(str, Enum):
    """
    Types of relationships between entities in the knowledge graph.

    These define how entities are connected and related to each other.
    """

    KNOWS = "KNOWS"
    """Person knows another person"""

    WORKS_FOR = "WORKS_FOR"
    """Person works for organization"""

    LOCATED_AT = "LOCATED_AT"
    """Entity located at location"""

    OWNS = "OWNS"
    """Entity owns another entity"""

    MENTIONED_IN = "MENTIONED_IN"
    """Entity mentioned in document"""

    PARTICIPATES_IN = "PARTICIPATES_IN"
    """Entity participates in event"""

    RELATED_TO = "RELATED_TO"
    """General relationship between entities"""

    PART_OF = "PART_OF"
    """Entity is part of another entity"""

    OCCURRED_ON = "OCCURRED_ON"
    """Event occurred on date"""

    INVOLVES = "INVOLVES"
    """Event involves entity"""

    @property
    def description(self) -> str:
        """Get human-readable description of the relationship type."""
        descriptions = {
            self.KNOWS: "Knows or is acquainted with",
            self.WORKS_FOR: "Works for or employed by",
            self.LOCATED_AT: "Located at or in",
            self.OWNS: "Owns or possesses",
            self.MENTIONED_IN: "Mentioned in document",
            self.PARTICIPATES_IN: "Participates in event",
            self.RELATED_TO: "Related to",
            self.PART_OF: "Part of or component of",
            self.OCCURRED_ON: "Occurred on date",
            self.INVOLVES: "Involves or includes",
        }
        return descriptions[self]


class ChunkType(str, Enum):
    """
    Types of text chunks used in document processing.

    Different chunk types serve different purposes in retrieval
    and analysis.
    """

    SUMMARY = "SUMMARY"
    """High-level summary of content"""

    SECTION = "SECTION"
    """Logical section or chapter"""

    MICROBLOCK = "MICROBLOCK"
    """Small semantic block (paragraph-level)"""

    SENTENCE = "SENTENCE"
    """Individual sentence"""

    @property
    def description(self) -> str:
        """Get human-readable description of the chunk type."""
        descriptions = {
            self.SUMMARY: "Document or section summary",
            self.SECTION: "Logical section or chapter",
            self.MICROBLOCK: "Semantic paragraph block",
            self.SENTENCE: "Individual sentence",
        }
        return descriptions[self]

    @property
    def typical_size(self) -> str:
        """Get typical size range for this chunk type."""
        sizes = {
            self.SUMMARY: "100-500 words",
            self.SECTION: "500-2000 words",
            self.MICROBLOCK: "50-200 words",
            self.SENTENCE: "10-50 words",
        }
        return sizes[self]


class ConfidenceLevel(str, Enum):
    """
    Confidence levels for ML/AI predictions and extractions.

    Used to indicate certainty in entity extraction, classifications,
    and other automated analysis.
    """

    VERY_LOW = "VERY_LOW"
    """Very low confidence (0-20%)"""

    LOW = "LOW"
    """Low confidence (20-40%)"""

    MEDIUM = "MEDIUM"
    """Medium confidence (40-60%)"""

    HIGH = "HIGH"
    """High confidence (60-80%)"""

    VERY_HIGH = "VERY_HIGH"
    """Very high confidence (80-100%)"""

    @property
    def description(self) -> str:
        """Get human-readable description of the confidence level."""
        descriptions = {
            self.VERY_LOW: "Very low confidence (0-20%)",
            self.LOW: "Low confidence (20-40%)",
            self.MEDIUM: "Medium confidence (40-60%)",
            self.HIGH: "High confidence (60-80%)",
            self.VERY_HIGH: "Very high confidence (80-100%)",
        }
        return descriptions[self]

    @property
    def min_score(self) -> float:
        """Get minimum score threshold for this level."""
        thresholds = {
            self.VERY_LOW: 0.0,
            self.LOW: 0.2,
            self.MEDIUM: 0.4,
            self.HIGH: 0.6,
            self.VERY_HIGH: 0.8,
        }
        return thresholds[self]

    @property
    def max_score(self) -> float:
        """Get maximum score threshold for this level."""
        thresholds = {
            self.VERY_LOW: 0.2,
            self.LOW: 0.4,
            self.MEDIUM: 0.6,
            self.HIGH: 0.8,
            self.VERY_HIGH: 1.0,
        }
        return thresholds[self]

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        """
        Convert a confidence score (0.0-1.0) to a ConfidenceLevel.

        Args:
            score: Confidence score between 0.0 and 1.0

        Returns:
            Corresponding ConfidenceLevel

        Raises:
            ValueError: If score is not in range [0.0, 1.0]

        Example:
            >>> ConfidenceLevel.from_score(0.85)
            <ConfidenceLevel.VERY_HIGH: 'VERY_HIGH'>
            >>> ConfidenceLevel.from_score(0.5)
            <ConfidenceLevel.MEDIUM: 'MEDIUM'>
        """
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {score}")

        if score >= 0.8:
            return cls.VERY_HIGH
        elif score >= 0.6:
            return cls.HIGH
        elif score >= 0.4:
            return cls.MEDIUM
        elif score >= 0.2:
            return cls.LOW
        else:
            return cls.VERY_LOW
