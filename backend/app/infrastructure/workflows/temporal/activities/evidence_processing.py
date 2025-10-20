"""
Temporal activities for evidence processing workflows.

These activities handle the discovery, indexing, and planning phases
of the deep research workflow. They interact with the database and
invoke LangGraph agents for AI-powered analysis.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import UUID

from temporalio import activity
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.workflows.temporal.models import (
    ResearchWorkflowInput,
    DiscoveryResult,
    PlanningResult,
    CaseMap,
    EvidenceItem,
    SearchStrategy,
)
from app.domain.research.entities.research_run import (
    ResearchRun,
    ResearchStatus,
    ResearchPhase,
)
from app.core.database import AsyncSessionLocal


logger = logging.getLogger(__name__)


# ==================== Helper Functions ====================

async def get_db_session() -> AsyncSession:
    """Get a database session for activity use."""
    async with AsyncSessionLocal() as session:
        return session


async def get_research_run(session: AsyncSession, research_run_id: str) -> ResearchRun:
    """
    Fetch a research run from the database.

    Args:
        session: Database session
        research_run_id: Research run ID

    Returns:
        ResearchRun entity

    Raises:
        ValueError: If research run not found
    """
    from app.infrastructure.persistence.sqlalchemy.models.research import (
        ResearchRunModel,
    )

    result = await session.execute(
        select(ResearchRunModel).where(ResearchRunModel.id == UUID(research_run_id))
    )
    model = result.scalar_one_or_none()

    if not model:
        raise ValueError(f"Research run {research_run_id} not found")

    # Convert SQLAlchemy model to domain entity
    return ResearchRun(
        id=model.id,
        case_id=model.case_id,
        status=ResearchStatus(model.status),
        phase=ResearchPhase(model.phase),
        query=model.query or "",
        findings=model.findings or [],
        config=model.config or {},
        started_at=model.started_at,
        completed_at=model.completed_at,
        dossier_path=model.dossier_path,
        metadata=model.metadata or {},
    )


async def save_research_run(session: AsyncSession, research_run: ResearchRun) -> None:
    """
    Save a research run to the database.

    Args:
        session: Database session
        research_run: ResearchRun entity to save
    """
    from app.infrastructure.persistence.sqlalchemy.models.research import (
        ResearchRunModel,
    )

    result = await session.execute(
        select(ResearchRunModel).where(ResearchRunModel.id == research_run.id)
    )
    model = result.scalar_one_or_none()

    if model:
        # Update existing
        model.status = research_run.status.value
        model.phase = research_run.phase.value
        model.query = research_run.query
        model.findings = research_run.findings
        model.config = research_run.config
        model.started_at = research_run.started_at
        model.completed_at = research_run.completed_at
        model.dossier_path = research_run.dossier_path
        model.metadata = research_run.metadata
    else:
        # Create new
        model = ResearchRunModel(
            id=research_run.id,
            case_id=research_run.case_id,
            status=research_run.status.value,
            phase=research_run.phase.value,
            query=research_run.query,
            findings=research_run.findings,
            config=research_run.config,
            started_at=research_run.started_at,
            completed_at=research_run.completed_at,
            dossier_path=research_run.dossier_path,
            metadata=research_run.metadata,
        )
        session.add(model)

    await session.commit()


# ==================== Activities ====================

@activity.defn(name="initialize_research_run")
async def initialize_research_run(input: ResearchWorkflowInput) -> str:
    """
    Initialize a research run in the database.

    Creates the ResearchRun record and sets initial status.

    Args:
        input: Workflow input parameters

    Returns:
        Research run ID

    Raises:
        ValueError: If case not found or research run already exists
    """
    logger.info(f"Initializing research run {input.research_run_id} for case {input.case_id}")

    async with AsyncSessionLocal() as session:
        # Create ResearchRun entity
        research_run = ResearchRun(
            id=UUID(input.research_run_id),
            case_id=UUID(input.case_id),
            status=ResearchStatus.PENDING,
            phase=ResearchPhase.INITIALIZING,
            query=input.query or "",
            findings=[],
            config=input.config,
            metadata={
                "defense_theory": input.defense_theory,
                "workflow_started_at": datetime.utcnow().isoformat(),
            },
        )

        # Start the research run
        research_run.start()

        # Save to database
        await save_research_run(session, research_run)

    logger.info(f"Research run {input.research_run_id} initialized successfully")
    return input.research_run_id


@activity.defn(name="run_discovery_phase")
async def run_discovery_phase(input: ResearchWorkflowInput) -> DiscoveryResult:
    """
    Execute the discovery/case cartography phase.

    Inventories all evidence in the case and generates a case map.
    This phase uses a LangGraph agent to analyze available evidence
    and recommend search strategies.

    Args:
        input: Workflow input parameters

    Returns:
        DiscoveryResult with case map and recommendations

    Raises:
        ValueError: If case not found
    """
    logger.info(f"Starting discovery phase for research run {input.research_run_id}")

    async with AsyncSessionLocal() as session:
        # Update research run phase
        research_run = await get_research_run(session, input.research_run_id)
        research_run.advance_to_indexing()
        await save_research_run(session, research_run)

        # Inventory all evidence in the case
        from app.models.document import Document
        from app.models.transcription import Transcription
        from app.models.forensic_export import ForensicExport

        # Send heartbeat periodically
        activity.heartbeat("Inventorying documents")

        # Get documents
        result = await session.execute(
            select(Document).where(Document.case_id == UUID(input.case_id))
        )
        documents = result.scalars().all()

        # Get transcripts
        activity.heartbeat("Inventorying transcripts")
        result = await session.execute(
            select(Transcription).where(Transcription.case_id == UUID(input.case_id))
        )
        transcripts = result.scalars().all()

        # Get forensic exports (communications)
        activity.heartbeat("Inventorying communications")
        result = await session.execute(
            select(ForensicExport).where(ForensicExport.case_id == UUID(input.case_id))
        )
        forensic_exports = result.scalars().all()

        # Build case map
        case_map = CaseMap(
            documents=[
                EvidenceItem(
                    id=str(doc.id),
                    type="document",
                    title=doc.filename,
                    source_path=doc.minio_path,
                    chunk_count=0,  # TODO: Get from chunks table
                    metadata={
                        "file_type": doc.file_type,
                        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                    },
                )
                for doc in documents
            ],
            transcripts=[
                EvidenceItem(
                    id=str(trans.id),
                    type="transcript",
                    title=trans.original_filename,
                    source_path=trans.audio_minio_path,
                    chunk_count=0,  # TODO: Get from chunks table
                    metadata={
                        "duration_seconds": trans.duration_seconds,
                        "speaker_count": trans.num_speakers,
                        "has_diarization": trans.diarization_enabled,
                    },
                )
                for trans in transcripts
            ],
            communications=[
                EvidenceItem(
                    id=str(export.id),
                    type="communication",
                    title=export.filename,
                    source_path=export.minio_path,
                    chunk_count=0,  # TODO: Get from chunks table
                    metadata={
                        "message_count": export.total_messages,
                        "date_range": export.date_range,
                        "source_platform": export.export_source,
                    },
                )
                for export in forensic_exports
            ],
            total_chunks=0,  # TODO: Sum all chunks
            indexed_at=datetime.utcnow(),
        )

        # Send heartbeat with progress
        activity.heartbeat(
            f"Inventoried {len(case_map.documents)} documents, "
            f"{len(case_map.transcripts)} transcripts, "
            f"{len(case_map.communications)} communications"
        )

        # TODO: Invoke LangGraph discovery agent to analyze case map
        # and generate recommendations
        # For now, provide basic recommendations
        discovery_summary = (
            f"Case contains {len(case_map.documents)} documents, "
            f"{len(case_map.transcripts)} transcripts, and "
            f"{len(case_map.communications)} communication exports. "
            f"Ready for deep research analysis."
        )

        recommended_strategies = [
            "Search documents for factual evidence and legal precedents",
            "Analyze transcripts for witness statements and admissions",
            "Review communications for timeline and relationship mapping",
        ]

        # Update research run metadata
        research_run.metadata["case_map"] = case_map.model_dump()
        research_run.metadata["discovery_summary"] = discovery_summary
        await save_research_run(session, research_run)

    logger.info(f"Discovery phase complete for research run {input.research_run_id}")

    return DiscoveryResult(
        research_run_id=input.research_run_id,
        case_id=input.case_id,
        case_map=case_map,
        discovery_summary=discovery_summary,
        recommended_search_strategies=recommended_strategies,
        completed_at=datetime.utcnow(),
    )


@activity.defn(name="run_planning_phase")
async def run_planning_phase(discovery: DiscoveryResult) -> PlanningResult:
    """
    Execute the planning phase.

    Analyzes the case map and research query to generate specific
    search strategies for each evidence type. Uses LangGraph planner agent.

    Args:
        discovery: Results from discovery phase

    Returns:
        PlanningResult with search strategies

    Raises:
        ValueError: If research run not found
    """
    logger.info(f"Starting planning phase for research run {discovery.research_run_id}")

    async with AsyncSessionLocal() as session:
        # Update research run phase
        research_run = await get_research_run(session, discovery.research_run_id)
        research_run.advance_to_searching()
        await save_research_run(session, research_run)

        # TODO: Invoke LangGraph planner agent to generate search strategies
        # For now, create basic strategies based on available evidence

        search_strategies: List[SearchStrategy] = []

        if discovery.case_map.documents:
            activity.heartbeat("Planning document search strategy")
            search_strategies.append(
                SearchStrategy(
                    evidence_type="document",
                    queries=[
                        research_run.query or "Find relevant factual evidence",
                        "Identify key legal arguments and precedents",
                        "Locate contracts, agreements, and formal communications",
                    ],
                    focus_areas=["facts", "legal precedents", "contracts"],
                    expected_finding_count=min(50, len(discovery.case_map.documents) * 5),
                )
            )

        if discovery.case_map.transcripts:
            activity.heartbeat("Planning transcript search strategy")
            search_strategies.append(
                SearchStrategy(
                    evidence_type="transcript",
                    queries=[
                        "Identify witness statements and testimonies",
                        "Find admissions, contradictions, or impeachment material",
                        "Locate discussions of key events and timeline markers",
                    ],
                    focus_areas=["statements", "admissions", "timeline"],
                    expected_finding_count=min(50, len(discovery.case_map.transcripts) * 10),
                )
            )

        if discovery.case_map.communications:
            activity.heartbeat("Planning communication search strategy")
            search_strategies.append(
                SearchStrategy(
                    evidence_type="communication",
                    queries=[
                        "Map communication patterns and relationships",
                        "Build timeline of key events and discussions",
                        "Identify inconsistencies or suspicious communications",
                    ],
                    focus_areas=["timeline", "relationships", "patterns"],
                    expected_finding_count=min(100, len(discovery.case_map.communications) * 20),
                )
            )

        # Estimate duration based on evidence volume
        total_evidence = (
            len(discovery.case_map.documents)
            + len(discovery.case_map.transcripts)
            + len(discovery.case_map.communications)
        )
        estimated_minutes = max(30, min(240, total_evidence * 2))

        # Update research run metadata
        research_run.metadata["search_strategies"] = [s.model_dump() for s in search_strategies]
        research_run.metadata["estimated_duration_minutes"] = estimated_minutes
        await save_research_run(session, research_run)

    logger.info(
        f"Planning phase complete for research run {discovery.research_run_id}, "
        f"generated {len(search_strategies)} search strategies"
    )

    return PlanningResult(
        research_run_id=discovery.research_run_id,
        case_id=discovery.case_id,
        query=research_run.query,
        defense_theory=research_run.metadata.get("defense_theory"),
        search_strategies=search_strategies,
        has_documents=len(discovery.case_map.documents) > 0,
        has_transcripts=len(discovery.case_map.transcripts) > 0,
        has_communications=len(discovery.case_map.communications) > 0,
        estimated_duration_minutes=estimated_minutes,
        completed_at=datetime.utcnow(),
    )
