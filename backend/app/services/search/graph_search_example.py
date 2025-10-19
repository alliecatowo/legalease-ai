"""
Example: Using Graph-Enhanced Search

This example demonstrates how to use the graph-enhanced search engine
to leverage knowledge graphs for better search results.
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.schemas.search import HybridSearchRequest
from app.services.search.graph_enhanced_search import get_graph_enhanced_search_engine
from app.core.config import settings


async def example_basic_graph_search():
    """
    Example 1: Basic graph-enhanced search with entity boosting.

    This example shows how entity extraction and graph traversal
    can improve search results for legal queries.
    """
    print("\n=== Example 1: Basic Graph-Enhanced Search ===\n")

    # Create search request
    request = HybridSearchRequest(
        query="contract dispute between ABC Corp and XYZ Ltd",
        use_bm25=True,
        use_dense=True,
        fusion_method="rrf",
        top_k=10,
        score_threshold=0.3,
        case_ids=["550e8400-e29b-41d4-a716-446655440000"]  # Example case ID
    )

    # Get graph-enhanced search engine
    search_engine = get_graph_enhanced_search_engine()

    # Create database session
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as db:
        # Perform graph-enhanced search
        response = await search_engine.search(
            request=request,
            db=db,
            entity_expansion_strategy="co_occurrence",  # Expand via co-occurring entities
            max_entity_hops=2  # Traverse 2 hops in graph
        )

        # Display results
        print(f"Query: {response.query}")
        print(f"Total results: {response.total_results}")
        print(f"\nGraph enhancement metadata:")
        print(f"  Entity boost: {response.search_metadata.get('graph_enhancement', {}).get('entity_boost_enabled')}")
        print(f"  Citation boost: {response.search_metadata.get('graph_enhancement', {}).get('citation_boost_enabled')}")
        print(f"\nTop 5 results:")

        for i, result in enumerate(response.results[:5], 1):
            print(f"\n{i}. Score: {result.score:.4f}")
            print(f"   Match type: {result.match_type}")
            print(f"   Text: {result.text[:100]}...")

            # Show graph boosting details
            if result.metadata:
                entity_boost = result.metadata.get("entity_boost", 0)
                citation_boost = result.metadata.get("citation_boost", 0)
                entity_matched = result.metadata.get("entity_matched", False)

                if entity_boost > 0:
                    print(f"   Entity boost: +{entity_boost:.4f}")
                if citation_boost > 0:
                    print(f"   Citation boost: +{citation_boost:.4f}")
                if entity_matched:
                    print(f"   Matched entities: {result.metadata.get('query_entities', [])}")


async def example_citation_focused_search():
    """
    Example 2: Citation-focused search.

    This example emphasizes citation network analysis to find
    highly-cited and authoritative documents.
    """
    print("\n=== Example 2: Citation-Focused Search ===\n")

    request = HybridSearchRequest(
        query="legal precedent for breach of contract",
        use_bm25=True,
        use_dense=True,
        fusion_method="rrf",
        top_k=10,
        case_ids=["550e8400-e29b-41d4-a716-446655440000"]
    )

    # Create search engine with higher citation boost weight
    from app.services.search.graph_enhanced_search import create_graph_enhanced_search_engine

    search_engine = create_graph_enhanced_search_engine(
        enable_entity_boost=True,
        enable_citation_boost=True,
        entity_boost_weight=0.10,  # Lower entity weight
        citation_boost_weight=0.30  # Higher citation weight
    )

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as db:
        response = await search_engine.search(request=request, db=db)

        print(f"Query: {response.query}")
        print(f"Total results: {response.total_results}\n")

        for i, result in enumerate(response.results[:5], 1):
            print(f"\n{i}. Score: {result.score:.4f}")

            # Show citation network details
            if result.metadata:
                citation_data = result.metadata.get("citation", {})
                if citation_data:
                    print(f"   Cited by: {citation_data.get('cited_by_count', 0)} documents")
                    print(f"   Cites: {citation_data.get('cites_count', 0)} documents")
                    print(f"   Citation score: {citation_data.get('citation_score', 0):.4f}")
                    print(f"   Highly cited: {citation_data.get('is_highly_cited', False)}")


async def example_entity_expansion_strategies():
    """
    Example 3: Comparing entity expansion strategies.

    Demonstrates the difference between co-occurrence and citation-based
    entity expansion.
    """
    print("\n=== Example 3: Entity Expansion Strategies ===\n")

    request = HybridSearchRequest(
        query="patent infringement lawsuit",
        use_bm25=True,
        use_dense=True,
        top_k=10,
        case_ids=["550e8400-e29b-41d4-a716-446655440000"]
    )

    search_engine = get_graph_enhanced_search_engine()

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as db:
        # Strategy 1: Co-occurrence
        print("\nStrategy 1: Co-occurrence entity expansion")
        response1 = await search_engine.search(
            request=request,
            db=db,
            entity_expansion_strategy="co_occurrence",
            max_entity_hops=2
        )
        print(f"  Results: {response1.total_results}")

        # Strategy 2: Citation chain
        print("\nStrategy 2: Citation-chain entity expansion")
        response2 = await search_engine.search(
            request=request,
            db=db,
            entity_expansion_strategy="citation_chain",
            max_entity_hops=2
        )
        print(f"  Results: {response2.total_results}")

        # Compare top results
        print("\n  Comparison of top 3 results:")
        print("  Co-occurrence:")
        for i, result in enumerate(response1.results[:3], 1):
            print(f"    {i}. {result.score:.4f} - {result.text[:60]}...")

        print("\n  Citation-chain:")
        for i, result in enumerate(response2.results[:3], 1):
            print(f"    {i}. {result.score:.4f} - {result.text[:60]}...")


async def example_pure_vector_vs_graph_enhanced():
    """
    Example 4: Pure vector search vs graph-enhanced search.

    Shows the improvement from adding graph signals.
    """
    print("\n=== Example 4: Vector Search vs Graph-Enhanced ===\n")

    from app.services.search.engine import get_search_engine

    request = HybridSearchRequest(
        query="employment contract termination clause",
        use_bm25=True,
        use_dense=True,
        top_k=5,
        case_ids=["550e8400-e29b-41d4-a716-446655440000"]
    )

    # Pure vector search
    print("\nPure Vector Search:")
    vector_engine = get_search_engine()
    vector_response = vector_engine.search(request)

    print(f"  Results: {vector_response.total_results}")
    for i, result in enumerate(vector_response.results, 1):
        print(f"  {i}. Score: {result.score:.4f}")

    # Graph-enhanced search
    print("\nGraph-Enhanced Search:")
    graph_engine = get_graph_enhanced_search_engine()

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as db:
        graph_response = await graph_engine.search(request=request, db=db)

        print(f"  Results: {graph_response.total_results}")
        for i, result in enumerate(graph_response.results, 1):
            entity_boost = result.metadata.get("entity_boost", 0) if result.metadata else 0
            citation_boost = result.metadata.get("citation_boost", 0) if result.metadata else 0
            total_boost = entity_boost + citation_boost

            print(f"  {i}. Score: {result.score:.4f} (+{total_boost:.4f} from graph)")


async def example_api_endpoint_usage():
    """
    Example 5: How to use in FastAPI endpoint.

    This shows the recommended pattern for integrating graph-enhanced
    search into your API endpoints.
    """
    print("\n=== Example 5: FastAPI Endpoint Pattern ===\n")

    print("""
