"""
Example usage of GraphRAG engine.

This demonstrates how to integrate GraphRAG with your search pipeline.
"""

from typing import List, Dict, Any
import asyncio

from app.core.neo4j import neo4j_client
from app.services.entity_service import entity_service
from app.services.search.graph_rag import create_graph_rag_engine


async def example_entity_enhanced_search():
    """
    Example: Using entity extraction to find related documents.
    """
    # Create GraphRAG engine
    graph_rag = create_graph_rag_engine(
        neo4j_client=neo4j_client,
        entity_service=entity_service
    )

    # Mock database session (replace with actual session)
    db = None  # You would get this from get_db() dependency

    # Example query
    query = "John Doe filed a motion in the California Superior Court"
    case_id = "case-123"

    # Get entity-enhanced document IDs
    try:
        doc_ids = await graph_rag.entity_enhanced_search(
            query=query,
            case_id=case_id,
            db=db,
            max_hops=1,
            min_confidence=0.5
        )

        print(f"Found {len(doc_ids)} documents related to entities in query:")
        print(f"Document IDs: {doc_ids[:10]}")  # Show first 10

        # These doc_ids can be used to:
        # 1. Filter vector search results
        # 2. Boost scores of these documents
        # 3. Ensure they appear in results even if vector score is lower

    except Exception as e:
        print(f"Error in entity-enhanced search: {e}")


def example_citation_enhancement():
    """
    Example: Adding citation context to search results.
    """
    # Create GraphRAG engine
    graph_rag = create_graph_rag_engine(
        neo4j_client=neo4j_client,
        entity_service=entity_service
    )

    # Mock search results (from your vector search)
    search_results = [
        {
            "id": "chunk-1",
            "score": 0.85,
            "document_id": "doc-123",
            "text": "This is a sample document...",
            "metadata": {
                "document_id": "doc-123",
                "case_id": "case-123"
            }
        },
        {
            "id": "chunk-2",
            "score": 0.78,
            "document_id": "doc-456",
            "text": "Another document...",
            "metadata": {
                "document_id": "doc-456",
                "case_id": "case-123"
            }
        }
    ]

    case_id = "case-123"

    # Add citation context and boost scores
    enhanced_results = graph_rag.add_citation_context(
        search_results=search_results,
        case_id=case_id,
        citation_boost_weight=0.15
    )

    print("Enhanced results with citation context:")
    for result in enhanced_results:
        citation = result.get("metadata", {}).get("citation", {})
        print(f"  Document {result['document_id']}:")
        print(f"    Score: {result['score']:.3f}")
        print(f"    Cited by: {citation.get('cited_by_count', 0)} documents")
        print(f"    Cites: {citation.get('cites_count', 0)} documents")
        print(f"    Citation score: {citation.get('citation_score', 0):.3f}")
        print(f"    Highly cited: {citation.get('is_highly_cited', False)}")
        print()


async def example_integrated_search():
    """
    Example: Full integration with hybrid search.
    """
    from app.services.search.engine import get_search_engine
    from app.schemas.search import HybridSearchRequest

    # Get search engine
    search_engine = get_search_engine()

    # Create GraphRAG engine
    graph_rag = create_graph_rag_engine(
        neo4j_client=neo4j_client,
        entity_service=entity_service
    )

    # Mock database session
    db = None  # Replace with actual session

    # Search parameters
    query = "contract dispute between parties"
    case_id = "case-123"

    # Step 1: Get entity-enhanced document IDs
    entity_doc_ids = await graph_rag.entity_enhanced_search(
        query=query,
        case_id=case_id,
        db=db
    )

    # Step 2: Perform hybrid search with entity filtering/boosting
    search_request = HybridSearchRequest(
        query=query,
        case_ids=[case_id],
        document_ids=entity_doc_ids,  # Focus on entity-related docs
        use_bm25=True,
        use_dense=True,
        fusion_method="rrf",
        top_k=50
    )

    search_response = search_engine.search(search_request)

    # Step 3: Add citation context to results
    enhanced_results = graph_rag.add_citation_context(
        search_results=[r.dict() for r in search_response.results],
        case_id=case_id
    )

    print(f"Integrated search returned {len(enhanced_results)} results")
    print(f"Top result: {enhanced_results[0]['text'][:100]}...")


if __name__ == "__main__":
    print("GraphRAG Engine Examples")
    print("=" * 60)

    print("\n1. Citation Enhancement Example:")
    print("-" * 60)
    example_citation_enhancement()

    # Note: Entity-enhanced search requires async context
    # Uncomment to run async examples:
    # print("\n2. Entity-Enhanced Search Example:")
    # print("-" * 60)
    # asyncio.run(example_entity_enhanced_search())

    # print("\n3. Integrated Search Example:")
    # print("-" * 60)
    # asyncio.run(example_integrated_search())
