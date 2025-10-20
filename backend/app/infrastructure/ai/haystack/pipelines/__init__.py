"""
Haystack 2.x pipelines for legal document processing.

This package provides production-ready pipelines for:
- Document indexing (ingestion + embedding)
- Document processing (chunking + enrichment)
- Hybrid retrieval (BM25 + dense vector + RRF)
"""

from app.infrastructure.ai.haystack.pipelines.retrieval import (
    HybridRetrievalPipeline,
    SearchMode,
    create_hybrid_search_pipeline,
    create_keyword_only_pipeline,
    create_semantic_only_pipeline,
)
from app.infrastructure.ai.haystack.pipelines.indexing import (
    DocumentIndexingPipeline,
    TranscriptIndexingPipeline,
    CommunicationIndexingPipeline,
)
from app.infrastructure.ai.haystack.pipelines.pipeline_factory import (
    PipelineFactory,
    create_document_pipeline,
    create_transcript_pipeline,
    create_communication_pipeline,
)

__all__ = [
    # Retrieval pipelines
    "HybridRetrievalPipeline",
    "SearchMode",
    "create_hybrid_search_pipeline",
    "create_keyword_only_pipeline",
    "create_semantic_only_pipeline",
    # Indexing pipelines
    "DocumentIndexingPipeline",
    "TranscriptIndexingPipeline",
    "CommunicationIndexingPipeline",
    # Pipeline factory
    "PipelineFactory",
    "create_document_pipeline",
    "create_transcript_pipeline",
    "create_communication_pipeline",
]
