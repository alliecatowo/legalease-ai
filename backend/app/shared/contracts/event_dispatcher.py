"""
Event Dispatcher protocol for domain event publishing.

This module defines the EventDispatcher protocol for publishing and
handling domain events in an event-driven architecture.

Example:
    >>> from dataclasses import dataclass
    >>> from datetime import datetime
    >>>
    >>> @dataclass
    ... class CaseCreated:
    ...     case_id: str
    ...     case_number: str
    ...     timestamp: datetime
    >>>
    >>> event = CaseCreated(
    ...     case_id="123",
    ...     case_number="2024-001",
    ...     timestamp=datetime.utcnow()
    ... )
    >>> await dispatcher.dispatch(event)
"""

from typing import Any, Awaitable, Callable, List, Protocol, TypeVar, Generic

# Type for domain events (any object)
TEvent = TypeVar("TEvent")

# Type for event handlers
EventHandler = Callable[[TEvent], None]
AsyncEventHandler = Callable[[TEvent], Awaitable[None]]


class EventDispatcher(Protocol):
    """
    Event dispatcher protocol for synchronous event publishing.

    The Event Dispatcher pattern enables loose coupling between components
    by allowing domain events to be published and handled asynchronously.

    This is useful for:
    - Sending notifications when entities change
    - Triggering side effects after business operations
    - Integrating with external systems
    - Implementing audit logs and event sourcing

    Example:
        >>> class InMemoryEventDispatcher(EventDispatcher):
        ...     def __init__(self):
        ...         self._handlers = {}
        ...
        ...     def register(self, event_type: type, handler: EventHandler):
        ...         if event_type not in self._handlers:
        ...             self._handlers[event_type] = []
        ...         self._handlers[event_type].append(handler)
        ...
        ...     def dispatch(self, event: Any) -> None:
        ...         event_type = type(event)
        ...         if event_type in self._handlers:
        ...             for handler in self._handlers[event_type]:
        ...                 handler(event)

        >>> # Usage
        >>> dispatcher = InMemoryEventDispatcher()
        >>> dispatcher.register(CaseCreated, send_notification)
        >>> dispatcher.register(CaseCreated, update_search_index)
        >>> dispatcher.dispatch(CaseCreated(case_id="123"))
    """

    def register(
        self,
        event_type: type[TEvent],
        handler: EventHandler[TEvent]
    ) -> None:
        """
        Register an event handler for a specific event type.

        Args:
            event_type: The type of event to handle
            handler: The handler function to call when event is dispatched

        Example:
            >>> def on_case_created(event: CaseCreated):
            ...     print(f"Case created: {event.case_number}")
            >>>
            >>> dispatcher.register(CaseCreated, on_case_created)
        """
        ...

    def unregister(
        self,
        event_type: type[TEvent],
        handler: EventHandler[TEvent]
    ) -> None:
        """
        Unregister a previously registered event handler.

        Args:
            event_type: The type of event
            handler: The handler to remove

        Example:
            >>> dispatcher.unregister(CaseCreated, on_case_created)
        """
        ...

    def dispatch(self, event: TEvent) -> None:
        """
        Dispatch an event to all registered handlers.

        This calls all handlers registered for the event's type
        synchronously in the order they were registered.

        Args:
            event: The event to dispatch

        Example:
            >>> event = CaseCreated(case_id="123", case_number="2024-001")
            >>> dispatcher.dispatch(event)
        """
        ...

    def dispatch_all(self, events: List[TEvent]) -> None:
        """
        Dispatch multiple events in sequence.

        Args:
            events: List of events to dispatch

        Example:
            >>> events = [
            ...     CaseCreated(...),
            ...     DocumentAdded(...),
            ...     CaseUpdated(...)
            ... ]
            >>> dispatcher.dispatch_all(events)
        """
        ...


