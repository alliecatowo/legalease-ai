"""Evidence domain repository interfaces."""

from .evidence_repository import (
    EvidenceRepository,
    DocumentRepository,
    TranscriptRepository,
    CommunicationRepository,
    ForensicReportRepository,
)

__all__ = [
    "EvidenceRepository",
    "DocumentRepository",
    "TranscriptRepository",
    "CommunicationRepository",
    "ForensicReportRepository",
]
