"""
Search Services Package

This package provides advanced search capabilities including:
- Hybrid search with BM25 and dense vector fusion
- GraphRAG-enhanced search with entity extraction and graph traversal
- Citation-based document ranking
- Cross-encoder reranking
"""

from app.services.search.engine import HybridSearchEngine, get_search_engine
from app.services.search.graph_rag import GraphRAGEngine, create_graph_rag_engine

__all__ = [
    "HybridSearchEngine",
    "get_search_engine",
    "GraphRAGEngine",
    "create_graph_rag_engine",
]
