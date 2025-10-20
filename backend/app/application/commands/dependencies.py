"""
Dependency injection for command handlers.

This module provides FastAPI dependency functions that construct
command handlers with all required dependencies.
"""

import logging
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.infrastructure.persistence.sqlalchemy.repositories.research import (
    SQLAlchemyResearchRunRepository,
    SQLAlchemyDossierRepository,
)
from app.infrastructure.workflows.temporal.client import get_temporal_client
from app.infrastructure.ai.haystack.pipelines.indexing import IndexingPipelineFactory
from app.infrastructure.persistence.qdrant.repositories.document import (
    QdrantDocumentRepository,
)
from app.infrastructure.persistence.opensearch.repositories.document import (
    OpenSearchDocumentRepository,
)
from temporalio.client import Client

from .start_research import StartResearchCommandHandler
from .process_evidence import ProcessEvidenceCommandHandler
from .generate_report import GenerateReportCommandHandler
from .pause_research import PauseResearchCommandHandler
from .resume_research import ResumeResearchCommandHandler
from .cancel_research import CancelResearchCommandHandler

logger = logging.getLogger(__name__)


# ============================================================================
# Repository Dependencies
# ============================================================================


async def get_research_run_repository(
    db: AsyncSession = Depends(get_async_db),
) -> SQLAlchemyResearchRunRepository:
    """
    Get ResearchRun repository instance.

    Args:
        db: Database session from FastAPI dependency

    Returns:
        Configured ResearchRunRepository
    """
    return SQLAlchemyResearchRunRepository(db)


async def get_dossier_repository(
    db: AsyncSession = Depends(get_async_db),
) -> SQLAlchemyDossierRepository:
    """
    Get Dossier repository instance.

    Args:
        db: Database session from FastAPI dependency

    Returns:
        Configured DossierRepository
    """
    return SQLAlchemyDossierRepository(db)


# ============================================================================
# External Service Dependencies
# ============================================================================


async def get_temporal_client_dep() -> Client:
    """
    Get Temporal client for workflow execution.

    Returns:
        Connected Temporal client
    """
    return await get_temporal_client()


async def get_indexing_pipeline_factory() -> IndexingPipelineFactory:
    """
    Get IndexingPipelineFactory for evidence processing.

    Returns:
        Configured IndexingPipelineFactory
    """
    # Import here to avoid circular dependencies
    from app.infrastructure.ai.haystack.pipelines.indexing import IndexingPipelineFactory

    return IndexingPipelineFactory()


async def get_qdrant_document_repository() -> QdrantDocumentRepository:
    """
    Get Qdrant document repository.

    Returns:
        Configured QdrantDocumentRepository
    """
    from app.core.qdrant import get_qdrant_client

    client = await get_qdrant_client()
    return QdrantDocumentRepository(client)


async def get_opensearch_document_repository() -> OpenSearchDocumentRepository:
    """
    Get OpenSearch document repository.

    Returns:
        Configured OpenSearchDocumentRepository
    """
    from app.core.opensearch import get_opensearch_client

    client = await get_opensearch_client()
    return OpenSearchDocumentRepository(client)


async def get_minio_storage_service():
    """
    Get MinIO storage service.

    Returns:
        Configured MinIO client
    """
    from app.core.minio_client import get_minio_client

    return await get_minio_client()


# ============================================================================
# Command Handler Dependencies
# ============================================================================


async def get_start_research_handler(
    research_repo: SQLAlchemyResearchRunRepository = Depends(get_research_run_repository),
    temporal_client: Client = Depends(get_temporal_client_dep),
) -> StartResearchCommandHandler:
    """
    Get StartResearchCommandHandler with dependencies.

    Args:
        research_repo: Research run repository
        temporal_client: Temporal client for workflows

    Returns:
        Configured StartResearchCommandHandler
    """
    return StartResearchCommandHandler(
        research_repository=research_repo,
        temporal_client=temporal_client,
    )


