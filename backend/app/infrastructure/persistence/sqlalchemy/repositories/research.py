"""
SQLAlchemy repository implementations for Research domain.

These repositories implement the abstract repository interfaces from the
domain layer, handling all database operations for research entities.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.domain.research.entities import ResearchRun, Finding, Hypothesis, Dossier
from app.domain.research.repositories.research_repository import (
    ResearchRunRepository,
    FindingRepository,
    HypothesisRepository,
    DossierRepository,
)
from ..models import (
    ResearchRunModel,
    FindingModel,
    HypothesisModel,
    DossierModel,
)
from ..mappers import (
    to_domain_research_run,
    to_model_research_run,
    to_domain_finding,
    to_model_finding,
    to_domain_hypothesis,
    to_model_hypothesis,
    to_domain_dossier,
    to_model_dossier,
)


class RepositoryException(Exception):
    """Base exception for repository operations."""
    pass


class SQLAlchemyResearchRunRepository(ResearchRunRepository):
    """SQLAlchemy implementation of ResearchRunRepository."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def get_by_id(self, id: UUID) -> Optional[ResearchRun]:
        """
        Get research run by ID.

        Args:
            id: Research run ID

        Returns:
            ResearchRun if found, None otherwise

        Raises:
            RepositoryException: If database error occurs
        """
        try:
            stmt = select(ResearchRunModel).where(ResearchRunModel.id == id)
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            return to_domain_research_run(model) if model else None
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to get research run {id}: {e}") from e

    async def find_by_case_id(self, case_id: UUID) -> List[ResearchRun]:
        """
        Find all research runs for a case.

        Args:
            case_id: Case ID

        Returns:
            List of research runs

        Raises:
            RepositoryException: If database error occurs
        """
        try:
            stmt = select(ResearchRunModel).where(
                ResearchRunModel.case_id == case_id
            ).order_by(ResearchRunModel.started_at.desc())
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_research_run(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find research runs for case {case_id}: {e}") from e

    async def find_by_status(self, status: str) -> List[ResearchRun]:
        """
        Find research runs by status.

        Args:
            status: Research status

        Returns:
            List of research runs

        Raises:
            RepositoryException: If database error occurs
        """
        try:
            stmt = select(ResearchRunModel).where(
                ResearchRunModel.status == status
            ).order_by(ResearchRunModel.started_at.desc())
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_research_run(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find research runs by status {status}: {e}") from e

    async def save(self, research_run: ResearchRun) -> ResearchRun:
        """
        Save or update a research run.

        Args:
            research_run: ResearchRun entity

        Returns:
            Saved research run

        Raises:
            RepositoryException: If database error occurs
        """
        try:
            # Check if exists
            existing = await self._session.get(ResearchRunModel, research_run.id)

            if existing:
                # Update existing
                existing.case_id = research_run.case_id
                existing.status = research_run.status.value
                existing.phase = research_run.phase.value
                existing.query = research_run.query
                existing.findings = [str(f) for f in research_run.findings]
                existing.config = research_run.config
                existing.started_at = research_run.started_at
                existing.completed_at = research_run.completed_at
                existing.dossier_path = research_run.dossier_path
                existing.metadata = research_run.metadata
                model = existing
            else:
                # Create new
                model = to_model_research_run(research_run)
                self._session.add(model)

            await self._session.flush()
            return to_domain_research_run(model)
        except IntegrityError as e:
            raise RepositoryException(f"Integrity error saving research run: {e}") from e
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to save research run: {e}") from e

    async def delete(self, id: UUID) -> bool:
        """
        Delete a research run.

        Args:
            id: Research run ID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryException: If database error occurs
        """
        try:
            stmt = delete(ResearchRunModel).where(ResearchRunModel.id == id)
            result = await self._session.execute(stmt)
            await self._session.flush()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to delete research run {id}: {e}") from e


class SQLAlchemyFindingRepository(FindingRepository):
    """SQLAlchemy implementation of FindingRepository."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def get_by_id(self, id: UUID) -> Optional[Finding]:
        """Get finding by ID."""
        try:
            stmt = select(FindingModel).where(FindingModel.id == id)
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            return to_domain_finding(model) if model else None
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to get finding {id}: {e}") from e

    async def find_by_research_run(self, research_run_id: UUID) -> List[Finding]:
        """Find all findings for a research run."""
        try:
            stmt = select(FindingModel).where(
                FindingModel.research_run_id == research_run_id
            ).order_by(FindingModel.confidence.desc())
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_finding(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find findings for research run {research_run_id}: {e}") from e

    async def find_by_type(
        self, research_run_id: UUID, finding_type: str
    ) -> List[Finding]:
        """Find findings by type."""
        try:
            stmt = select(FindingModel).where(
                and_(
                    FindingModel.research_run_id == research_run_id,
                    FindingModel.finding_type == finding_type,
                )
            ).order_by(FindingModel.confidence.desc())
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_finding(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find findings by type: {e}") from e

    async def find_by_confidence(
        self, research_run_id: UUID, min_confidence: float
    ) -> List[Finding]:
        """Find findings with confidence above threshold."""
        try:
            stmt = select(FindingModel).where(
                and_(
                    FindingModel.research_run_id == research_run_id,
                    FindingModel.confidence >= min_confidence,
                )
            ).order_by(FindingModel.confidence.desc())
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_finding(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find findings by confidence: {e}") from e

    async def find_by_tag(self, research_run_id: UUID, tag: str) -> List[Finding]:
        """Find findings with a specific tag."""
        try:
            # Use JSONB contains operator for tag search
            stmt = select(FindingModel).where(
                and_(
                    FindingModel.research_run_id == research_run_id,
                    FindingModel.tags.contains([tag]),
                )
            ).order_by(FindingModel.confidence.desc())
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_finding(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find findings by tag: {e}") from e

    async def save(self, finding: Finding) -> Finding:
        """Save or update a finding."""
        try:
            existing = await self._session.get(FindingModel, finding.id)

            if existing:
                # Update existing
                existing.research_run_id = finding.research_run_id
                existing.finding_type = finding.finding_type.value
                existing.text = finding.text
                existing.entities = [str(e) for e in finding.entities]
                existing.citations = [str(c) for c in finding.citations]
                existing.confidence = finding.confidence
                existing.relevance = finding.relevance
                existing.tags = finding.tags
                existing.metadata = finding.metadata
                model = existing
            else:
                # Create new
                model = to_model_finding(finding)
                self._session.add(model)

            await self._session.flush()
            return to_domain_finding(model)
        except IntegrityError as e:
            raise RepositoryException(f"Integrity error saving finding: {e}") from e
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to save finding: {e}") from e

    async def delete(self, id: UUID) -> bool:
        """Delete a finding."""
        try:
            stmt = delete(FindingModel).where(FindingModel.id == id)
            result = await self._session.execute(stmt)
            await self._session.flush()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to delete finding {id}: {e}") from e


class SQLAlchemyHypothesisRepository(HypothesisRepository):
    """SQLAlchemy implementation of HypothesisRepository."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def get_by_id(self, id: UUID) -> Optional[Hypothesis]:
        """Get hypothesis by ID."""
        try:
            stmt = select(HypothesisModel).where(HypothesisModel.id == id)
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            return to_domain_hypothesis(model) if model else None
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to get hypothesis {id}: {e}") from e

    async def find_by_research_run(self, research_run_id: UUID) -> List[Hypothesis]:
        """Find all hypotheses for a research run."""
        try:
            stmt = select(HypothesisModel).where(
                HypothesisModel.research_run_id == research_run_id
            ).order_by(HypothesisModel.confidence.desc())
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_hypothesis(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find hypotheses for research run {research_run_id}: {e}") from e

    async def find_by_confidence(
        self, research_run_id: UUID, min_confidence: float
    ) -> List[Hypothesis]:
        """Find hypotheses with confidence above threshold."""
        try:
            stmt = select(HypothesisModel).where(
                and_(
                    HypothesisModel.research_run_id == research_run_id,
                    HypothesisModel.confidence >= min_confidence,
                )
            ).order_by(HypothesisModel.confidence.desc())
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_hypothesis(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find hypotheses by confidence: {e}") from e

    async def save(self, hypothesis: Hypothesis) -> Hypothesis:
        """Save or update a hypothesis."""
        try:
            existing = await self._session.get(HypothesisModel, hypothesis.id)

            if existing:
                # Update existing
                existing.research_run_id = hypothesis.research_run_id
                existing.hypothesis_text = hypothesis.hypothesis_text
                existing.supporting_findings = [str(f) for f in hypothesis.supporting_findings]
                existing.contradicting_findings = [str(f) for f in hypothesis.contradicting_findings]
                existing.confidence = hypothesis.confidence
                existing.metadata = hypothesis.metadata
                model = existing
            else:
                # Create new
                model = to_model_hypothesis(hypothesis)
                self._session.add(model)

            await self._session.flush()
            return to_domain_hypothesis(model)
        except IntegrityError as e:
            raise RepositoryException(f"Integrity error saving hypothesis: {e}") from e
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to save hypothesis: {e}") from e

    async def delete(self, id: UUID) -> bool:
        """Delete a hypothesis."""
        try:
            stmt = delete(HypothesisModel).where(HypothesisModel.id == id)
            result = await self._session.execute(stmt)
            await self._session.flush()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to delete hypothesis {id}: {e}") from e


class SQLAlchemyDossierRepository(DossierRepository):
    """SQLAlchemy implementation of DossierRepository."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def get_by_id(self, id: UUID) -> Optional[Dossier]:
        """Get dossier by ID."""
        try:
            stmt = select(DossierModel).where(DossierModel.id == id)
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            return to_domain_dossier(model) if model else None
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to get dossier {id}: {e}") from e

    async def get_by_research_run(self, research_run_id: UUID) -> Optional[Dossier]:
        """Get dossier for a research run."""
        try:
            stmt = select(DossierModel).where(
                DossierModel.research_run_id == research_run_id
            )
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            return to_domain_dossier(model) if model else None
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to get dossier for research run {research_run_id}: {e}") from e

    async def save(self, dossier: Dossier) -> Dossier:
        """Save or update a dossier."""
        try:
            existing = await self._session.get(DossierModel, dossier.id)

            if existing:
                # Update existing
                existing.research_run_id = dossier.research_run_id
                existing.executive_summary = dossier.executive_summary
                existing.sections = [
                    {
                        "title": s.title,
                        "content": s.content,
                        "order": s.order,
                        "metadata": s.metadata,
                    }
                    for s in dossier.sections
                ]
                existing.citations_appendix = dossier.citations_appendix
                existing.generated_at = dossier.generated_at
                existing.metadata = dossier.metadata
                model = existing
            else:
                # Create new
                model = to_model_dossier(dossier)
                self._session.add(model)

            await self._session.flush()
            return to_domain_dossier(model)
        except IntegrityError as e:
            raise RepositoryException(f"Integrity error saving dossier: {e}") from e
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to save dossier: {e}") from e

    async def delete(self, id: UUID) -> bool:
        """Delete a dossier."""
        try:
            stmt = delete(DossierModel).where(DossierModel.id == id)
            result = await self._session.execute(stmt)
            await self._session.flush()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to delete dossier {id}: {e}") from e