# In your FastAPI router:

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.search import HybridSearchRequest, HybridSearchResponse
from app.services.search.graph_enhanced_search import get_graph_enhanced_search_engine

router = APIRouter()

@router.post("/search/graph-enhanced", response_model=HybridSearchResponse)
async def graph_enhanced_search(
    request: HybridSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    \"\"\"
    Perform graph-enhanced search with entity and citation boosting.

    This endpoint combines:
    - Hybrid vector search (BM25 + Dense + Fusion)
    - Entity extraction and graph traversal
    - Citation network analysis
    \"\"\"
    search_engine = get_graph_enhanced_search_engine()

    response = await search_engine.search(
        request=request,
        db=db,
        entity_expansion_strategy="co_occurrence",
        max_entity_hops=2
    )

    return response

# Optional: Add configuration endpoint
@router.post("/search/graph-enhanced/custom", response_model=HybridSearchResponse)
async def custom_graph_search(
    request: HybridSearchRequest,
    db: AsyncSession = Depends(get_db),
    entity_boost_weight: float = 0.20,
    citation_boost_weight: float = 0.15,
    entity_expansion_strategy: str = "co_occurrence",
    max_entity_hops: int = 2
):
    \"\"\"
    Graph-enhanced search with custom boost weights.
    \"\"\"
    from app.services.search.graph_enhanced_search import create_graph_enhanced_search_engine

    search_engine = create_graph_enhanced_search_engine(
        enable_entity_boost=True,
        enable_citation_boost=True,
        entity_boost_weight=entity_boost_weight,
        citation_boost_weight=citation_boost_weight
    )

    response = await search_engine.search(
        request=request,
        db=db,
        entity_expansion_strategy=entity_expansion_strategy,
        max_entity_hops=max_entity_hops
    )

    return response
    """)


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("Graph-Enhanced Search Examples")
    print("="*60)

    # Run examples
    await example_basic_graph_search()
    await example_citation_focused_search()
    await example_entity_expansion_strategies()
    await example_pure_vector_vs_graph_enhanced()
    await example_api_endpoint_usage()

    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