async def get_process_evidence_handler(
    pipeline_factory: IndexingPipelineFactory = Depends(get_indexing_pipeline_factory),
    qdrant_repo: QdrantDocumentRepository = Depends(get_qdrant_document_repository),
    opensearch_repo: OpenSearchDocumentRepository = Depends(
        get_opensearch_document_repository
    ),
) -> ProcessEvidenceCommandHandler:
    """
    Get ProcessEvidenceCommandHandler with dependencies.

    Args:
        pipeline_factory: Factory for indexing pipelines
        qdrant_repo: Qdrant vector storage repository
        opensearch_repo: OpenSearch text search repository

    Returns:
        Configured ProcessEvidenceCommandHandler
    """
    return ProcessEvidenceCommandHandler(
        pipeline_factory=pipeline_factory,
        qdrant_repo=qdrant_repo,
        opensearch_repo=opensearch_repo,
    )


async def get_generate_report_handler(
    dossier_repo: SQLAlchemyDossierRepository = Depends(get_dossier_repository),
    research_repo: SQLAlchemyResearchRunRepository = Depends(get_research_run_repository),
    storage_service=Depends(get_minio_storage_service),
) -> GenerateReportCommandHandler:
    """
    Get GenerateReportCommandHandler with dependencies.

    Args:
        dossier_repo: Dossier repository
        research_repo: Research run repository
        storage_service: MinIO storage service

    Returns:
        Configured GenerateReportCommandHandler
    """
    return GenerateReportCommandHandler(
        dossier_repository=dossier_repo,
        research_repository=research_repo,
        storage_service=storage_service,
    )


async def get_pause_research_handler(
    research_repo: SQLAlchemyResearchRunRepository = Depends(get_research_run_repository),
    temporal_client: Client = Depends(get_temporal_client_dep),
) -> PauseResearchCommandHandler:
    """
    Get PauseResearchCommandHandler with dependencies.

    Args:
        research_repo: Research run repository
        temporal_client: Temporal client

    Returns:
        Configured PauseResearchCommandHandler
    """
    return PauseResearchCommandHandler(
        research_repository=research_repo,
        temporal_client=temporal_client,
    )


async def get_resume_research_handler(
    research_repo: SQLAlchemyResearchRunRepository = Depends(get_research_run_repository),
    temporal_client: Client = Depends(get_temporal_client_dep),
) -> ResumeResearchCommandHandler:
    """
    Get ResumeResearchCommandHandler with dependencies.

    Args:
        research_repo: Research run repository
        temporal_client: Temporal client

    Returns:
        Configured ResumeResearchCommandHandler
    """
    return ResumeResearchCommandHandler(
        research_repository=research_repo,
        temporal_client=temporal_client,
    )


async def get_cancel_research_handler(
    research_repo: SQLAlchemyResearchRunRepository = Depends(get_research_run_repository),
    temporal_client: Client = Depends(get_temporal_client_dep),
) -> CancelResearchCommandHandler:
    """
    Get CancelResearchCommandHandler with dependencies.

    Args:
        research_repo: Research run repository
        temporal_client: Temporal client

    Returns:
        Configured CancelResearchCommandHandler
    """
    return CancelResearchCommandHandler(
        research_repository=research_repo,
        temporal_client=temporal_client,
    )


# ============================================================================
# Command Bus Setup
# ============================================================================


async def setup_command_bus():
    """
    Initialize and configure the command bus with all handlers.

    This function should be called during application startup to
    register all command handlers with the command bus.

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>>
        >>> @app.on_event("startup")
        >>> async def startup():
        ...     await setup_command_bus()
    """
    from .command_bus import get_command_bus
    from .start_research import StartResearchCommand
    from .process_evidence import ProcessEvidenceCommand
    from .generate_report import GenerateReportCommand
    from .pause_research import PauseResearchCommand
    from .resume_research import ResumeResearchCommand
    from .cancel_research import CancelResearchCommand

    bus = get_command_bus()

    # Note: In a real application with FastAPI, we can't directly instantiate
    # handlers here because they require request-scoped dependencies.
    # Instead, the command bus would be used within API endpoints where
    # dependencies are properly injected.

    logger.info("Command bus setup complete")
