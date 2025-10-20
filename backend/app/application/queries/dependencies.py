"""
Dependency injection setup for query handlers.

Configures the QueryBus with all query handlers and their dependencies.
"""

import logging
from typing import Any

from app.application.queries.query_bus import QueryBus, LoggingMiddleware, ValidationMiddleware
from app.application.queries.search_evidence import (
    SearchEvidenceQuery,
    SearchEvidenceQueryHandler,
)
from app.application.queries.get_findings import (
    GetFindingsQuery,
    GetFindingsQueryHandler,
)
from app.application.queries.get_research_status import (
    GetResearchStatusQuery,
    GetResearchStatusQueryHandler,
)
from app.application.queries.query_graph import (
    QueryGraphQuery,
    QueryGraphQueryHandler,
)
from app.application.queries.get_dossier import (
    GetDossierQuery,
    GetDossierQueryHandler,
)
from app.application.queries.get_timeline import (
    GetTimelineQuery,
    GetTimelineQueryHandler,
)
from app.application.queries.list_research_runs import (
    ListResearchRunsQuery,
    ListResearchRunsQueryHandler,
)


logger = logging.getLogger(__name__)


def setup_query_bus(
    # Infrastructure dependencies
    retrieval_pipeline: Any = None,
    result_enricher: Any = None,
    finding_repo: Any = None,
    research_repo: Any = None,
    dossier_repo: Any = None,
    graph_repo: Any = None,
    temporal_monitor: Any = None,
) -> QueryBus:
    """
    Configure and setup the QueryBus with all handlers.

    This function creates handler instances with their dependencies
    and registers them with the query bus.

    Args:
        retrieval_pipeline: Haystack hybrid retrieval pipeline
        result_enricher: Service for enriching search results
        finding_repo: Repository for findings
        research_repo: Repository for research runs
        dossier_repo: Repository for dossiers
        graph_repo: Repository for graph operations
        temporal_monitor: Temporal workflow monitor

    Returns:
        Configured QueryBus instance

    Example:
        >>> # In FastAPI startup
        >>> query_bus = setup_query_bus(
        ...     retrieval_pipeline=haystack_pipeline,
        ...     finding_repo=finding_repository,
        ...     research_repo=research_repository,
        ...     graph_repo=graph_repository,
        ... )
        >>> app.state.query_bus = query_bus
    """
    logger.info("Setting up QueryBus with handlers")

    # Create QueryBus
    bus = QueryBus()

    # Add middleware
    bus.add_middleware(LoggingMiddleware())
    bus.add_middleware(ValidationMiddleware())

    # Register handlers with dependencies
    try:
        # SearchEvidenceQuery
        if retrieval_pipeline and result_enricher:
            search_handler = SearchEvidenceQueryHandler(
                retrieval_pipeline=retrieval_pipeline,
                result_enricher=result_enricher,
            )
            bus.register(SearchEvidenceQuery, search_handler)
            logger.info("Registered SearchEvidenceQueryHandler")

        # GetFindingsQuery
        if finding_repo:
            findings_handler = GetFindingsQueryHandler(
                finding_repo=finding_repo,
            )
            bus.register(GetFindingsQuery, findings_handler)
            logger.info("Registered GetFindingsQueryHandler")

        # GetResearchStatusQuery
        if research_repo:
            status_handler = GetResearchStatusQueryHandler(
                research_repo=research_repo,
                temporal_monitor=temporal_monitor,
            )
            bus.register(GetResearchStatusQuery, status_handler)
            logger.info("Registered GetResearchStatusQueryHandler")

        # QueryGraphQuery
        if graph_repo:
            graph_handler = QueryGraphQueryHandler(
                graph_repo=graph_repo,
            )
            bus.register(QueryGraphQuery, graph_handler)
            logger.info("Registered QueryGraphQueryHandler")

        # GetDossierQuery
        if dossier_repo:
            dossier_handler = GetDossierQueryHandler(
                dossier_repo=dossier_repo,
            )
            bus.register(GetDossierQuery, dossier_handler)
            logger.info("Registered GetDossierQueryHandler")

        # GetTimelineQuery
        if graph_repo:
            timeline_handler = GetTimelineQueryHandler(
                graph_repo=graph_repo,
            )
            bus.register(GetTimelineQuery, timeline_handler)
            logger.info("Registered GetTimelineQueryHandler")

        # ListResearchRunsQuery
        if research_repo:
            list_runs_handler = ListResearchRunsQueryHandler(
                research_repo=research_repo,
            )
            bus.register(ListResearchRunsQuery, list_runs_handler)
            logger.info("Registered ListResearchRunsQueryHandler")

        logger.info(
            f"QueryBus setup complete with {len(bus.get_registered_queries())} handlers",
            extra={"handler_count": len(bus.get_registered_queries())}
        )

    except Exception as e:
        logger.error(f"Failed to setup QueryBus: {e}", exc_info=True)
        raise

    return bus


def get_query_bus_factory():
    """
    Factory function for creating QueryBus instances.

    This can be used with dependency injection frameworks like FastAPI's Depends.

    Returns:
        Function that returns configured QueryBus

    Example:
        >>> # In FastAPI route
        >>> @app.get("/api/search")
        >>> async def search(
        ...     query: str,
        ...     bus: QueryBus = Depends(get_query_bus_factory())
        ... ):
        ...     result = await bus.execute(SearchEvidenceQuery(query=query))
        ...     return result
    """
    def _get_bus() -> QueryBus:
        # This would typically get the bus from app state or container
        # For now, return a new instance
        # In production, this should be a singleton
        raise NotImplementedError(
            "Query bus factory not implemented. "
            "Setup QueryBus in app startup and store in app.state"
        )

    return _get_bus
