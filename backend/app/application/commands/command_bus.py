"""
CommandBus - Central dispatcher for all commands in the application.

The command bus provides a single entry point for executing commands,
handling dependency injection, logging, and error handling.
"""

import logging
from typing import Any, Dict, Type, TypeVar, Generic

logger = logging.getLogger(__name__)

# Type variables for generic command/result handling
TCommand = TypeVar("TCommand")
TResult = TypeVar("TResult")


class CommandHandler(Generic[TCommand, TResult]):
    """
    Base class for command handlers.

    All command handlers should inherit from this class to ensure
    type safety and consistent interface.
    """

    async def handle(self, command: TCommand) -> TResult:
        """
        Handle a command.

        Args:
            command: The command to execute

        Returns:
            Result of command execution
        """
        raise NotImplementedError


class CommandBus:
    """
    Central command dispatcher implementing the Command pattern.

    The CommandBus routes commands to their respective handlers,
    providing:
    - Centralized command dispatching
    - Dependency injection for handlers
    - Logging and monitoring
    - Error handling and recovery

    Example:
        >>> bus = CommandBus()
        >>> bus.register(StartResearchCommand, start_research_handler)
        >>> result = await bus.execute(StartResearchCommand(case_id=uuid4()))
    """

    def __init__(self):
        """Initialize the command bus with an empty handler registry."""
        self._handlers: Dict[Type, Any] = {}
        logger.info("CommandBus initialized")

    def register(self, command_type: Type[TCommand], handler: Any) -> None:
        """
        Register a command handler.

        Args:
            command_type: The command class type
            handler: The handler instance for this command

        Raises:
            ValueError: If handler already registered for this command type

        Example:
            >>> bus.register(StartResearchCommand, StartResearchCommandHandler(...))
        """
        if command_type in self._handlers:
            logger.warning(
                f"Overwriting existing handler for {command_type.__name__}"
            )

        self._handlers[command_type] = handler
        logger.debug(f"Registered handler for {command_type.__name__}")

    def unregister(self, command_type: Type[TCommand]) -> None:
        """
        Unregister a command handler.

        Args:
            command_type: The command class type to unregister
        """
        if command_type in self._handlers:
            del self._handlers[command_type]
            logger.debug(f"Unregistered handler for {command_type.__name__}")

    async def execute(self, command: TCommand) -> TResult:
        """
        Execute a command.

        Args:
            command: The command instance to execute

        Returns:
            Result from the command handler

        Raises:
            ValueError: If no handler registered for this command type
            Exception: Any exception raised by the handler (propagated after logging)

        Example:
            >>> command = StartResearchCommand(case_id=uuid4())
            >>> result = await bus.execute(command)
            >>> if result.success:
            ...     print(f"Research started: {result.workflow_id}")
        """
        command_type = type(command)
        command_name = command_type.__name__

        # Find handler
        handler = self._handlers.get(command_type)
        if not handler:
            error_msg = f"No handler registered for command type: {command_name}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Execute command
        logger.info(f"Executing command: {command_name}")
        logger.debug(f"Command details: {command}")

        try:
            result = await handler.handle(command)
            logger.info(f"Command {command_name} executed successfully")
            logger.debug(f"Result: {result}")
            return result

        except Exception as e:
            logger.error(
                f"Command {command_name} failed with error: {e}",
                exc_info=True,
            )
            # Re-raise the exception after logging
            # The caller can decide how to handle it
            raise

    def has_handler(self, command_type: Type[TCommand]) -> bool:
        """
        Check if a handler is registered for a command type.

        Args:
            command_type: The command class type

        Returns:
            True if handler is registered, False otherwise
        """
        return command_type in self._handlers

    def get_registered_commands(self) -> list[Type]:
        """
        Get list of all registered command types.

        Returns:
            List of command types that have registered handlers
        """
        return list(self._handlers.keys())

    def clear(self) -> None:
        """
        Clear all registered handlers.

        Useful for testing or reinitializing the bus.
        """
        self._handlers.clear()
        logger.info("Cleared all registered command handlers")


# Singleton instance for application-wide use
_command_bus_instance: CommandBus | None = None


def get_command_bus() -> CommandBus:
    """
    Get the singleton CommandBus instance.

    This function ensures a single CommandBus instance is shared
    across the application.

    Returns:
        The singleton CommandBus instance

    Example:
        >>> from app.application.commands.command_bus import get_command_bus
        >>> bus = get_command_bus()
        >>> result = await bus.execute(my_command)
    """
    global _command_bus_instance

    if _command_bus_instance is None:
        _command_bus_instance = CommandBus()
        logger.info("Created singleton CommandBus instance")

    return _command_bus_instance


def reset_command_bus() -> None:
    """
    Reset the singleton CommandBus instance.

    This is primarily useful for testing to ensure a clean state
    between test runs.

    Warning:
        Do not use this in production code unless you know what you're doing.
    """
    global _command_bus_instance
    _command_bus_instance = None
    logger.warning("Reset CommandBus singleton instance")
