"""
Application layer queries for CQRS pattern.

This module contains all query classes, handlers, and the query bus
for read operations following CQRS (Command Query Responsibility Segregation).

Queries are immutable, side-effect free operations that fetch data
without modifying state. All queries return DTOs (Data Transfer Objects)
rather than domain entities to maintain separation of concerns.

Available Queries:
    - SearchEvidenceQuery: Hybrid search across all evidence
    - GetFindingsQuery: Retrieve findings from research run
    - GetResearchStatusQuery: Get current research run status
    - QueryGraphQuery: Query knowledge graph
    - GetDossierQuery: Retrieve generated dossier
    - GetTimelineQuery: Get chronological timeline
    - ListResearchRunsQuery: List research runs for a case

Example:
    >>> from app.application.queries import QueryBus, SearchEvidenceQuery
    >>> from app.application.queries.dependencies import setup_query_bus
    >>>
    >>> # Setup query bus with dependencies
    >>> bus = setup_query_bus(
    ...     retrieval_pipeline=pipeline,
    ...     finding_repo=repo,
    ...     # ... other dependencies
    ... )
    >>>
    >>> # Execute a query
    >>> query = SearchEvidenceQuery(
    ...     query="contract terms",
    ...     case_ids=[case_uuid],
    ...     top_k=20,
    ... )
    >>> result = await bus.execute(query)
"""

# Query Bus
from app.application.queries.query_bus import (
    QueryBus,
    QueryHandler,
    LoggingMiddleware,
    ValidationMiddleware,
)

# Search Evidence
from app.application.queries.search_evidence import (
    SearchEvidenceQuery,
    SearchResult,
    SearchEvidenceResult,
    SearchEvidenceQueryHandler,
)

# Get Findings
from app.application.queries.get_findings import (
    GetFindingsQuery,
    FindingDTO,
    GetFindingsResult,
    GetFindingsQueryHandler,
)

# Get Research Status
from app.application.queries.get_research_status import (
    GetResearchStatusQuery,
    ResearchStatusDTO,
    GetResearchStatusQueryHandler,
)

# Query Graph
from app.application.queries.query_graph import (
    QueryGraphQuery,
    EntityDTO,
    RelationshipDTO,
    EventDTO,
    QueryGraphResult,
    QueryGraphQueryHandler,
)

# Get Dossier
from app.application.queries.get_dossier import (
    GetDossierQuery,
    DossierDTO,
    DossierSectionDTO,
    GetDossierQueryHandler,
)

# Get Timeline
from app.application.queries.get_timeline import (
    GetTimelineQuery,
    TimelineEventDTO,
    GetTimelineResult,
    GetTimelineQueryHandler,
)

# List Research Runs
from app.application.queries.list_research_runs import (
    ListResearchRunsQuery,
    ListResearchRunsResult,
    ListResearchRunsQueryHandler,
)

# Dependencies
from app.application.queries.dependencies import setup_query_bus


__all__ = [
    # Query Bus
    "QueryBus",
    "QueryHandler",
    "LoggingMiddleware",
    "ValidationMiddleware",
    # Search Evidence
    "SearchEvidenceQuery",
    "SearchResult",
    "SearchEvidenceResult",
    "SearchEvidenceQueryHandler",
    # Get Findings
    "GetFindingsQuery",
    "FindingDTO",
    "GetFindingsResult",
    "GetFindingsQueryHandler",
    # Get Research Status
    "GetResearchStatusQuery",
    "ResearchStatusDTO",
    "GetResearchStatusQueryHandler",
    # Query Graph
    "QueryGraphQuery",
    "EntityDTO",
    "RelationshipDTO",
    "EventDTO",
    "QueryGraphResult",
    "QueryGraphQueryHandler",
    # Get Dossier
    "GetDossierQuery",
    "DossierDTO",
    "DossierSectionDTO",
    "GetDossierQueryHandler",
    # Get Timeline
    "GetTimelineQuery",
    "TimelineEventDTO",
    "GetTimelineResult",
    "GetTimelineQueryHandler",
    # List Research Runs
    "ListResearchRunsQuery",
    "ListResearchRunsResult",
    "ListResearchRunsQueryHandler",
    # Dependencies
    "setup_query_bus",
]
