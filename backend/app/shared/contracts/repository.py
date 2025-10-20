"""
Generic repository protocol for data access.

This module defines the Repository protocol that all repository
implementations should follow for consistency and testability.

Example:
    >>> class CaseRepository(Repository[Case, CaseId]):
    ...     def get(self, id: CaseId) -> Optional[Case]:
    ...         return db.query(Case).filter_by(id=id).first()
    ...
    ...     def add(self, entity: Case) -> None:
    ...         db.add(entity)
    ...
    ...     def delete(self, entity: Case) -> None:
    ...         db.delete(entity)
"""

from typing import Generic, List, Optional, Protocol, TypeVar
from uuid import UUID

# Generic types for repository pattern
TEntity = TypeVar("TEntity", contravariant=False)
TId = TypeVar("TId", bound=UUID, contravariant=False)


class Repository(Protocol, Generic[TEntity, TId]):
    """
    Generic repository protocol for CRUD operations.

    This protocol defines the standard interface for data access operations.
    All repository implementations should conform to this protocol to enable
    dependency injection and testability.

    Type Parameters:
        TEntity: The domain entity type
        TId: The identifier type (must be UUID-based)

    Example:
        >>> from app.shared.types import CaseId
        >>> from app.models import Case
        >>>
        >>> class CaseRepository(Repository[Case, CaseId]):
        ...     def __init__(self, db: Session):
        ...         self.db = db
        ...
        ...     def get(self, id: CaseId) -> Optional[Case]:
        ...         return self.db.query(Case).filter_by(id=id).first()
        ...
        ...     def add(self, entity: Case) -> None:
        ...         self.db.add(entity)
        ...
        ...     def save(self, entity: Case) -> None:
        ...         self.db.merge(entity)
        ...
        ...     def delete(self, entity: Case) -> None:
        ...         self.db.delete(entity)
        ...
        ...     def list(self, limit: int = 100, offset: int = 0) -> List[Case]:
        ...         return self.db.query(Case).limit(limit).offset(offset).all()
    """

    def get(self, id: TId) -> Optional[TEntity]:
        """
        Retrieve an entity by its identifier.

        Args:
            id: The entity identifier

        Returns:
            The entity if found, None otherwise

        Example:
            >>> case = repository.get(CaseId(uuid.uuid4()))
            >>> if case:
            ...     print(f"Found: {case.name}")
        """
        ...

    def add(self, entity: TEntity) -> None:
        """
        Add a new entity to the repository.

        Args:
            entity: The entity to add

        Example:
            >>> case = Case(name="New Case", case_number="2024-001")
            >>> repository.add(case)
            >>> db.commit()
        """
        ...

    def save(self, entity: TEntity) -> None:
        """
        Save changes to an existing entity.

        This is typically used for updates. Some implementations
        may merge this with add().

        Args:
            entity: The entity to save

        Example:
            >>> case.name = "Updated Name"
            >>> repository.save(case)
            >>> db.commit()
        """
        ...

    def delete(self, entity: TEntity) -> None:
        """
        Delete an entity from the repository.

        Args:
            entity: The entity to delete

        Example:
            >>> repository.delete(case)
            >>> db.commit()
        """
        ...

    def list(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[TEntity]:
        """
        List entities with optional filtering and pagination.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            **filters: Additional filter criteria (implementation-specific)

        Returns:
            List of entities matching the criteria

        Example:
            >>> # Get first 10 active cases
            >>> cases = repository.list(limit=10, status="ACTIVE")
            >>>
            >>> # Get next page
            >>> cases = repository.list(limit=10, offset=10, status="ACTIVE")
        """
        ...

    def count(self, **filters) -> int:
        """
        Count entities matching the given criteria.

        Args:
            **filters: Filter criteria (implementation-specific)

        Returns:
            Number of matching entities

        Example:
            >>> total = repository.count(status="ACTIVE")
            >>> print(f"Active cases: {total}")
        """
        ...

    def exists(self, id: TId) -> bool:
        """
        Check if an entity exists by ID.

        Args:
            id: The entity identifier

        Returns:
            True if entity exists, False otherwise

        Example:
            >>> if repository.exists(case_id):
            ...     print("Case exists")
        """
        ...

    def find_by(self, **criteria) -> Optional[TEntity]:
        """
        Find a single entity matching the given criteria.

        Args:
            **criteria: Search criteria (implementation-specific)

        Returns:
            First matching entity or None

        Example:
            >>> case = repository.find_by(case_number="2024-001")
            >>> if case:
            ...     print(f"Found: {case.name}")
        """
        ...

    def find_all_by(self, **criteria) -> List[TEntity]:
        """
        Find all entities matching the given criteria.

        Args:
            **criteria: Search criteria (implementation-specific)

        Returns:
            List of matching entities

        Example:
            >>> active_cases = repository.find_all_by(status="ACTIVE")
            >>> archived_cases = repository.find_all_by(status="ARCHIVED")
        """
        ...


class ReadOnlyRepository(Protocol, Generic[TEntity, TId]):
    """
    Read-only repository protocol for query operations only.

    This protocol is useful for read models, reporting, and cases
    where write operations should not be allowed.

    Example:
        >>> class CaseQueryRepository(ReadOnlyRepository[Case, CaseId]):
        ...     def get(self, id: CaseId) -> Optional[Case]:
        ...         return db.query(Case).filter_by(id=id).first()
        ...
        ...     def list(self, limit: int = 100, offset: int = 0) -> List[Case]:
        ...         return db.query(Case).limit(limit).offset(offset).all()
    """

    def get(self, id: TId) -> Optional[TEntity]:
        """Retrieve an entity by its identifier."""
        ...

    def list(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[TEntity]:
        """List entities with optional filtering and pagination."""
        ...

    def count(self, **filters) -> int:
        """Count entities matching the given criteria."""
        ...

    def exists(self, id: TId) -> bool:
        """Check if an entity exists by ID."""
        ...

    def find_by(self, **criteria) -> Optional[TEntity]:
        """Find a single entity matching the given criteria."""
        ...

    def find_all_by(self, **criteria) -> List[TEntity]:
        """Find all entities matching the given criteria."""
        ...
