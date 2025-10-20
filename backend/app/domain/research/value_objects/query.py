"""
Query value object for the Research domain.

Represents a structured research query with type, filters, and parameters.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime


class QueryType(str, Enum):
    """Type of research query."""

    TIMELINE = "TIMELINE"
    ENTITY_SEARCH = "ENTITY_SEARCH"
    PATTERN_DISCOVERY = "PATTERN_DISCOVERY"
    RELATIONSHIP_MAPPING = "RELATIONSHIP_MAPPING"
    CONTRADICTION_ANALYSIS = "CONTRADICTION_ANALYSIS"
    OPEN_ENDED = "OPEN_ENDED"


@dataclass(frozen=True)
class QueryFilter:
    """
    Immutable filter for constraining query scope.

    Attributes:
        field: Field to filter on (e.g., 'date_range', 'entity_type')
        operator: Comparison operator (e.g., 'eq', 'gt', 'contains')
        value: Filter value
    """

    field: str
    operator: str
    value: Any


@dataclass(frozen=True)
class Query:
    """
    Immutable query value object.

    Represents a structured research query that drives the research process.

    Attributes:
        text: Natural language query text
        query_type: Type of query being performed
        filters: List of filters to constrain the search
        parameters: Additional query parameters

    Example:
        >>> query = Query(
        ...     text="Find all communications between John Doe and Jane Smith in March 2024",
        ...     query_type=QueryType.ENTITY_SEARCH,
        ...     filters=[
        ...         QueryFilter("entity_name", "in", ["John Doe", "Jane Smith"]),
        ...         QueryFilter("date", "between", ["2024-03-01", "2024-03-31"]),
        ...     ],
        ...     parameters={"max_results": 100, "min_confidence": 0.7},
        ... )
    """

    text: str
    query_type: QueryType
    filters: List[QueryFilter] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate query invariants."""
        if not self.text or not self.text.strip():
            raise ValueError("Query text cannot be empty")

    def has_filter(self, field: str) -> bool:
        """Check if query has a filter on a specific field."""
        return any(f.field == field for f in self.filters)

    def get_filter(self, field: str) -> Optional[QueryFilter]:
        """Get filter for a specific field."""
        for f in self.filters:
            if f.field == field:
                return f
        return None

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get a query parameter."""
        return self.parameters.get(key, default)
