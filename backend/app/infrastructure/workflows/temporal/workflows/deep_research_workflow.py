"""
Temporal workflow for deep research orchestration.

This workflow coordinates the entire AI-powered deep research process,
from evidence discovery through final dossier generation. It can take
30 minutes to 4 hours depending on the case size and complexity.
"""

import asyncio
import logging
from datetime import timedelta
from typing import Optional, Dict, Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.infrastructure.workflows.temporal.models import (
        ResearchWorkflowInput,
        ResearchWorkflowOutput,
        WorkflowPhase,
        WorkflowStatus,
        DiscoveryResult,
        PlanningResult,
        DocumentAnalysisResult,
        TranscriptAnalysisResult,
        CommunicationAnalysisResult,
        CorrelationResult,
        Dossier,
    )


logger = logging.getLogger(__name__)


@workflow.defn
class DeepResearchWorkflow:
    """
    Deep research workflow that orchestrates AI-powered case analysis.

    This workflow:
    1. Initializes the research run
    2. Discovers and inventories all evidence (Case Cartography)
    3. Plans search strategies based on available evidence
    4. Executes parallel analysis on documents, transcripts, and communications
    5. Correlates findings and builds knowledge graph
    6. Synthesizes final dossier
    7. Generates report files (DOCX, PDF)

    The workflow supports pause/resume/cancel operations and provides
    real-time status queries for progress monitoring.
    """

    def __init__(self) -> None:
        """Initialize workflow state."""
        self.current_phase: WorkflowPhase = WorkflowPhase.INITIALIZING
        self.progress_pct: float = 0.0
        self.findings_count: int = 0
        self.citations_count: int = 0
        self.is_paused: bool = False
        self.is_cancelled: bool = False
        self.error: Optional[str] = None
        self.current_activity: Optional[str] = None

    @workflow.run
    async def run(self, input: ResearchWorkflowInput) -> ResearchWorkflowOutput:
        """
        Execute the deep research workflow.

        Args:
            input: Workflow input parameters

        Returns:
            ResearchWorkflowOutput with results and status

        Raises:
            Exception: If workflow execution fails
        """
        workflow.logger.info(
            f"Starting deep research workflow for research_run_id={input.research_run_id}, "
            f"case_id={input.case_id}"
        )

        # Default retry policy for activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(minutes=5),
            maximum_attempts=3,
            backoff_coefficient=2.0,
        )

        try:
            # ==================== Phase 0: Initialize ====================
            self.current_phase = WorkflowPhase.INITIALIZING
            self.current_activity = "initialize_research_run"
            self.progress_pct = 0.0

            await workflow.execute_activity(
                "initialize_research_run",
                input,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy,
            )

            await self._check_pause_or_cancel()
            self.progress_pct = 5.0

            # ==================== Phase 1: Discovery (Case Cartography) ====================
            self.current_phase = WorkflowPhase.DISCOVERY
            self.current_activity = "run_discovery_phase"
            workflow.logger.info("Starting discovery phase")

            discovery_result: DiscoveryResult = await workflow.execute_activity(
                "run_discovery_phase",
                input,
                start_to_close_timeout=timedelta(minutes=30),
                heartbeat_timeout=timedelta(minutes=5),
                retry_policy=retry_policy,
            )

            await self._check_pause_or_cancel()
            self.progress_pct = 15.0

            # ==================== Phase 2: Planning ====================
            self.current_phase = WorkflowPhase.PLANNING
            self.current_activity = "run_planning_phase"
            workflow.logger.info("Starting planning phase")

            planning_result: PlanningResult = await workflow.execute_activity(
                "run_planning_phase",
                discovery_result,
                start_to_close_timeout=timedelta(minutes=20),
                heartbeat_timeout=timedelta(minutes=5),
                retry_policy=retry_policy,
            )

            await self._check_pause_or_cancel()
            self.progress_pct = 25.0

            # ==================== Phase 3: Parallel Analysis ====================
            # Run document, transcript, and communication analysts in parallel
            workflow.logger.info("Starting parallel analysis phase")

            analysis_tasks = []

            if planning_result.has_documents:
                self.current_phase = WorkflowPhase.DOCUMENT_ANALYSIS
                self.current_activity = "run_document_analysis"
                analysis_tasks.append(
                    workflow.execute_activity(
                        "run_document_analysis",
                        planning_result,
                        start_to_close_timeout=timedelta(hours=1),
                        heartbeat_timeout=timedelta(minutes=5),
                        retry_policy=retry_policy,
                    )
                )

            if planning_result.has_transcripts:
                self.current_phase = WorkflowPhase.TRANSCRIPT_ANALYSIS
                self.current_activity = "run_transcript_analysis"
                analysis_tasks.append(
                    workflow.execute_activity(
                        "run_transcript_analysis",
                        planning_result,
                        start_to_close_timeout=timedelta(hours=1),
                        heartbeat_timeout=timedelta(minutes=5),
                        retry_policy=retry_policy,
                    )
                )

            if planning_result.has_communications:
                self.current_phase = WorkflowPhase.COMMUNICATION_ANALYSIS
                self.current_activity = "run_communication_analysis"
                analysis_tasks.append(
                    workflow.execute_activity(
                        "run_communication_analysis",
                        planning_result,
                        start_to_close_timeout=timedelta(hours=1),
                        heartbeat_timeout=timedelta(minutes=5),
                        retry_policy=retry_policy,
                    )
                )

            # Wait for all analysis activities to complete
            workflow.logger.info(f"Waiting for {len(analysis_tasks)} analysis activities to complete")
            analysis_results = await asyncio.gather(*analysis_tasks)

            await self._check_pause_or_cancel()

            # Update findings count from analysis results
            for result in analysis_results:
                self.findings_count += len(result.findings)
                self.citations_count += len(result.citations)

            self.progress_pct = 60.0

            # ==================== Phase 4: Correlation ====================
            self.current_phase = WorkflowPhase.CORRELATION
            self.current_activity = "run_correlation_phase"
            workflow.logger.info("Starting correlation phase")

            correlation_result: CorrelationResult = await workflow.execute_activity(
                "run_correlation_phase",
                analysis_results,
                start_to_close_timeout=timedelta(minutes=40),
                heartbeat_timeout=timedelta(minutes=5),
                retry_policy=retry_policy,
            )

            await self._check_pause_or_cancel()
            self.progress_pct = 75.0

            # ==================== Phase 5: Synthesis ====================
            self.current_phase = WorkflowPhase.SYNTHESIS
            self.current_activity = "run_synthesis_phase"
            workflow.logger.info("Starting synthesis phase")

            dossier: Dossier = await workflow.execute_activity(
                "run_synthesis_phase",
                correlation_result,
                start_to_close_timeout=timedelta(minutes=20),
                heartbeat_timeout=timedelta(minutes=5),
                retry_policy=retry_policy,
            )

            await self._check_pause_or_cancel()
            self.progress_pct = 90.0

            # ==================== Phase 6: Generate Report Files ====================
            self.current_phase = WorkflowPhase.REPORT_GENERATION
            self.current_activity = "generate_report_files"
            workflow.logger.info("Generating report files")

            report_path: str = await workflow.execute_activity(
                "generate_report_files",
                dossier,
                start_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=retry_policy,
            )

            # ==================== Complete ====================
            self.current_phase = WorkflowPhase.COMPLETED
            self.current_activity = None
            self.progress_pct = 100.0

            workflow.logger.info(
                f"Deep research workflow completed successfully: "
                f"{self.findings_count} findings, {self.citations_count} citations"
            )

            return ResearchWorkflowOutput(
                research_run_id=input.research_run_id,
                status="COMPLETED",
                dossier_path=report_path,
                findings_count=self.findings_count,
                citations_count=self.citations_count,
                duration_seconds=None,  # Will be calculated by Temporal
            )

        except asyncio.CancelledError:
            # Handle cancellation
            workflow.logger.warning(f"Workflow cancelled for research_run_id={input.research_run_id}")
            self.current_phase = WorkflowPhase.CANCELLED
            self.is_cancelled = True

            return ResearchWorkflowOutput(
                research_run_id=input.research_run_id,
                status="CANCELLED",
                dossier_path=None,
                findings_count=self.findings_count,
                citations_count=self.citations_count,
                error="Workflow was cancelled by user",
            )

        except Exception as e:
            # Handle failure
            error_msg = f"Workflow failed: {str(e)}"
            workflow.logger.error(f"Workflow failed for research_run_id={input.research_run_id}: {e}")
            self.current_phase = WorkflowPhase.FAILED
            self.error = error_msg

            return ResearchWorkflowOutput(
                research_run_id=input.research_run_id,
                status="FAILED",
                dossier_path=None,
                findings_count=self.findings_count,
                citations_count=self.citations_count,
                error=error_msg,
            )

    # ==================== Signals ====================

    @workflow.signal
    async def pause(self) -> None:
        """
        Pause the workflow execution.

        The workflow will pause at the next checkpoint (between activities).
        """
        workflow.logger.info("Received pause signal")
        self.is_paused = True

    @workflow.signal
    async def resume(self) -> None:
        """
        Resume a paused workflow.
        """
        workflow.logger.info("Received resume signal")
        self.is_paused = False

    @workflow.signal
    async def cancel(self) -> None:
        """
        Cancel the workflow execution.

        The workflow will cancel at the next checkpoint.
        """
        workflow.logger.info("Received cancel signal")
        self.is_cancelled = True

    # ==================== Queries ====================

    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """
        Query the current workflow status.

        Returns:
            Dictionary with current phase, progress, and findings count

        Example:
            >>> handle = client.get_workflow_handle(workflow_id)
            >>> status = await handle.query("get_status")
            >>> print(f"Progress: {status['progress_pct']}%")
        """
        return {
            "phase": self.current_phase.value,
            "progress_pct": self.progress_pct,
            "current_activity": self.current_activity,
            "findings_count": self.findings_count,
            "citations_count": self.citations_count,
            "is_paused": self.is_paused,
            "is_cancelled": self.is_cancelled,
            "error": self.error,
        }

    @workflow.query
    def get_progress(self) -> float:
        """
        Get workflow progress percentage.

        Returns:
            Progress as a float between 0.0 and 100.0
        """
        return self.progress_pct

    # ==================== Helper Methods ====================

    async def _check_pause_or_cancel(self) -> None:
        """
        Check if workflow should pause or cancel.

        Raises:
            asyncio.CancelledError: If workflow is cancelled
        """
        # Check for cancellation
        if self.is_cancelled:
            raise asyncio.CancelledError("Workflow cancelled by user")

        # Wait while paused
        while self.is_paused:
            workflow.logger.info("Workflow is paused, waiting for resume signal")
            await asyncio.sleep(1)
