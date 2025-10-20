"""
Haystack pipeline for hybrid document retrieval.

Implements production-ready hybrid search combining:
- BM25 keyword search (OpenSearch)
- Dense vector search (Qdrant)
- Reciprocal Rank Fusion (RRF)
- Query preprocessing and result enrichment
"""

import logging
from typing import List, Dict, Any, Optional
from enum import Enum

from haystack import Pipeline

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
)
from app.infrastructure.ai.haystack.components.enricher import (
    ResultEnricher,
    HighlightExtractor,
)

logger = logging.getLogger(__name__)


class SearchMode(str, Enum):
    """Search mode enumeration."""
    HYBRID = "hybrid"
    KEYWORD_ONLY = "keyword_only"
    SEMANTIC_ONLY = "semantic_only"


class HybridRetrievalPipeline:
    """
    Production hybrid retrieval pipeline.

    Pipeline flow (HYBRID mode):
    ```
    Query → Preprocessor → [Embedder → QdrantRetriever]
                        → [OpenSearchRetriever]
                        → RRFRanker → ScoreFilter → Enricher → HighlightExtractor → Results
    ```

    Features:
    - Multi-mode search (hybrid, keyword-only, semantic-only)
    - Legal query preprocessing
    - Reciprocal rank fusion
    - Score threshold filtering
    - Result enrichment with PostgreSQL metadata
    - Highlight extraction
    """

    def __init__(
        self,
        mode: SearchMode = SearchMode.HYBRID,
        top_k: int = 10,
        score_threshold: float = 0.3,
        rrf_k: int = 60,
        expand_synonyms: bool = True,
        enrich_results: bool = True,
    ):
        """
        Initialize hybrid retrieval pipeline.

        Args:
            mode: Search mode (hybrid, keyword_only, semantic_only)
            top_k: Number of results to return
            score_threshold: Minimum score threshold
            rrf_k: RRF k parameter for rank fusion
            expand_synonyms: Whether to expand legal synonyms
            enrich_results: Whether to enrich results with full metadata
        """
        self.mode = mode
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.rrf_k = rrf_k
        self.expand_synonyms = expand_synonyms
        self.enrich_results = enrich_results

        # Build pipeline based on mode
        self.pipeline = self._build_pipeline()

        logger.info(
            f"Initialized HybridRetrievalPipeline "
            f"(mode={mode}, top_k={top_k}, threshold={score_threshold})"
        )

    def _build_pipeline(self) -> Pipeline:
        """
        Build the Haystack pipeline based on search mode.

        Returns:
            Configured Haystack Pipeline
        """
        pipeline = Pipeline()

        # Add query preprocessor
        pipeline.add_component(
            "preprocessor",
            LegalQueryPreprocessor(
                expand_synonyms=self.expand_synonyms,
                preserve_citations=True,
                remove_common_stopwords=False,
            ),
        )

        if self.mode == SearchMode.HYBRID:
            # Hybrid mode: Both BM25 and dense search with RRF fusion

            # Add embedder for dense search
            pipeline.add_component(
                "embedder",
                QueryEmbedder(model_name="BAAI/bge-small-en-v1.5"),
            )

            # Add Qdrant dense retriever
            pipeline.add_component(
                "qdrant_retriever",
                QdrantHybridRetriever(
                    default_top_k=self.top_k * 2,  # Get more for fusion
                ),
            )

            # Add OpenSearch BM25 retriever
            pipeline.add_component(
                "opensearch_retriever",
                OpenSearchHybridRetriever(
                    default_top_k=self.top_k * 2,  # Get more for fusion
                ),
            )

            # Add RRF ranker
            pipeline.add_component(
                "ranker",
                ReciprocalRankFusionRanker(
                    rrf_k=self.rrf_k,
                    normalize_scores=True,
                    boost_keyword_matches=True,
                ),
            )

            # Connect components
            pipeline.connect("preprocessor.query", "embedder.query")
            pipeline.connect("embedder.embedding", "qdrant_retriever.query_embedding")
            pipeline.connect("preprocessor.query", "opensearch_retriever.query")
            pipeline.connect("opensearch_retriever.documents", "ranker.bm25_documents")
            pipeline.connect("qdrant_retriever.documents", "ranker.dense_documents")

            last_component = "ranker"

        elif self.mode == SearchMode.KEYWORD_ONLY:
            # Keyword-only mode: BM25 search only

            # Add OpenSearch BM25 retriever
            pipeline.add_component(
                "opensearch_retriever",
                OpenSearchHybridRetriever(
                    default_top_k=self.top_k * 2,
                ),
            )

            # Connect components
            pipeline.connect("preprocessor.query", "opensearch_retriever.query")

            last_component = "opensearch_retriever"

        elif self.mode == SearchMode.SEMANTIC_ONLY:
            # Semantic-only mode: Dense vector search only

            # Add embedder
            pipeline.add_component(
                "embedder",
                QueryEmbedder(model_name="BAAI/bge-small-en-v1.5"),
            )

            # Add Qdrant dense retriever
            pipeline.add_component(
                "qdrant_retriever",
                QdrantHybridRetriever(
                    default_top_k=self.top_k * 2,
                ),
            )

            # Connect components
            pipeline.connect("preprocessor.query", "embedder.query")
            pipeline.connect("embedder.embedding", "qdrant_retriever.query_embedding")

            last_component = "qdrant_retriever"

        # Add score threshold filter
        pipeline.add_component(
            "score_filter",
            ScoreThresholdFilter(score_threshold=self.score_threshold),
        )
        pipeline.connect(f"{last_component}.documents", "score_filter.documents")

        # Add result enricher (optional)
        if self.enrich_results:
            pipeline.add_component(
                "enricher",
                ResultEnricher(
                    fetch_surrounding_context=False,
                    format_citations=True,
                ),
            )
            pipeline.connect("score_filter.documents", "enricher.documents")
            last_component = "enricher"
        else:
            last_component = "score_filter"

        # Add highlight extractor
        pipeline.add_component(
            "highlighter",
            HighlightExtractor(
                max_highlights=3,
                context_words=10,
            ),
        )
        pipeline.connect(f"{last_component}.documents", "highlighter.documents")
        pipeline.connect("preprocessor.query", "highlighter.query")

        logger.info(f"Built {self.mode} pipeline with {len(pipeline.graph.nodes)} components")

        return pipeline

    async def run(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Run the hybrid retrieval pipeline.

        Args:
            query: Search query text
            filters: Optional metadata filters (case_ids, document_ids, chunk_types, evidence_types)
            top_k: Number of results to return (overrides default)
            score_threshold: Score threshold (overrides default)

        Returns:
            Pipeline results with documents and metadata
        """
        top_k = top_k or self.top_k
        score_threshold = score_threshold or self.score_threshold

        # Prepare pipeline inputs
        pipeline_inputs = {
            "preprocessor": {
                "query": query,
            },
        }

        # Add filters to retrievers
        if filters:
            if self.mode in [SearchMode.HYBRID, SearchMode.SEMANTIC_ONLY]:
                pipeline_inputs["qdrant_retriever"] = {
                    "filters": filters,
                    "top_k": top_k * 2,
                }

            if self.mode in [SearchMode.HYBRID, SearchMode.KEYWORD_ONLY]:
                pipeline_inputs["opensearch_retriever"] = {
                    "filters": filters,
                    "top_k": top_k * 2,
                }

        # Add score threshold
        pipeline_inputs["score_filter"] = {
            "score_threshold": score_threshold,
        }

        # Add top_k to ranker (hybrid mode only)
        if self.mode == SearchMode.HYBRID:
            pipeline_inputs["ranker"] = {
                "top_k": top_k,
            }

        logger.info(f"Running {self.mode} pipeline: query='{query}', filters={filters}")

        # Run pipeline
        try:
            result = await self.pipeline.run(pipeline_inputs)

            # Extract documents from result
            documents = result.get("highlighter", {}).get("documents", [])

            # Limit to top_k
            documents = documents[:top_k]

            logger.info(f"Pipeline returned {len(documents)} results")

            return {
                "documents": documents,
                "total_results": len(documents),
                "query": query,
                "mode": self.mode,
            }

        except Exception as e:
            logger.error(f"Pipeline execution error: {e}", exc_info=True)
            raise


def create_hybrid_search_pipeline(
    mode: SearchMode = SearchMode.HYBRID,
    top_k: int = 10,
    score_threshold: float = 0.3,
    **kwargs,
) -> HybridRetrievalPipeline:
    """
    Factory function to create a hybrid search pipeline.

    Args:
        mode: Search mode (hybrid, keyword_only, semantic_only)
        top_k: Number of results to return
        score_threshold: Minimum score threshold
        **kwargs: Additional pipeline configuration

    Returns:
        Configured HybridRetrievalPipeline
    """
    return HybridRetrievalPipeline(
        mode=mode,
        top_k=top_k,
        score_threshold=score_threshold,
        **kwargs,
    )


def create_keyword_only_pipeline(
    top_k: int = 10,
    score_threshold: float = 0.3,
    **kwargs,
) -> HybridRetrievalPipeline:
    """
    Factory function to create a keyword-only search pipeline.

    Args:
        top_k: Number of results to return
        score_threshold: Minimum score threshold
        **kwargs: Additional pipeline configuration

    Returns:
        Configured keyword-only pipeline
    """
    return HybridRetrievalPipeline(
        mode=SearchMode.KEYWORD_ONLY,
        top_k=top_k,
        score_threshold=score_threshold,
        **kwargs,
    )


def create_semantic_only_pipeline(
    top_k: int = 10,
    score_threshold: float = 0.3,
    **kwargs,
) -> HybridRetrievalPipeline:
    """
    Factory function to create a semantic-only search pipeline.

    Args:
        top_k: Number of results to return
        score_threshold: Minimum score threshold
        **kwargs: Additional pipeline configuration

    Returns:
        Configured semantic-only pipeline
    """
    return HybridRetrievalPipeline(
        mode=SearchMode.SEMANTIC_ONLY,
        top_k=top_k,
        score_threshold=score_threshold,
        **kwargs,
    )


# Example usage:
"""
from app.infrastructure.ai.haystack.pipelines.retrieval import (
    create_hybrid_search_pipeline,
    SearchMode,
)

# Create hybrid pipeline
pipeline = create_hybrid_search_pipeline(
    mode=SearchMode.HYBRID,
    top_k=20,
    score_threshold=0.4,
)

# Run search
results = await pipeline.run(
    query="contract breach liability damages",
    filters={
        "case_ids": ["uuid1", "uuid2"],
        "chunk_types": ["summary", "section"],
        "evidence_types": ["documents", "transcripts"],
    },
)

# Access results
for doc in results["documents"]:
    print(f"Score: {doc.score:.3f} - {doc.content[:100]}")
    print(f"Citation: {doc.meta.get('citation')}")
    print(f"Match type: {doc.meta.get('match_type')}")
"""
