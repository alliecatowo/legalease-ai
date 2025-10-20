"""Protocol definitions for dependency injection and clean architecture."""

from app.shared.contracts.repository import Repository, ReadOnlyRepository
from app.shared.contracts.unit_of_work import (
    UnitOfWork,
    AsyncUnitOfWork,
    UnitOfWorkFactory,
    AsyncUnitOfWorkFactory,
)
from app.shared.contracts.event_dispatcher import (
    EventDispatcher,
    AsyncEventDispatcher,
    DomainEvent,
    EventStore,
    AsyncEventStore,
)

__all__ = [
    # Repository
    "Repository",
    "ReadOnlyRepository",
    # Unit of Work
    "UnitOfWork",
    "AsyncUnitOfWork",
    "UnitOfWorkFactory",
    "AsyncUnitOfWorkFactory",
    # Event Dispatcher
    "EventDispatcher",
    "AsyncEventDispatcher",
    "DomainEvent",
    "EventStore",
    "AsyncEventStore",
]
