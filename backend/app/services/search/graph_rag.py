"""
GraphRAG-Enhanced Search Engine

Combines vector search with graph traversal to:
1. Extract entities from queries and find related documents via Neo4j
2. Add citation chain metadata and boost highly-cited documents
3. Enhance search results with graph-based context
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.neo4j import Neo4jClient
from app.services.entity_service import EntityExtractionService
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class GraphRAGEngine:
    """
    GraphRAG engine that enhances vector search with knowledge graph traversal.

    Features:
    - Entity extraction from queries to find related documents
    - Citation chain analysis for document importance ranking
    - Graph-based context enrichment for search results
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        entity_service: EntityExtractionService
    ):
        """
        Initialize GraphRAG engine.

        Args:
            neo4j_client: Neo4j client for graph operations
            entity_service: Entity extraction service
        """
        self.neo4j = neo4j_client
        self.entity_service = entity_service
        logger.info("GraphRAG engine initialized")

    async def entity_enhanced_search(
        self,
        query: str,
        case_id: str,
        db: AsyncSession,
        max_hops: int = 1,
        min_confidence: float = 0.5
    ) -> List[str]:
        """
        Extract entities from query and find related documents via graph.

        This method:
        1. Extracts entities from the search query
        2. Finds related entities (1-hop in Neo4j)
        3. Finds documents mentioning these entities
        4. Returns document IDs to boost in vector search

        Args:
            query: Search query text
            case_id: Case ID to scope the search
            db: Database session
            max_hops: Maximum hops to traverse in graph (default: 1)
            min_confidence: Minimum entity confidence threshold (default: 0.5)

        Returns:
            List of document IDs to boost in search results
        """
        try:
            # Step 1: Extract entities from query using entity service
            logger.info(f"Extracting entities from query: {query[:100]}...")
            query_entities = await self.entity_service.extract_entities(
                document_id="query_temp",  # Temporary ID for query
                text=query,
                db=db
            )

            # Filter by confidence threshold
            high_confidence_entities = [
                e for e in query_entities
                if e.get("confidence", 0) >= min_confidence
            ]

            if not high_confidence_entities:
                logger.info("No high-confidence entities found in query")
                return []

            entity_texts = [e["text"] for e in high_confidence_entities]
            logger.info(f"Found {len(entity_texts)} entities: {entity_texts[:5]}")

            # Step 2: Find related entities via graph traversal (1-hop)
            related_entity_texts = set(entity_texts)  # Start with query entities

            for entity_text in entity_texts:
                try:
                    # Find co-occurring entities (1-hop in graph)
                    connections = self.neo4j.find_entity_connections(
                        entity_text=entity_text,
                        case_id=case_id
                    )

                    # Add related entities
                    co_occurring = connections.get("co_occurring_entities", [])
                    for co_entity in co_occurring[:10]:  # Limit to top 10 related
                        related_entity_texts.add(co_entity["entity"])

                except Exception as e:
                    logger.warning(f"Failed to find connections for entity '{entity_text}': {e}")
                    continue

            logger.info(
                f"Expanded to {len(related_entity_texts)} entities "
                f"(including related entities)"
            )

            # Step 3: Find documents mentioning these entities
            related_docs = self.neo4j.find_related_documents(
                entity_texts=list(related_entity_texts),
                case_id=case_id
            )

            # Extract document IDs and sort by number of matching entities
            doc_ids = [doc["doc_id"] for doc in related_docs]

            logger.info(
                f"Found {len(doc_ids)} documents related to entities "
                f"from query in case {case_id}"
            )

            return doc_ids

        except Exception as e:
            logger.error(f"Entity-enhanced search failed: {e}", exc_info=True)
            return []

    def add_citation_context(
        self,
        search_results: List[Dict],
        case_id: str,
        citation_boost_weight: float = 0.15
    ) -> List[Dict]:
        """
        Add citation chain metadata and boost highly-cited documents.

        This method:
        1. Gets citation chain from Neo4j for each result
        2. Calculates citation centrality (PageRank-like score)
        3. Boosts score based on citation importance
        4. Adds citation metadata to results

        Args:
            search_results: List of search results from vector search
            case_id: Case ID to scope citations
            citation_boost_weight: Weight for citation boost (0-1, default: 0.15)

        Returns:
            Search results with citation metadata and boosted scores
        """
        try:
            logger.info(f"Adding citation context to {len(search_results)} results")

            # Get citation statistics for the case
            case_graph = self.neo4j.get_case_graph(case_id)
            citations = case_graph.get("citations", [])

            # Build citation graph: doc_id -> {cited_by: [], cites: []}
            citation_graph = {}
            for citation in citations:
                from_doc = citation["from_doc"]
                to_doc = citation["to_doc"]

                # Initialize if not exists
                if from_doc not in citation_graph:
                    citation_graph[from_doc] = {"cited_by": [], "cites": []}
                if to_doc not in citation_graph:
                    citation_graph[to_doc] = {"cited_by": [], "cites": []}

                # Add citation relationships
                citation_graph[from_doc]["cites"].append(to_doc)
                citation_graph[to_doc]["cited_by"].append(from_doc)

            # Calculate citation centrality (simple PageRank approximation)
            citation_scores = self._calculate_citation_centrality(citation_graph)

            # Normalize citation scores to 0-1 range
            max_citation_score = max(citation_scores.values()) if citation_scores else 1.0
            if max_citation_score > 0:
                citation_scores = {
                    doc_id: score / max_citation_score
                    for doc_id, score in citation_scores.items()
                }

            # Enhance each result
            for result in search_results:
                # Extract document ID from result
                doc_id = self._extract_doc_id(result)
                if not doc_id:
                    continue

                # Get citation info
                citation_info = citation_graph.get(doc_id, {"cited_by": [], "cites": []})
                citation_score = citation_scores.get(doc_id, 0.0)

                # Calculate citation chain depth
                citation_chain = []
                if doc_id in citation_graph:
                    try:
                        chain_data = self.neo4j.find_citation_chain(doc_id, depth=3)
                        citation_chain = [
                            {
                                "depth": item.get("depth", 0),
                                "path_length": item.get("depth", 0)
                            }
                            for item in chain_data
                        ]
                    except Exception as e:
                        logger.warning(f"Failed to get citation chain for {doc_id}: {e}")

                # Add citation metadata
                citation_metadata = {
                    "cited_by_count": len(citation_info["cited_by"]),
                    "cites_count": len(citation_info["cites"]),
                    "citation_score": citation_score,
                    "citation_chain_depth": max(
                        [c["depth"] for c in citation_chain],
                        default=0
                    ),
                    "is_highly_cited": citation_score > 0.7,
                }

                # Add to result metadata
                if "metadata" not in result:
                    result["metadata"] = {}
                result["metadata"]["citation"] = citation_metadata

                # Boost score based on citation centrality
                original_score = result.get("score", 0.0)
                citation_boost = citation_score * citation_boost_weight
                boosted_score = original_score + citation_boost

                # Ensure score stays in valid range (0-1)
                result["score"] = min(1.0, boosted_score)

                # Track boost amount
                result["metadata"]["citation_boost"] = citation_boost

                logger.debug(
                    f"Document {doc_id}: cited_by={citation_metadata['cited_by_count']}, "
                    f"citation_score={citation_score:.3f}, "
                    f"boost={citation_boost:.3f}, "
                    f"score={original_score:.3f}->{result['score']:.3f}"
                )

            # Re-sort by boosted scores
            search_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)

            logger.info(
                f"Citation context added. "
                f"Avg boost: {sum(r.get('metadata', {}).get('citation_boost', 0) for r in search_results) / len(search_results):.3f}"
            )

            return search_results

        except Exception as e:
            logger.error(f"Failed to add citation context: {e}", exc_info=True)
            # Return original results if citation enhancement fails
            return search_results

    def _calculate_citation_centrality(
        self,
        citation_graph: Dict[str, Dict[str, List[str]]],
        damping_factor: float = 0.85,
        iterations: int = 10
    ) -> Dict[str, float]:
        """
        Calculate citation centrality using simplified PageRank algorithm.

        Args:
            citation_graph: Graph of citations {doc_id: {cited_by: [], cites: []}}
            damping_factor: PageRank damping factor (default: 0.85)
            iterations: Number of iterations (default: 10)

        Returns:
            Dictionary of document IDs to centrality scores
        """
        if not citation_graph:
            return {}

        # Initialize scores
        doc_ids = list(citation_graph.keys())
        num_docs = len(doc_ids)
        scores = {doc_id: 1.0 / num_docs for doc_id in doc_ids}

        # Iterative PageRank calculation
        for _ in range(iterations):
            new_scores = {}

            for doc_id in doc_ids:
                # Base score (random jump)
                base_score = (1 - damping_factor) / num_docs

                # Citation score (from documents citing this one)
                citation_score = 0.0
                cited_by = citation_graph[doc_id].get("cited_by", [])

                for citing_doc in cited_by:
                    if citing_doc in scores:
                        # Score from citing doc divided by its out-degree
                        citing_score = scores[citing_doc]
                        out_degree = len(citation_graph[citing_doc].get("cites", []))
                        if out_degree > 0:
                            citation_score += citing_score / out_degree

                # Combine base and citation scores
                new_scores[doc_id] = base_score + (damping_factor * citation_score)

            scores = new_scores

        return scores

    def _extract_doc_id(self, result: Dict[str, Any]) -> Optional[str]:
        """
        Extract document ID from search result.

        Args:
            result: Search result dictionary

        Returns:
            Document ID or None
        """
        # Try different possible locations for document ID
        doc_id = result.get("document_id")
        if doc_id:
            return str(doc_id)

        # Try metadata
        metadata = result.get("metadata", {})
        doc_id = metadata.get("document_id") or metadata.get("doc_id")
        if doc_id:
            return str(doc_id)

        # Try payload (Qdrant format)
        payload = result.get("payload", {})
        doc_id = payload.get("document_id") or payload.get("doc_id")
        if doc_id:
            return str(doc_id)

        return None


# Factory function for easy instantiation
def create_graph_rag_engine(
    neo4j_client: Neo4jClient,
    entity_service: EntityExtractionService
) -> GraphRAGEngine:
    """
    Create a GraphRAG engine instance.

    Args:
        neo4j_client: Neo4j client instance
        entity_service: Entity extraction service instance

    Returns:
        Configured GraphRAG engine
    """
    return GraphRAGEngine(
        neo4j_client=neo4j_client,
        entity_service=entity_service
    )
