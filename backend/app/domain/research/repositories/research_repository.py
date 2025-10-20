"""
Repository interfaces for Research domain.

Abstract interfaces for research persistence following hexagonal architecture.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..entities import ResearchRun, Finding, Hypothesis, Dossier


class ResearchRunRepository(ABC):
    """Repository interface for ResearchRun entities."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[ResearchRun]:
        """Get research run by ID."""
        pass

    @abstractmethod
    async def find_by_case_id(self, case_id: UUID) -> List[ResearchRun]:
        """Find all research runs for a case."""
        pass

    @abstractmethod
    async def find_by_status(self, status: str) -> List[ResearchRun]:
        """Find research runs by status."""
        pass

    @abstractmethod
    async def save(self, research_run: ResearchRun) -> ResearchRun:
        """Save or update a research run."""
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete a research run."""
        pass


class FindingRepository(ABC):
    """Repository interface for Finding entities."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Finding]:
        """Get finding by ID."""
        pass

    @abstractmethod
    async def find_by_research_run(self, research_run_id: UUID) -> List[Finding]:
        """Find all findings for a research run."""
        pass

    @abstractmethod
    async def find_by_type(
        self, research_run_id: UUID, finding_type: str
    ) -> List[Finding]:
        """Find findings by type."""
        pass

    @abstractmethod
    async def find_by_confidence(
        self, research_run_id: UUID, min_confidence: float
    ) -> List[Finding]:
        """Find findings with confidence above threshold."""
        pass

    @abstractmethod
    async def find_by_tag(self, research_run_id: UUID, tag: str) -> List[Finding]:
        """Find findings with a specific tag."""
        pass

    @abstractmethod
    async def save(self, finding: Finding) -> Finding:
        """Save or update a finding."""
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete a finding."""
        pass


class HypothesisRepository(ABC):
    """Repository interface for Hypothesis entities."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Hypothesis]:
        """Get hypothesis by ID."""
        pass

    @abstractmethod
    async def find_by_research_run(self, research_run_id: UUID) -> List[Hypothesis]:
        """Find all hypotheses for a research run."""
        pass

    @abstractmethod
    async def find_by_confidence(
        self, research_run_id: UUID, min_confidence: float
    ) -> List[Hypothesis]:
        """Find hypotheses with confidence above threshold."""
        pass

    @abstractmethod
    async def save(self, hypothesis: Hypothesis) -> Hypothesis:
        """Save or update a hypothesis."""
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete a hypothesis."""
        pass


class DossierRepository(ABC):
    """Repository interface for Dossier entities."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Dossier]:
        """Get dossier by ID."""
        pass

    @abstractmethod
    async def get_by_research_run(self, research_run_id: UUID) -> Optional[Dossier]:
        """Get dossier for a research run."""
        pass

    @abstractmethod
    async def save(self, dossier: Dossier) -> Dossier:
        """Save or update a dossier."""
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete a dossier."""
        pass
