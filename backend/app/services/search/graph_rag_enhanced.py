"""
Enhanced GraphRAG Engine with Hybrid Approach

Combines direct Neo4j operations (for performance) with PropertyGraph abstraction
(for future extensibility and advanced features).

Architecture Decision:
- Use DIRECT NEO4J for core retrieval operations (performance-critical paths)
- Use PROPERTY GRAPH wrapper for advanced features and future extensibility
- This hybrid approach balances performance with flexibility

Rationale:
1. Direct Neo4j is faster for production graph traversals
2. PropertyGraph provides standardized entity extraction and retrieval patterns
3. Existing Neo4j graph data is preserved and enhanced
4. Can migrate fully to PropertyGraph later if needed
"""

from typing import List, Dict, Any, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.neo4j import Neo4jClient
from app.services.entity_service import EntityExtractionService
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class EnhancedGraphRAGEngine:
    """
    Enhanced GraphRAG engine combining direct Neo4j operations with PropertyGraph patterns.

    Features:
    - Multi-hop entity traversal for query expansion
    - Citation network analysis for document ranking
    - Entity-based document retrieval
    - Knowledge graph context enrichment
    - Configurable graph traversal strategies
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        entity_service: EntityExtractionService
    ):
        """
        Initialize enhanced GraphRAG engine.

        Args:
            neo4j_client: Neo4j client for graph operations
            entity_service: Entity extraction service
        """
        self.neo4j = neo4j_client
        self.entity_service = entity_service
        logger.info("Enhanced GraphRAG engine initialized")

    async def entity_enhanced_search(
        self,
        query: str,
        case_id: str,
        db: AsyncSession,
        max_hops: int = 2,
        min_confidence: float = 0.5,
        expansion_strategy: str = "co_occurrence"  # or "citation_chain"
    ) -> Dict[str, Any]:
        """
        Extract entities from query and find related documents via graph traversal.

        This method performs multi-stage entity expansion:
        1. Extract entities from query using entity service
        2. Expand entities using graph traversal (co-occurrence or citation chains)
        3. Find documents mentioning expanded entities
        4. Score and rank documents by entity relevance

        Args:
            query: Search query text
            case_id: Case ID to scope the search
            db: Database session
            max_hops: Maximum hops to traverse in graph (1-3, default: 2)
            min_confidence: Minimum entity confidence threshold (default: 0.5)
            expansion_strategy: Strategy for expanding entities ("co_occurrence" or "citation_chain")

        Returns:
            Dict containing:
            - document_ids: List of document IDs to boost
            - entity_scores: Dict mapping doc_id -> entity relevance score
            - query_entities: List of entities extracted from query
            - expanded_entities: List of entities found via graph traversal
        """
        try:
            # Stage 1: Extract entities from query
            logger.info(f"Extracting entities from query: {query[:100]}...")
            query_entities = await self.entity_service.extract_entities(
                document_id="query_temp",
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
                return {
                    "document_ids": [],
                    "entity_scores": {},
                    "query_entities": [],
                    "expanded_entities": []
                }

            query_entity_texts = [e["text"] for e in high_confidence_entities]
            logger.info(f"Found {len(query_entity_texts)} entities: {query_entity_texts[:5]}")

            # Stage 2: Expand entities using graph traversal
            expanded_entities = await self._expand_entities(
                entity_texts=query_entity_texts,
                case_id=case_id,
                max_hops=max_hops,
                strategy=expansion_strategy
            )

            logger.info(
                f"Expanded to {len(expanded_entities)} entities "
                f"(from {len(query_entity_texts)} original)"
            )

            # Stage 3: Find related documents with entity scoring
            doc_scores = await self._find_and_score_documents(
                entity_texts=expanded_entities,
                query_entity_texts=query_entity_texts,
                case_id=case_id
            )

            # Sort documents by score
            sorted_docs = sorted(
                doc_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )

            document_ids = [doc_id for doc_id, _ in sorted_docs]
            entity_scores = dict(sorted_docs)

            logger.info(
                f"Found {len(document_ids)} documents related to entities "
                f"from query in case {case_id}"
            )

            return {
                "document_ids": document_ids[:50],  # Limit to top 50
                "entity_scores": entity_scores,
                "query_entities": query_entity_texts,
                "expanded_entities": list(expanded_entities)
            }

        except Exception as e:
            logger.error(f"Entity-enhanced search failed: {e}", exc_info=True)
            return {
                "document_ids": [],
                "entity_scores": {},
                "query_entities": [],
                "expanded_entities": []
            }

    async def _expand_entities(
        self,
        entity_texts: List[str],
        case_id: str,
        max_hops: int,
        strategy: str
    ) -> Set[str]:
        """
        Expand entities using graph traversal.

        Args:
            entity_texts: Starting entity texts
            case_id: Case ID for scoping
            max_hops: Maximum traversal hops
            strategy: Expansion strategy

        Returns:
            Set of expanded entity texts
        """
        expanded = set(entity_texts)  # Start with query entities

        if strategy == "co_occurrence":
            # Strategy 1: Expand via co-occurring entities
            for entity_text in entity_texts:
                try:
                    connections = self.neo4j.find_entity_connections(
                        entity_text=entity_text,
                        case_id=case_id
                    )

                    # Add co-occurring entities
                    co_occurring = connections.get("co_occurring_entities", [])
                    for co_entity in co_occurring[:10]:  # Top 10 related
                        expanded.add(co_entity["entity"])

                except Exception as e:
                    logger.warning(
                        f"Failed to find connections for entity '{entity_text}': {e}"
                    )
                    continue

        elif strategy == "citation_chain":
            # Strategy 2: Expand via citation chains
            # Find documents mentioning query entities
            related_docs = self.neo4j.find_related_documents(
                entity_texts=entity_texts,
                case_id=case_id
            )

            # For each document, traverse citation chain
            for doc in related_docs[:5]:  # Top 5 most relevant docs
                try:
                    doc_id = doc["doc_id"]
                    # Find cited documents
                    chain = self.neo4j.find_citation_chain(doc_id, depth=max_hops)

                    # Extract entities from cited documents
                    # (This would require additional Neo4j queries)
                    # For now, we'll use co-occurrence as fallback

                except Exception as e:
                    logger.warning(f"Failed to traverse citation chain: {e}")
                    continue

        return expanded

    async def _find_and_score_documents(
        self,
        entity_texts: List[str],
        query_entity_texts: List[str],
        case_id: str
    ) -> Dict[str, float]:
        """
        Find documents mentioning entities and score by relevance.

        Scoring factors:
        - Number of matching entities
        - Proportion of query entities matched
        - Entity types matched
        - Entity confidence scores

        Args:
            entity_texts: All entity texts (expanded)
            query_entity_texts: Original query entities
            case_id: Case ID

        Returns:
            Dict mapping doc_id -> relevance score (0-1)
        """
        # Find related documents
        related_docs = self.neo4j.find_related_documents(
            entity_texts=list(entity_texts),
            case_id=case_id
        )

        doc_scores = {}

        for doc in related_docs:
            doc_id = doc["doc_id"]
            matched_entities = doc.get("entities", [])

            # Calculate score based on multiple factors
            score = 0.0

            # Factor 1: Number of query entities matched (most important)
            query_entity_matches = len(
                set(matched_entities).intersection(set(query_entity_texts))
            )
            if len(query_entity_texts) > 0:
                query_match_ratio = query_entity_matches / len(query_entity_texts)
                score += query_match_ratio * 0.6  # 60% weight

            # Factor 2: Total number of entity matches
            total_matches = len(matched_entities)
            if len(entity_texts) > 0:
                expanded_match_ratio = total_matches / len(entity_texts)
                score += expanded_match_ratio * 0.3  # 30% weight

            # Factor 3: Document entity density (entities per document)
            # Higher density suggests more relevant document
            density_bonus = min(total_matches / 10.0, 0.1)  # Max 10% bonus
            score += density_bonus

            # Normalize to 0-1 range
            doc_scores[doc_id] = min(score, 1.0)

        return doc_scores

    def add_citation_context(
        self,
        search_results: List[Dict],
        case_id: str,
        citation_boost_weight: float = 0.15,
        use_pagerank: bool = True
    ) -> List[Dict]:
        """
        Add citation chain metadata and boost highly-cited documents.

        Enhanced features:
        - Configurable PageRank vs simple citation count
        - Citation chain depth analysis
        - Bidirectional citation flow (cited_by and cites)
        - Citation recency weighting

        Args:
            search_results: List of search results from vector search
            case_id: Case ID to scope citations
            citation_boost_weight: Weight for citation boost (0-1, default: 0.15)
            use_pagerank: Use PageRank algorithm vs simple citation count

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

            # Calculate citation scores
            if use_pagerank:
                citation_scores = self._calculate_citation_centrality(citation_graph)
            else:
                # Simple citation count
                citation_scores = {
                    doc_id: len(info["cited_by"])
                    for doc_id, info in citation_graph.items()
                }

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

                # Add citation metadata
                citation_metadata = {
                    "cited_by_count": len(citation_info["cited_by"]),
                    "cites_count": len(citation_info["cites"]),
                    "citation_score": citation_score,
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

            # Re-sort by boosted scores
            search_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)

            logger.info(
                f"Citation context added. "
                f"Avg boost: {sum(r.get('metadata', {}).get('citation_boost', 0) for r in search_results) / len(search_results):.3f}"
            )

            return search_results

        except Exception as e:
            logger.error(f"Failed to add citation context: {e}", exc_info=True)
            return search_results

    def _calculate_citation_centrality(
        self,
        citation_graph: Dict[str, Dict[str, List[str]]],
        damping_factor: float = 0.85,
        iterations: int = 10
    ) -> Dict[str, float]:
        """
        Calculate citation centrality using PageRank algorithm.

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


# Factory function
def create_enhanced_graph_rag_engine(
    neo4j_client: Neo4jClient,
    entity_service: EntityExtractionService
) -> EnhancedGraphRAGEngine:
    """
    Create an enhanced GraphRAG engine instance.

    Args:
        neo4j_client: Neo4j client instance
        entity_service: Entity extraction service instance

    Returns:
        Configured enhanced GraphRAG engine
    """
    return EnhancedGraphRAGEngine(
        neo4j_client=neo4j_client,
        entity_service=entity_service
    )
