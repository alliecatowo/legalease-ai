"""
ProcessEvidenceCommand - Processes and indexes new evidence.

This command handles ingestion of documents, transcripts, and communications,
using Haystack indexing pipelines to write to Qdrant and OpenSearch.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from app.shared.types.enums import EvidenceType
from app.infrastructure.ai.haystack.pipelines.indexing import (
    IndexingPipelineFactory,
)
from app.infrastructure.persistence.qdrant.repositories.document import (
    QdrantDocumentRepository,
)
from app.infrastructure.persistence.opensearch.repositories.document import (
    OpenSearchDocumentRepository,
)


logger = logging.getLogger(__name__)


@dataclass
class ProcessEvidenceCommand:
    """
    Command to process and index evidence.

    Attributes:
        evidence_id: UUID of the evidence to process
        evidence_type: Type of evidence (DOCUMENT, TRANSCRIPT, COMMUNICATION)
        case_id: UUID of the case this evidence belongs to
        file_path: Path to the file (for documents/transcripts)
        data: Structured data (for communications)
        metadata: Additional metadata to store
    """

    evidence_id: UUID
    evidence_type: EvidenceType
    case_id: UUID
    file_path: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProcessEvidenceResult:
    """
    Result of processing evidence.

    Attributes:
        success: Whether processing succeeded
        evidence_id: ID of the processed evidence
        chunks_indexed: Number of chunks indexed
        message: Human-readable status message
        error: Error message if failed
        metadata: Additional result metadata
    """

    success: bool
    evidence_id: UUID
    chunks_indexed: int = 0
    message: str = ""
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProcessEvidenceCommandHandler:
    """
    Handler for ProcessEvidenceCommand.

    Orchestrates:
    1. Validating evidence exists and is accessible
    2. Selecting appropriate Haystack indexing pipeline
    3. Running indexing pipeline (writes to Qdrant + OpenSearch)
    4. Updating metadata in PostgreSQL
    """

    def __init__(
        self,
        pipeline_factory: IndexingPipelineFactory,
        qdrant_repo: QdrantDocumentRepository,
        opensearch_repo: OpenSearchDocumentRepository,
    ):
        """
        Initialize handler with dependencies.

        Args:
            pipeline_factory: Factory for creating indexing pipelines
            qdrant_repo: Qdrant repository for vector storage
            opensearch_repo: OpenSearch repository for text search
        """
        self.pipeline_factory = pipeline_factory
        self.qdrant_repo = qdrant_repo
        self.opensearch_repo = opensearch_repo

    async def handle(self, command: ProcessEvidenceCommand) -> ProcessEvidenceResult:
        """
        Handle the ProcessEvidenceCommand.

        Args:
            command: The command to execute

        Returns:
            ProcessEvidenceResult with success status and chunk count

        Process:
            1. Validate evidence file/data exists
            2. Select appropriate pipeline based on evidence type
            3. Run indexing pipeline
            4. Verify chunks were written
            5. Return result
        """
        logger.info(
            f"Processing {command.evidence_type.value} evidence {command.evidence_id}"
        )

        try:
            # Validate input
            if command.evidence_type in (
                EvidenceType.DOCUMENT,
                EvidenceType.TRANSCRIPT,
            ):
                if not command.file_path:
                    return ProcessEvidenceResult(
                        success=False,
                        evidence_id=command.evidence_id,
                        message="file_path is required for documents and transcripts",
                        error="Missing file_path",
                    )

                # Check file exists
                file_path = Path(command.file_path)
                if not file_path.exists():
                    return ProcessEvidenceResult(
                        success=False,
                        evidence_id=command.evidence_id,
                        message=f"File not found: {command.file_path}",
                        error="File not found",
                    )

            elif command.evidence_type == EvidenceType.COMMUNICATION:
                if not command.data:
                    return ProcessEvidenceResult(
                        success=False,
                        evidence_id=command.evidence_id,
                        message="data is required for communications",
                        error="Missing data",
                    )

            # Select appropriate pipeline
            logger.info(f"Creating indexing pipeline for {command.evidence_type.value}")
            pipeline = self.pipeline_factory.create_pipeline(command.evidence_type)

            # Prepare pipeline input
            pipeline_input = {
                "evidence_id": str(command.evidence_id),
                "case_id": str(command.case_id),
                "evidence_type": command.evidence_type.value,
                "metadata": command.metadata or {},
            }

            if command.file_path:
                pipeline_input["file_path"] = command.file_path

            if command.data:
                pipeline_input["data"] = command.data

            # Run indexing pipeline
            logger.info(f"Running indexing pipeline for evidence {command.evidence_id}")
            result = await pipeline.run(pipeline_input)

            # Extract chunk count from pipeline result
            # The exact structure depends on the pipeline implementation
            chunks_indexed = self._extract_chunk_count(result)

            logger.info(
                f"Successfully indexed {chunks_indexed} chunks for evidence {command.evidence_id}"
            )

            return ProcessEvidenceResult(
                success=True,
                evidence_id=command.evidence_id,
                chunks_indexed=chunks_indexed,
                message=f"Successfully processed {command.evidence_type.value}",
                metadata={
                    "pipeline_result": result,
                    "evidence_type": command.evidence_type.value,
                },
            )

        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return ProcessEvidenceResult(
                success=False,
                evidence_id=command.evidence_id,
                message=f"File not found: {command.file_path}",
                error=str(e),
            )

        except Exception as e:
            logger.error(
                f"Failed to process evidence {command.evidence_id}: {e}", exc_info=True
            )
            return ProcessEvidenceResult(
                success=False,
                evidence_id=command.evidence_id,
                message="Failed to process evidence",
                error=str(e),
            )

    def _extract_chunk_count(self, pipeline_result: Dict[str, Any]) -> int:
        """
        Extract chunk count from pipeline result.

        Args:
            pipeline_result: Result dictionary from pipeline execution

        Returns:
            Number of chunks indexed
        """
        # Try different possible keys where chunk count might be stored
        possible_keys = [
            "chunks_indexed",
            "documents_written",
            "chunks_written",
            "num_chunks",
        ]

        for key in possible_keys:
            if key in pipeline_result:
                value = pipeline_result[key]
                if isinstance(value, int):
                    return value
                elif isinstance(value, list):
                    return len(value)

        # Try to find in nested results
        if "writer" in pipeline_result:
            writer_result = pipeline_result["writer"]
            if isinstance(writer_result, dict):
                if "documents_written" in writer_result:
                    return writer_result["documents_written"]

        # Default to 0 if we can't determine
        logger.warning(
            f"Could not determine chunk count from pipeline result: {pipeline_result.keys()}"
        )
        return 0
