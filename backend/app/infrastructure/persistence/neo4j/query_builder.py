"""
Cypher query builder for type-safe query construction.

This module provides a fluent API for building Cypher queries programmatically
with parameter injection to prevent Cypher injection attacks.
"""

from typing import Any, Dict, List, Optional, Union
from enum import Enum


class OrderDirection(str, Enum):
    """Sort direction for ORDER BY clause."""
    ASC = "ASC"
    DESC = "DESC"


class CypherQueryBuilder:
    """
    Fluent query builder for Cypher queries.

    Provides a type-safe way to construct complex Cypher queries programmatically
    with automatic parameter handling.

    Example:
        >>> query = (CypherQueryBuilder()
        ...     .match("(p:Person)")
        ...     .where("p.age > $min_age")
        ...     .where("p.city = $city")
        ...     .return_("p")
        ...     .order_by("p.name", OrderDirection.ASC)
        ...     .limit(10)
        ...     .build())
        >>> params = {"min_age": 21, "city": "New York"}
    """

    def __init__(self):
        """Initialize empty query builder."""
        self._match_clauses: List[str] = []
        self._optional_match_clauses: List[str] = []
        self._where_clauses: List[str] = []
        self._with_clauses: List[str] = []
        self._return_clauses: List[str] = []
        self._order_by_clauses: List[str] = []
        self._create_clauses: List[str] = []
        self._merge_clauses: List[str] = []
        self._set_clauses: List[str] = []
        self._delete_clauses: List[str] = []
        self._limit_value: Optional[int] = None
        self._skip_value: Optional[int] = None
        self._distinct: bool = False

    def match(self, pattern: str) -> "CypherQueryBuilder":
        """
        Add a MATCH clause.

        Args:
            pattern: Cypher pattern to match

        Returns:
            Self for chaining

        Example:
            >>> builder.match("(p:Person)-[:KNOWS]->(f:Person)")
        """
        self._match_clauses.append(pattern)
        return self

    def optional_match(self, pattern: str) -> "CypherQueryBuilder":
        """
        Add an OPTIONAL MATCH clause.

        Args:
            pattern: Cypher pattern to optionally match

        Returns:
            Self for chaining

        Example:
            >>> builder.optional_match("(p)-[:LIVES_IN]->(c:City)")
        """
        self._optional_match_clauses.append(pattern)
        return self

    def where(self, condition: str) -> "CypherQueryBuilder":
        """
        Add a WHERE condition.

        Multiple WHERE calls are combined with AND.

        Args:
            condition: Condition expression

        Returns:
            Self for chaining

        Example:
            >>> builder.where("p.age > $min_age").where("p.active = true")
        """
        self._where_clauses.append(condition)
        return self

    def where_in(self, field: str, param_name: str) -> "CypherQueryBuilder":
        """
        Add a WHERE IN condition.

        Args:
            field: Field to check
            param_name: Parameter name for the list

        Returns:
            Self for chaining

        Example:
            >>> builder.where_in("p.type", "types")
            >>> # Generates: WHERE p.type IN $types
        """
        self._where_clauses.append(f"{field} IN ${param_name}")
        return self

    def create(self, pattern: str) -> "CypherQueryBuilder":
        """
        Add a CREATE clause.

        Args:
            pattern: Pattern to create

        Returns:
            Self for chaining

        Example:
            >>> builder.create("(p:Person {name: $name, age: $age})")
        """
        self._create_clauses.append(pattern)
        return self

    def merge(self, pattern: str) -> "CypherQueryBuilder":
        """
        Add a MERGE clause.

        Args:
            pattern: Pattern to merge

        Returns:
            Self for chaining

        Example:
            >>> builder.merge("(p:Person {id: $id})")
        """
        self._merge_clauses.append(pattern)
        return self

    def set(self, assignments: Union[str, List[str]]) -> "CypherQueryBuilder":
        """
        Add SET assignments.

        Args:
            assignments: Single assignment or list of assignments

        Returns:
            Self for chaining

        Example:
            >>> builder.set("p.name = $name")
            >>> builder.set(["p.name = $name", "p.age = $age"])
        """
        if isinstance(assignments, str):
            self._set_clauses.append(assignments)
        else:
            self._set_clauses.extend(assignments)
        return self

    def delete(self, variables: Union[str, List[str]]) -> "CypherQueryBuilder":
        """
        Add DELETE clause.

        Args:
            variables: Variable or list of variables to delete

        Returns:
            Self for chaining

        Example:
            >>> builder.delete("r")
            >>> builder.delete(["r", "n"])
        """
        if isinstance(variables, str):
            self._delete_clauses.append(variables)
        else:
            self._delete_clauses.extend(variables)
        return self

    def detach_delete(self, variables: Union[str, List[str]]) -> "CypherQueryBuilder":
        """
        Add DETACH DELETE clause.

        Args:
            variables: Variable or list of variables to delete with relationships

        Returns:
            Self for chaining

        Example:
            >>> builder.detach_delete("n")
        """
        if isinstance(variables, str):
            self._delete_clauses.append(f"DETACH {variables}")
        else:
            for var in variables:
                self._delete_clauses.append(f"DETACH {var}")
        return self

    def with_(self, expressions: Union[str, List[str]]) -> "CypherQueryBuilder":
        """
        Add WITH clause.

        Args:
            expressions: Expression or list of expressions

        Returns:
            Self for chaining

        Example:
            >>> builder.with_("p, count(f) as friend_count")
        """
        if isinstance(expressions, str):
            self._with_clauses.append(expressions)
        else:
            self._with_clauses.append(", ".join(expressions))
        return self

    def return_(
        self,
        expressions: Union[str, List[str]],
        distinct: bool = False
    ) -> "CypherQueryBuilder":
        """
        Add RETURN clause.

        Args:
            expressions: Expression or list of expressions to return
            distinct: Whether to use DISTINCT

        Returns:
            Self for chaining

        Example:
            >>> builder.return_("p.name, p.age")
            >>> builder.return_(["p", "f"], distinct=True)
        """
        if isinstance(expressions, str):
            self._return_clauses.append(expressions)
        else:
            self._return_clauses.append(", ".join(expressions))

        if distinct:
            self._distinct = True

        return self

    def order_by(
        self,
        field: str,
        direction: OrderDirection = OrderDirection.ASC
    ) -> "CypherQueryBuilder":
        """
        Add ORDER BY clause.

        Args:
            field: Field to sort by
            direction: Sort direction (ASC or DESC)

        Returns:
            Self for chaining

        Example:
            >>> builder.order_by("p.name")
            >>> builder.order_by("p.age", OrderDirection.DESC)
        """
        self._order_by_clauses.append(f"{field} {direction.value}")
        return self

    def limit(self, count: int) -> "CypherQueryBuilder":
        """
        Add LIMIT clause.

        Args:
            count: Maximum number of results

        Returns:
            Self for chaining

        Example:
            >>> builder.limit(100)
        """
        self._limit_value = count
        return self

    def skip(self, count: int) -> "CypherQueryBuilder":
        """
        Add SKIP clause.

        Args:
            count: Number of results to skip

        Returns:
            Self for chaining

        Example:
            >>> builder.skip(50).limit(10)  # Pagination
        """
        self._skip_value = count
        return self

    def build(self) -> str:
        """
        Build the final Cypher query string.

        Returns:
            Complete Cypher query

        Example:
            >>> query = builder.match("(p:Person)").return_("p").build()
            >>> print(query)
            MATCH (p:Person)
            RETURN p
        """
        parts: List[str] = []

        # MATCH clauses
        for match_clause in self._match_clauses:
            parts.append(f"MATCH {match_clause}")

        # OPTIONAL MATCH clauses
        for optional_match in self._optional_match_clauses:
            parts.append(f"OPTIONAL MATCH {optional_match}")

        # CREATE clauses
        for create_clause in self._create_clauses:
            parts.append(f"CREATE {create_clause}")

        # MERGE clauses
        for merge_clause in self._merge_clauses:
            parts.append(f"MERGE {merge_clause}")

        # SET clauses
        if self._set_clauses:
            parts.append(f"SET {', '.join(self._set_clauses)}")

        # WHERE clauses
        if self._where_clauses:
            parts.append(f"WHERE {' AND '.join(self._where_clauses)}")

        # WITH clauses
        for with_clause in self._with_clauses:
            parts.append(f"WITH {with_clause}")

        # DELETE clauses
        if self._delete_clauses:
            delete_items = []
            detach_items = []
            for item in self._delete_clauses:
                if item.startswith("DETACH "):
                    detach_items.append(item.replace("DETACH ", ""))
                else:
                    delete_items.append(item)

            if detach_items:
                parts.append(f"DETACH DELETE {', '.join(detach_items)}")
            if delete_items:
                parts.append(f"DELETE {', '.join(delete_items)}")

        # RETURN clauses
        if self._return_clauses:
            return_str = "RETURN DISTINCT" if self._distinct else "RETURN"
            parts.append(f"{return_str} {', '.join(self._return_clauses)}")

        # ORDER BY clauses
        if self._order_by_clauses:
            parts.append(f"ORDER BY {', '.join(self._order_by_clauses)}")

        # SKIP clause
        if self._skip_value is not None:
            parts.append(f"SKIP {self._skip_value}")

        # LIMIT clause
        if self._limit_value is not None:
            parts.append(f"LIMIT {self._limit_value}")

        return "\n".join(parts)

    def __str__(self) -> str:
        """Return the built query."""
        return self.build()

    def __repr__(self) -> str:
        """Return representation of the builder."""
        return f"<CypherQueryBuilder: {len(self._match_clauses)} matches, {len(self._where_clauses)} conditions>"


