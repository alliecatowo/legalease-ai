"""
Application Commands Module.

This module contains all CQRS write operations (commands) for the application.
Commands modify state and trigger workflows, separated from read operations (queries).

Available Commands:
    - StartResearchCommand: Initiate a new deep research workflow
    - ProcessEvidenceCommand: Process and index evidence (documents, transcripts, communications)
    - GenerateReportCommand: Generate dossier files (DOCX, PDF) from research results
    - PauseResearchCommand: Pause a running research workflow
    - ResumeResearchCommand: Resume a paused research workflow
    - CancelResearchCommand: Cancel a running research workflow

Command Bus:
    The CommandBus provides centralized command dispatching with dependency injection,
    logging, and error handling.

Usage Example:
    >>> from app.application.commands import (
    ...     StartResearchCommand,
    ...     get_command_bus,
    ...     get_start_research_handler,
    ... )
    >>>
    >>> # In a FastAPI endpoint
    >>> @app.post("/research/start")
    >>> async def start_research(
    ...     case_id: UUID,
    ...     handler = Depends(get_start_research_handler)
    ... ):
    ...     command = StartResearchCommand(case_id=case_id)
    ...     result = await handler.handle(command)
    ...     return result

Architecture:
    Each command follows the Command pattern:
    1. Command class (immutable dataclass) - Represents the intent
    2. Result class - Structured response with success/error information
    3. Handler class - Contains business logic and orchestration
    4. Dependencies - Injected repositories and services
"""

# Command classes
from .start_research import (
    StartResearchCommand,
    StartResearchResult,
    StartResearchCommandHandler,
)
from .process_evidence import (
    ProcessEvidenceCommand,
    ProcessEvidenceResult,
    ProcessEvidenceCommandHandler,
)
from .generate_report import (
    GenerateReportCommand,
    GenerateReportResult,
    GenerateReportCommandHandler,
)
from .pause_research import (
    PauseResearchCommand,
    PauseResearchResult,
    PauseResearchCommandHandler,
)
from .resume_research import (
    ResumeResearchCommand,
    ResumeResearchResult,
    ResumeResearchCommandHandler,
)
from .cancel_research import (
    CancelResearchCommand,
    CancelResearchResult,
    CancelResearchCommandHandler,
)

# Command bus and infrastructure
from .command_bus import (
    CommandBus,
    CommandHandler,
    get_command_bus,
    reset_command_bus,
)

# Dependency injection
from .dependencies import (
    get_start_research_handler,
    get_process_evidence_handler,
    get_generate_report_handler,
    get_pause_research_handler,
    get_resume_research_handler,
    get_cancel_research_handler,
    setup_command_bus,
)

__all__ = [
    # Start Research
    "StartResearchCommand",
    "StartResearchResult",
    "StartResearchCommandHandler",
    # Process Evidence
    "ProcessEvidenceCommand",
    "ProcessEvidenceResult",
    "ProcessEvidenceCommandHandler",
    # Generate Report
    "GenerateReportCommand",
    "GenerateReportResult",
    "GenerateReportCommandHandler",
    # Pause Research
    "PauseResearchCommand",
    "PauseResearchResult",
    "PauseResearchCommandHandler",
    # Resume Research
    "ResumeResearchCommand",
    "ResumeResearchResult",
    "ResumeResearchCommandHandler",
    # Cancel Research
    "CancelResearchCommand",
    "CancelResearchResult",
    "CancelResearchCommandHandler",
    # Command Bus
    "CommandBus",
    "CommandHandler",
    "get_command_bus",
    "reset_command_bus",
    # Dependencies
    "get_start_research_handler",
    "get_process_evidence_handler",
    "get_generate_report_handler",
    "get_pause_research_handler",
    "get_resume_research_handler",
    "get_cancel_research_handler",
    "setup_command_bus",
]
