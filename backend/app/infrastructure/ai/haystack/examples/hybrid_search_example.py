"""
Hybrid Search Integration Example

Demonstrates how to use the Haystack hybrid retrieval pipeline
to search legal documents with BM25 + dense vector + RRF.
"""

import asyncio
import logging
from typing import List, Dict, Any

from app.infrastructure.ai.haystack.pipelines.retrieval import (
    create_hybrid_search_pipeline,
    create_keyword_only_pipeline,
    create_semantic_only_pipeline,
    SearchMode,
)
from app.schemas.search import HybridSearchResponse, SearchResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def example_hybrid_search():
    """Example: Full hybrid search with BM25 + dense + RRF."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 1: Hybrid Search (BM25 + Dense + RRF)")
    logger.info("=" * 80)

    # Create hybrid pipeline
    pipeline = create_hybrid_search_pipeline(
        mode=SearchMode.HYBRID,
        top_k=10,
        score_threshold=0.3,
        rrf_k=60,
        expand_synonyms=True,
        enrich_results=True,
    )

    # Run search
    results = await pipeline.run(
        query="contract breach liability damages",
        filters={
            "case_ids": ["case-uuid-1", "case-uuid-2"],
            "chunk_types": ["summary", "section"],
            "evidence_types": ["documents"],
        },
        top_k=10,
    )

    # Display results
    logger.info(f"\nQuery: {results['query']}")
    logger.info(f"Mode: {results['mode']}")
    logger.info(f"Total results: {results['total_results']}\n")

    for i, doc in enumerate(results["documents"], 1):
        logger.info(f"Result {i}:")
        logger.info(f"  Score: {doc.score:.3f}")
        logger.info(f"  Match type: {doc.meta.get('match_type')}")
        logger.info(f"  BM25 score: {doc.meta.get('bm25_score', 0):.3f}")
        logger.info(f"  Dense score: {doc.meta.get('dense_score', 0):.3f}")
        logger.info(f"  Text: {doc.content[:100]}...")
        logger.info(f"  Citation: {doc.meta.get('citation')}")
        logger.info(f"  Highlights: {doc.meta.get('highlights', [])[:2]}")
        logger.info("")

    return results


async def example_keyword_only_search():
    """Example: Keyword-only search (BM25 only)."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 2: Keyword-Only Search (BM25)")
    logger.info("=" * 80)

    # Create keyword-only pipeline
    pipeline = create_keyword_only_pipeline(
        top_k=10,
        score_threshold=0.3,
    )

    # Run search
    results = await pipeline.run(
        query="employment discrimination wrongful termination",
        filters={
            "evidence_types": ["documents", "transcripts"],
        },
    )

    # Display results
    logger.info(f"\nQuery: {results['query']}")
    logger.info(f"Mode: {results['mode']}")
    logger.info(f"Total results: {results['total_results']}\n")

    for i, doc in enumerate(results["documents"], 1):
        logger.info(f"Result {i}: Score={doc.score:.3f}, Text={doc.content[:80]}...")

    return results


async def example_semantic_only_search():
    """Example: Semantic-only search (dense vectors only)."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 3: Semantic-Only Search (Dense Vectors)")
    logger.info("=" * 80)

    # Create semantic-only pipeline
    pipeline = create_semantic_only_pipeline(
        top_k=10,
        score_threshold=0.3,
    )

    # Run search
    results = await pipeline.run(
        query="legal responsibilities of corporate officers",
        filters={
            "chunk_types": ["summary", "section"],
        },
    )

    # Display results
    logger.info(f"\nQuery: {results['query']}")
    logger.info(f"Mode: {results['mode']}")
    logger.info(f"Total results: {results['total_results']}\n")

    for i, doc in enumerate(results["documents"], 1):
        logger.info(f"Result {i}: Score={doc.score:.3f}, Text={doc.content[:80]}...")

    return results


async def example_compare_modes():
    """Example: Compare different search modes for the same query."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 4: Compare Search Modes")
    logger.info("=" * 80)

    query = "negligence malpractice liability"

    # Create pipelines
    hybrid_pipeline = create_hybrid_search_pipeline(top_k=5)
    keyword_pipeline = create_keyword_only_pipeline(top_k=5)
    semantic_pipeline = create_semantic_only_pipeline(top_k=5)

    # Run searches
    hybrid_results = await hybrid_pipeline.run(query=query)
    keyword_results = await keyword_pipeline.run(query=query)
    semantic_results = await semantic_pipeline.run(query=query)

    # Compare results
    logger.info(f"\nQuery: {query}\n")

    logger.info("Hybrid Search Results:")
    for i, doc in enumerate(hybrid_results["documents"], 1):
        logger.info(f"  {i}. Score={doc.score:.3f}, Match={doc.meta.get('match_type')}")

    logger.info("\nKeyword-Only Results:")
    for i, doc in enumerate(keyword_results["documents"], 1):
        logger.info(f"  {i}. Score={doc.score:.3f}")

    logger.info("\nSemantic-Only Results:")
    for i, doc in enumerate(semantic_results["documents"], 1):
        logger.info(f"  {i}. Score={doc.score:.3f}")