class AsyncEventDispatcher(Protocol):
    """
    Async event dispatcher protocol for asynchronous event publishing.

    This is the async version of EventDispatcher for use with async/await
    event handlers.

    Example:
        >>> class AsyncEventDispatcher:
        ...     def __init__(self):
        ...         self._handlers = {}
        ...
        ...     def register(self, event_type: type, handler: AsyncEventHandler):
        ...         if event_type not in self._handlers:
        ...             self._handlers[event_type] = []
        ...         self._handlers[event_type].append(handler)
        ...
        ...     async def dispatch(self, event: Any) -> None:
        ...         event_type = type(event)
        ...         if event_type in self._handlers:
        ...             for handler in self._handlers[event_type]:
        ...                 await handler(event)

        >>> # Usage
        >>> async def on_case_created(event: CaseCreated):
        ...     await send_email_notification(event.case_number)
        >>>
        >>> dispatcher = AsyncEventDispatcher()
        >>> dispatcher.register(CaseCreated, on_case_created)
        >>> await dispatcher.dispatch(CaseCreated(case_id="123"))
    """

    def register(
        self,
        event_type: type[TEvent],
        handler: AsyncEventHandler[TEvent]
    ) -> None:
        """
        Register an async event handler for a specific event type.

        Args:
            event_type: The type of event to handle
            handler: The async handler function to call when event is dispatched

        Example:
            >>> async def on_case_created(event: CaseCreated):
            ...     await notify_users(event.case_id)
            >>>
            >>> dispatcher.register(CaseCreated, on_case_created)
        """
        ...

    def unregister(
        self,
        event_type: type[TEvent],
        handler: AsyncEventHandler[TEvent]
    ) -> None:
        """
        Unregister a previously registered async event handler.

        Args:
            event_type: The type of event
            handler: The handler to remove
        """
        ...

    async def dispatch(self, event: TEvent) -> None:
        """
        Dispatch an event to all registered async handlers.

        This awaits all handlers registered for the event's type
        in the order they were registered.

        Args:
            event: The event to dispatch

        Example:
            >>> event = CaseCreated(case_id="123", case_number="2024-001")
            >>> await dispatcher.dispatch(event)
        """
        ...

    async def dispatch_all(self, events: List[TEvent]) -> None:
        """
        Dispatch multiple events in sequence asynchronously.

        Args:
            events: List of events to dispatch

        Example:
            >>> events = [
            ...     CaseCreated(...),
            ...     DocumentAdded(...),
            ... ]
            >>> await dispatcher.dispatch_all(events)
        """
        ...


class DomainEvent(Protocol):
    """
    Protocol that all domain events should implement.

    Domain events represent something that happened in the domain
    that domain experts care about.

    Example:
        >>> @dataclass
        ... class CaseCreated:
        ...     event_id: str
        ...     timestamp: datetime
        ...     case_id: str
        ...     case_number: str
        ...
        ...     def event_name(self) -> str:
        ...         return "case.created"
        ...
        ...     def aggregate_id(self) -> str:
        ...         return self.case_id
    """

    def event_name(self) -> str:
        """
        Get the name of the event.

        This is typically in the format "entity.action" (e.g., "case.created").

        Returns:
            Event name string

        Example:
            >>> event = CaseCreated(...)
            >>> event.event_name()
            'case.created'
        """
        ...

    def aggregate_id(self) -> str:
        """
        Get the ID of the aggregate that generated this event.

        Returns:
            Aggregate identifier

        Example:
            >>> event = CaseCreated(case_id="123", ...)
            >>> event.aggregate_id()
            '123'
        """
        ...


class EventStore(Protocol):
    """
    Protocol for event store implementations.

    An event store persists domain events for event sourcing
    and audit trail purposes.

    Example:
        >>> class PostgresEventStore(EventStore):
        ...     def append(self, event: DomainEvent) -> None:
        ...         db.execute(
        ...             "INSERT INTO events (name, data, timestamp) VALUES (%s, %s, %s)",
        ...             (event.event_name(), json.dumps(event.__dict__), datetime.utcnow())
        ...         )
        ...
        ...     def get_events(self, aggregate_id: str) -> List[DomainEvent]:
        ...         rows = db.execute(
        ...             "SELECT data FROM events WHERE aggregate_id = %s ORDER BY timestamp",
        ...             (aggregate_id,)
        ...         )
        ...         return [deserialize_event(row['data']) for row in rows]
    """

    def append(self, event: DomainEvent) -> None:
        """
        Append an event to the store.

        Args:
            event: The domain event to persist

        Example:
            >>> event = CaseCreated(...)
            >>> event_store.append(event)
        """
        ...

    def get_events(
        self,
        aggregate_id: str,
        from_version: int = 0
    ) -> List[DomainEvent]:
        """
        Get all events for an aggregate.

        Args:
            aggregate_id: ID of the aggregate
            from_version: Optional version number to get events from

        Returns:
            List of events in chronological order

        Example:
            >>> events = event_store.get_events("case-123")
            >>> for event in events:
            ...     print(event.event_name())
        """
        ...

    def get_events_by_type(
        self,
        event_type: type[TEvent],
        limit: int = 100
    ) -> List[TEvent]:
        """
        Get events of a specific type.

        Args:
            event_type: Type of events to retrieve
            limit: Maximum number of events to return

        Returns:
            List of events of the specified type

        Example:
            >>> events = event_store.get_events_by_type(CaseCreated, limit=10)
        """
        ...


class AsyncEventStore(Protocol):
    """
    Async protocol for event store implementations.

    This is the async version of EventStore.
    """

    async def append(self, event: DomainEvent) -> None:
        """Append an event to the store asynchronously."""
        ...

    async def get_events(
        self,
        aggregate_id: str,
        from_version: int = 0
    ) -> List[DomainEvent]:
        """Get all events for an aggregate asynchronously."""
        ...

    async def get_events_by_type(
        self,
        event_type: type[TEvent],
        limit: int = 100
    ) -> List[TEvent]:
        """Get events of a specific type asynchronously."""
        ...
