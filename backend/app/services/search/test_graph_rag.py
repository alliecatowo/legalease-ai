"""
Unit tests for GraphRAG engine.

These tests verify the core functionality without requiring full database setup.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import List, Dict, Any

from app.services.search.graph_rag import GraphRAGEngine


class TestGraphRAGEngine:
    """Test suite for GraphRAG engine"""

    @pytest.fixture
    def mock_neo4j_client(self):
        """Create mock Neo4j client"""
        mock = Mock()

        # Mock find_entity_connections
        mock.find_entity_connections.return_value = {
            "entity": "John Doe",
            "co_occurring_entities": [
                {"entity": "Jane Smith", "type": "PERSON", "frequency": 3},
                {"entity": "Acme Corp", "type": "ORGANIZATION", "frequency": 2}
            ],
            "documents": [
                {"doc_id": "doc-1", "title": "Contract Agreement"},
                {"doc_id": "doc-2", "title": "Motion to Dismiss"}
            ]
        }

        # Mock find_related_documents
        mock.find_related_documents.return_value = [
            {"doc_id": "doc-1", "title": "Contract Agreement", "entities": ["John Doe", "Acme Corp"]},
            {"doc_id": "doc-2", "title": "Motion to Dismiss", "entities": ["John Doe"]},
            {"doc_id": "doc-3", "title": "Settlement Agreement", "entities": ["Jane Smith"]}
        ]

        # Mock get_case_graph
        mock.get_case_graph.return_value = {
            "documents": [
                {"id": "doc-1", "title": "Contract Agreement"},
                {"id": "doc-2", "title": "Motion to Dismiss"},
                {"id": "doc-3", "title": "Settlement Agreement"}
            ],
            "entities": [],
            "citations": [
                {"from_doc": "doc-1", "to_doc": "doc-2", "citation_text": "See Motion"},
                {"from_doc": "doc-1", "to_doc": "doc-3", "citation_text": "As settled in"},
                {"from_doc": "doc-3", "to_doc": "doc-2", "citation_text": "Reference to"}
            ]
        }

        # Mock find_citation_chain
        mock.find_citation_chain.return_value = [
            {"depth": 1},
            {"depth": 2}
        ]

        return mock

    @pytest.fixture
    def mock_entity_service(self):
        """Create mock entity service"""
        mock = Mock()

        # Mock extract_entities
        async def mock_extract(*args, **kwargs):
            return [
                {"text": "John Doe", "type": "PERSON", "confidence": 0.95},
                {"text": "Acme Corp", "type": "ORGANIZATION", "confidence": 0.92},
                {"text": "contract", "type": "LEGAL_TERM", "confidence": 0.88}
            ]

        mock.extract_entities = AsyncMock(side_effect=mock_extract)

        return mock

    @pytest.fixture
    def graph_rag_engine(self, mock_neo4j_client, mock_entity_service):
        """Create GraphRAG engine with mocked dependencies"""
        return GraphRAGEngine(
            neo4j_client=mock_neo4j_client,
            entity_service=mock_entity_service
        )

    @pytest.mark.asyncio
    async def test_entity_enhanced_search(
        self,
        graph_rag_engine,
        mock_entity_service,
        mock_neo4j_client
    ):
        """Test entity-enhanced search returns document IDs"""
        # Mock database session
        db = Mock()

        # Perform search
        doc_ids = await graph_rag_engine.entity_enhanced_search(
            query="John Doe filed a motion against Acme Corp",
            case_id="case-123",
            db=db
        )

        # Verify entity extraction was called
        mock_entity_service.extract_entities.assert_called_once()

        # Verify graph queries were made
        assert mock_neo4j_client.find_entity_connections.called
        assert mock_neo4j_client.find_related_documents.called

        # Verify results
        assert isinstance(doc_ids, list)
        assert len(doc_ids) > 0
        assert "doc-1" in doc_ids
        assert "doc-2" in doc_ids

    def test_citation_context_basic(self, graph_rag_engine):
        """Test basic citation context enhancement"""
        # Mock search results
        search_results = [
            {
                "id": "chunk-1",
                "score": 0.85,
                "document_id": "doc-1",
                "text": "Sample text",
                "metadata": {"document_id": "doc-1"}
            },
            {
                "id": "chunk-2",
                "score": 0.75,
                "document_id": "doc-2",
                "text": "Another text",
                "metadata": {"document_id": "doc-2"}
            }
        ]

        # Add citation context
        enhanced = graph_rag_engine.add_citation_context(
            search_results=search_results,
            case_id="case-123"
        )

        # Verify enhancement
        assert len(enhanced) == 2

        # Check citation metadata was added
        for result in enhanced:
            assert "citation" in result["metadata"]
            citation = result["metadata"]["citation"]
            assert "cited_by_count" in citation
            assert "cites_count" in citation
            assert "citation_score" in citation
            assert "is_highly_cited" in citation

    def test_citation_context_score_boost(self, graph_rag_engine):
        """Test that citation context boosts scores"""
        search_results = [
            {
                "id": "chunk-1",
                "score": 0.70,
                "document_id": "doc-2",  # Highly cited doc
                "metadata": {"document_id": "doc-2"}
            },
            {
                "id": "chunk-2",
                "score": 0.80,
                "document_id": "doc-1",  # Less cited doc
                "metadata": {"document_id": "doc-1"}
            }
        ]

        original_scores = {r["id"]: r["score"] for r in search_results}

        # Add citation context
        enhanced = graph_rag_engine.add_citation_context(
            search_results=search_results,
            case_id="case-123",
            citation_boost_weight=0.15
        )

        # Verify boost was applied
        for result in enhanced:
            boost = result["metadata"].get("citation_boost", 0)
            # Highly cited docs should get some boost
            if result["document_id"] == "doc-2":
                assert boost > 0, "Highly cited document should receive boost"

    def test_calculate_citation_centrality(self, graph_rag_engine):
        """Test PageRank-style citation centrality calculation"""
        # Simple citation graph: doc-1 -> doc-2, doc-3 -> doc-2
        # doc-2 should have highest centrality
        citation_graph = {
            "doc-1": {"cited_by": [], "cites": ["doc-2"]},
            "doc-2": {"cited_by": ["doc-1", "doc-3"], "cites": []},
            "doc-3": {"cited_by": [], "cites": ["doc-2"]}
        }

        scores = graph_rag_engine._calculate_citation_centrality(citation_graph)

        # Verify scores were calculated
        assert len(scores) == 3
        assert all(score > 0 for score in scores.values())

        # doc-2 should have highest score (cited by 2 docs)
        assert scores["doc-2"] > scores["doc-1"]
        assert scores["doc-2"] > scores["doc-3"]

    def test_extract_doc_id(self, graph_rag_engine):
        """Test document ID extraction from various result formats"""
        # Test different result formats
        test_cases = [
            # Direct document_id
            {
                "result": {"document_id": "doc-123"},
                "expected": "doc-123"
            },
            # In metadata
            {
                "result": {"metadata": {"document_id": "doc-456"}},
                "expected": "doc-456"
            },
            # In payload (Qdrant format)
            {
                "result": {"payload": {"document_id": "doc-789"}},
                "expected": "doc-789"
            },
            # Not found
            {
                "result": {"id": "chunk-1"},
                "expected": None
            }
        ]

        for test_case in test_cases:
            result = graph_rag_engine._extract_doc_id(test_case["result"])
            assert result == test_case["expected"]

    def test_empty_citation_graph(self, graph_rag_engine):
        """Test handling of empty citation graph"""
        scores = graph_rag_engine._calculate_citation_centrality({})
        assert scores == {}

    def test_citation_context_with_no_citations(
        self,
        mock_neo4j_client,
        mock_entity_service
    ):
        """Test citation enhancement when no citations exist"""
        # Override mock to return empty citations
        mock_neo4j_client.get_case_graph.return_value = {
            "documents": [],
            "entities": [],
            "citations": []
        }

        engine = GraphRAGEngine(mock_neo4j_client, mock_entity_service)

        search_results = [
            {
                "id": "chunk-1",
                "score": 0.85,
                "document_id": "doc-1",
                "metadata": {"document_id": "doc-1"}
            }
        ]

        # Should not crash, just not add boosts
        enhanced = engine.add_citation_context(
            search_results=search_results,
            case_id="case-123"
        )

        assert len(enhanced) == 1
        assert enhanced[0]["metadata"]["citation"]["cited_by_count"] == 0


def test_create_graph_rag_engine():
    """Test factory function"""
    from app.services.search.graph_rag import create_graph_rag_engine

    mock_neo4j = Mock()
    mock_entity_service = Mock()

    engine = create_graph_rag_engine(
        neo4j_client=mock_neo4j,
        entity_service=mock_entity_service
    )

    assert isinstance(engine, GraphRAGEngine)
    assert engine.neo4j == mock_neo4j
    assert engine.entity_service == mock_entity_service


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