def convert_to_api_response(haystack_results: Dict[str, Any]) -> HybridSearchResponse:
    """
    Convert Haystack pipeline results to API response format.

    Args:
        haystack_results: Results from HybridRetrievalPipeline.run()

    Returns:
        HybridSearchResponse compatible with existing API
    """
    documents = haystack_results.get("documents", [])

    # Convert to SearchResult objects
    search_results = []
    for doc in documents:
        meta = doc.meta or {}

        search_results.append(
            SearchResult(
                id=doc.id,
                gid=doc.id,
                score=doc.score or 0.0,
                text=doc.content,
                match_type=meta.get("match_type", "semantic"),
                page_number=meta.get("page_number"),
                bboxes=meta.get("bboxes", []),
                metadata={
                    "document_id": meta.get("document_id"),
                    "document_gid": meta.get("document_gid"),
                    "case_id": meta.get("case_id"),
                    "case_gid": meta.get("case_gid"),
                    "chunk_type": meta.get("chunk_type"),
                    "position": meta.get("position"),
                    "bm25_score": meta.get("bm25_score", 0.0),
                    "dense_score": meta.get("dense_score", 0.0),
                    "score_debug": meta.get("score_debug"),
                    "citation": meta.get("citation"),
                },
                highlights=meta.get("highlights"),
                vector_type=meta.get("chunk_type"),
            )
        )

    # Build response
    response = HybridSearchResponse(
        results=search_results,
        total_results=len(search_results),
        query=haystack_results.get("query", ""),
        search_metadata={
            "mode": str(haystack_results.get("mode", "hybrid")),
            "search_time_ms": 0,  # Add timing if needed
            "pipeline": "haystack",
        },
    )

    return response


async def example_api_integration():
    """Example: Integration with existing API response format."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 5: API Integration")
    logger.info("=" * 80)

    # Create pipeline
    pipeline = create_hybrid_search_pipeline(top_k=5)

    # Run search
    haystack_results = await pipeline.run(
        query="contract termination clause",
        filters={"chunk_types": ["section", "microblock"]},
    )

    # Convert to API response
    api_response = convert_to_api_response(haystack_results)

    logger.info(f"\nAPI Response:")
    logger.info(f"  Total results: {api_response.total_results}")
    logger.info(f"  Query: {api_response.query}")
    logger.info(f"  Metadata: {api_response.search_metadata}")
    logger.info(f"\n  First result:")
    if api_response.results:
        first = api_response.results[0]
        logger.info(f"    Score: {first.score:.3f}")
        logger.info(f"    Match type: {first.match_type}")
        logger.info(f"    Text: {first.text[:100]}...")


async def example_advanced_filters():
    """Example: Advanced filtering options."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 6: Advanced Filters")
    logger.info("=" * 80)

    pipeline = create_hybrid_search_pipeline()

    # Filter by multiple criteria
    results = await pipeline.run(
        query="discovery objection",
        filters={
            # Filter by specific cases
            "case_ids": ["case-1", "case-2"],

            # Filter by specific documents
            "document_ids": ["doc-1", "doc-2", "doc-3"],

            # Filter by chunk types
            "chunk_types": ["summary", "section"],  # Exclude microblocks

            # Filter by evidence types
            "evidence_types": ["documents", "transcripts"],  # Exclude communications
        },
        top_k=10,
        score_threshold=0.4,  # Higher threshold for more relevant results
    )

    logger.info(f"\nResults with advanced filters: {len(results['documents'])}")


async def example_query_preprocessing():
    """Example: Query preprocessing features."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 7: Query Preprocessing")
    logger.info("=" * 80)

    pipeline = create_hybrid_search_pipeline(expand_synonyms=True)

    # Query with legal terms that will be expanded
    original_query = "attorney malpractice contract breach"

    results = await pipeline.run(query=original_query)

    logger.info(f"\nOriginal query: {original_query}")
    logger.info("Synonyms expanded:")
    logger.info("  attorney → [lawyer, counsel]")
    logger.info("  contract → [agreement]")
    logger.info("  breach → [violation, infringement]")
    logger.info(f"\nResults: {len(results['documents'])}")


async def main():
    """Run all examples."""
    try:
        # Example 1: Full hybrid search
        await example_hybrid_search()
        await asyncio.sleep(1)

        # Example 2: Keyword-only
        await example_keyword_only_search()
        await asyncio.sleep(1)

        # Example 3: Semantic-only
        await example_semantic_only_search()
        await asyncio.sleep(1)

        # Example 4: Compare modes
        await example_compare_modes()
        await asyncio.sleep(1)

        # Example 5: API integration
        await example_api_integration()
        await asyncio.sleep(1)

        # Example 6: Advanced filters
        await example_advanced_filters()
        await asyncio.sleep(1)

        # Example 7: Query preprocessing
        await example_query_preprocessing()

    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
