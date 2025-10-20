"""
Repository interfaces for Evidence domain.

These are abstract interfaces (ports) that define how the domain
interacts with persistence, following hexagonal architecture.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..entities import Document, Transcript, Communication, ForensicReport


class EvidenceRepository(ABC):
    """Base repository interface for all evidence types."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[object]:
        """
        Retrieve evidence by ID.

        Args:
            id: Evidence ID

        Returns:
            Evidence entity or None if not found
        """
        pass

    @abstractmethod
    async def find_by_case_id(self, case_id: UUID) -> List[object]:
        """
        Find all evidence for a case.

        Args:
            case_id: Case ID

        Returns:
            List of evidence entities
        """
        pass

    @abstractmethod
    async def save(self, evidence: object) -> object:
        """
        Save or update evidence.

        Args:
            evidence: Evidence entity to save

        Returns:
            Saved evidence entity
        """
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """
        Delete evidence by ID.

        Args:
            id: Evidence ID

        Returns:
            True if deleted, False if not found
        """
        pass


class DocumentRepository(ABC):
    """Repository interface for Document entities."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Document]:
        """Get document by ID."""
        pass

    @abstractmethod
    async def find_by_case_id(self, case_id: UUID) -> List[Document]:
        """Find all documents for a case."""
        pass

    @abstractmethod
    async def find_by_status(self, case_id: UUID, status: str) -> List[Document]:
        """Find documents by processing status."""
        pass

    @abstractmethod
    async def save(self, document: Document) -> Document:
        """Save or update a document."""
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete a document."""
        pass

    @abstractmethod
    async def get_by_checksum(self, checksum: str) -> Optional[Document]:
        """Find document by checksum to detect duplicates."""
        pass


class TranscriptRepository(ABC):
    """Repository interface for Transcript entities."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Transcript]:
        """Get transcript by ID."""
        pass

    @abstractmethod
    async def find_by_case_id(self, case_id: UUID) -> List[Transcript]:
        """Find all transcripts for a case."""
        pass

    @abstractmethod
    async def find_by_speaker(self, case_id: UUID, speaker_id: str) -> List[Transcript]:
        """Find transcripts containing a specific speaker."""
        pass

    @abstractmethod
    async def save(self, transcript: Transcript) -> Transcript:
        """Save or update a transcript."""
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete a transcript."""
        pass


class CommunicationRepository(ABC):
    """Repository interface for Communication entities."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Communication]:
        """Get communication by ID."""
        pass

    @abstractmethod
    async def find_by_case_id(self, case_id: UUID) -> List[Communication]:
        """Find all communications for a case."""
        pass

    @abstractmethod
    async def find_by_thread(self, case_id: UUID, thread_id: str) -> List[Communication]:
        """Find all communications in a thread."""
        pass

    @abstractmethod
    async def find_by_participant(
        self, case_id: UUID, participant_id: str
    ) -> List[Communication]:
        """Find communications involving a participant."""
        pass

    @abstractmethod
    async def find_by_time_range(
        self, case_id: UUID, start: object, end: object
    ) -> List[Communication]:
        """Find communications within a time range."""
        pass

    @abstractmethod
    async def save(self, communication: Communication) -> Communication:
        """Save or update a communication."""
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete a communication."""
        pass


class ForensicReportRepository(ABC):
    """Repository interface for ForensicReport entities."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[ForensicReport]:
        """Get forensic report by ID."""
        pass

    @abstractmethod
    async def find_by_case_id(self, case_id: UUID) -> List[ForensicReport]:
        """Find all forensic reports for a case."""
        pass

    @abstractmethod
    async def find_by_device(self, device_id: str) -> List[ForensicReport]:
        """Find reports for a specific device."""
        pass

    @abstractmethod
    async def save(self, report: ForensicReport) -> ForensicReport:
        """Save or update a forensic report."""
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete a forensic report."""
        pass