def build_property_map(
    properties: Dict[str, Any],
    prefix: str = ""
) -> tuple[str, Dict[str, Any]]:
    """
    Build a property map expression and parameters.

    Args:
        properties: Dictionary of properties
        prefix: Optional prefix for parameter names

    Returns:
        Tuple of (property expression, parameters dict)

    Example:
        >>> expr, params = build_property_map({"name": "Alice", "age": 30}, "person")
        >>> print(expr)
        {name: $person_name, age: $person_age}
        >>> print(params)
        {'person_name': 'Alice', 'person_age': 30}
    """
    if not properties:
        return "{}", {}

    expressions = []
    parameters = {}

    for key, value in properties.items():
        param_name = f"{prefix}_{key}" if prefix else key
        expressions.append(f"{key}: ${param_name}")
        parameters[param_name] = value

    expr = "{" + ", ".join(expressions) + "}"
    return expr, parameters


def escape_property_name(name: str) -> str:
    """
    Escape a property name for use in Cypher.

    Args:
        name: Property name

    Returns:
        Escaped property name

    Example:
        >>> escape_property_name("my-property")
        '`my-property`'
    """
    # Only escape if necessary (contains special characters)
    if any(char in name for char in ["-", " ", ".", ":"]):
        return f"`{name}`"
    return name
