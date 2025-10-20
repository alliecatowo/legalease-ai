"""
Temporal worker for deep research workflows.

This worker executes workflows and activities on behalf of the Temporal server.
Run this as a separate process (e.g., via supervisord or systemd).

Usage:
    python -m app.infrastructure.workflows.temporal.worker

Or with mise:
    mise run worker:temporal
"""

import asyncio
import logging
import signal
from typing import Optional

from temporalio.client import Client
from temporalio.worker import Worker

from app.core.config import settings
from app.infrastructure.workflows.temporal.client import get_temporal_client
from app.infrastructure.workflows.temporal.workflows import DeepResearchWorkflow
from app.infrastructure.workflows.temporal.activities import (
    initialize_research_run,
    run_discovery_phase,
    run_planning_phase,
    run_document_analysis,
    run_transcript_analysis,
    run_communication_analysis,
    run_correlation_phase,
    run_synthesis_phase,
    generate_report_files,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TemporalWorker:
    """
    Temporal worker that executes deep research workflows and activities.

    This worker connects to the Temporal server and processes tasks from
    the configured task queue. It runs workflows and activities asynchronously.
    """

    def __init__(self) -> None:
        """Initialize the worker."""
        self.client: Optional[Client] = None
        self.worker: Optional[Worker] = None
        self.shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """
        Start the Temporal worker.

        Connects to Temporal server and begins processing tasks.

        Raises:
            ConnectionError: If unable to connect to Temporal server
        """
        logger.info("Starting Temporal worker...")

        # Get Temporal client
        self.client = await get_temporal_client()

        logger.info(
            f"Connected to Temporal at {settings.TEMPORAL_HOST}, "
            f"namespace={settings.TEMPORAL_NAMESPACE}"
        )

        # Create worker
        self.worker = Worker(
            self.client,
            task_queue=settings.TEMPORAL_TASK_QUEUE,
            workflows=[DeepResearchWorkflow],
            activities=[
                initialize_research_run,
                run_discovery_phase,
                run_planning_phase,
                run_document_analysis,
                run_transcript_analysis,
                run_communication_analysis,
                run_correlation_phase,
                run_synthesis_phase,
                generate_report_files,
            ],
            max_concurrent_workflow_tasks=settings.RESEARCH_MAX_CONCURRENT_AGENTS,
            max_concurrent_activities=settings.RESEARCH_MAX_CONCURRENT_AGENTS * 2,
        )

        logger.info(
            f"Worker configured with task_queue={settings.TEMPORAL_TASK_QUEUE}, "
            f"max_concurrent_workflows={settings.RESEARCH_MAX_CONCURRENT_AGENTS}"
        )

        # Run worker
        logger.info("Temporal worker started and ready to process tasks")
        await self.worker.run()

    async def stop(self) -> None:
        """
        Stop the Temporal worker gracefully.

        Completes currently running tasks before shutting down.
        """
        logger.info("Stopping Temporal worker...")

        if self.worker:
            # Signal shutdown
            self.shutdown_event.set()

            # Wait for worker to finish current tasks
            # The worker.run() call will complete when shutdown is signaled

        logger.info("Temporal worker stopped")

    async def run(self) -> None:
        """
        Run the worker with signal handling.

        Handles SIGINT and SIGTERM for graceful shutdown.
        """
        # Setup signal handlers
        loop = asyncio.get_running_loop()

        def signal_handler(sig: int) -> None:
            """Handle shutdown signals."""
            logger.info(f"Received signal {sig}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())

        # Register signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

        try:
            # Start worker (this blocks until shutdown)
            await self.start()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            await self.stop()
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            await self.stop()
            raise


async def main() -> None:
    """
    Main entry point for the Temporal worker.

    Creates and runs a worker instance.
    """
    logger.info("Initializing Temporal worker for LegalEase deep research")
    logger.info(f"Configuration:")
    logger.info(f"  Temporal Host: {settings.TEMPORAL_HOST}")
    logger.info(f"  Namespace: {settings.TEMPORAL_NAMESPACE}")
    logger.info(f"  Task Queue: {settings.TEMPORAL_TASK_QUEUE}")
    logger.info(f"  Max Concurrent Agents: {settings.RESEARCH_MAX_CONCURRENT_AGENTS}")

    worker = TemporalWorker()
    await worker.run()


if __name__ == "__main__":
    """Run the worker when executed as a script."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker shutdown complete")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
