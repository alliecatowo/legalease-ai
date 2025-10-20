"""
Haystack 2.x custom components for legal document processing.

This package contains custom Haystack components for:
- Document conversion (Cellebrite, legal documents)
- Legal chunking strategies
- Citation extraction
- Hybrid retrieval (Qdrant + OpenSearch)
- Reciprocal rank fusion
- Query preprocessing
- Result enrichment
"""

from app.infrastructure.ai.haystack.components.cellebrite_converter import (
    CellebriteConverter,
)
from app.infrastructure.ai.haystack.components.legal_chunker import (
    LegalChunker,
)
from app.infrastructure.ai.haystack.components.citation_extractor import (
    CitationExtractor,
)
from app.infrastructure.ai.haystack.components.retrievers import (
    QdrantHybridRetriever,
    OpenSearchHybridRetriever,
)
from app.infrastructure.ai.haystack.components.ranker import (
    ReciprocalRankFusionRanker,
    ScoreThresholdFilter,
)
from app.infrastructure.ai.haystack.components.query_processor import (
    LegalQueryPreprocessor,
    QueryEmbedder,
    QuerySparseEncoder,
)
from app.infrastructure.ai.haystack.components.enricher import (
    ResultEnricher,
    HighlightExtractor,
)
# Indexing components
from app.infrastructure.ai.haystack.components.docling_converter import DoclingDocumentConverter
from app.infrastructure.ai.haystack.components.document_cleaner import LegalDocumentCleaner
from app.infrastructure.ai.haystack.components.embedders import (
    FastEmbedDocumentEmbedder,
    FastEmbedQueryEmbedder,
    SparseEmbedder,
)
from app.infrastructure.ai.haystack.components.transcript_converter import (
    TranscriptSegmentConverter,
    SpeakerAwareChunker,
)
from app.infrastructure.ai.haystack.components.communication_converter import (
    CommunicationConverter,
    ThreadGrouper,
)

__all__ = [
    # Converters
    "CellebriteConverter",
    "DoclingDocumentConverter",
    "TranscriptSegmentConverter",
    "CommunicationConverter",
    # Chunkers
    "LegalChunker",
    "SpeakerAwareChunker",
    "ThreadGrouper",
    # Extractors
    "CitationExtractor",
    # Retrievers
    "QdrantHybridRetriever",
    "OpenSearchHybridRetriever",
    # Rankers
    "ReciprocalRankFusionRanker",
    "ScoreThresholdFilter",
    # Query processors
    "LegalQueryPreprocessor",
    "QueryEmbedder",
    "QuerySparseEncoder",
    # Enrichers
    "ResultEnricher",
    "HighlightExtractor",
    # Document processing
    "LegalDocumentCleaner",
    # Embedders
    "FastEmbedDocumentEmbedder",
    "FastEmbedQueryEmbedder",
    "SparseEmbedder",
]
