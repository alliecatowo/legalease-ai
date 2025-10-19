"""
PropertyGraph Wrapper for LlamaIndex Integration

This module provides a wrapper around LlamaIndex PropertyGraph abstractions
for future extensibility. Currently serves as a bridge between our existing
Neo4j implementation and LlamaIndex's PropertyGraph patterns.

Use Cases:
- Advanced entity extraction using LlamaIndex extractors
- Standardized graph retrieval patterns
- Future migration to full PropertyGraph abstraction
- Integration with LlamaIndex query engines

Note: This is designed for FUTURE use. Current production code should use
EnhancedGraphRAGEngine for performance-critical paths.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

try:
    from llama_index.core import PropertyGraphIndex
    from llama_index.core.indices.property_graph import SimpleLLMPathExtractor
    from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False
    logger = get_logger(__name__)
    logger.warning(
        "LlamaIndex PropertyGraph dependencies not available. "
        "Install llama-index-graph-stores-neo4j for full functionality."
    )

from app.core.config import settings

logger = get_logger(__name__)


@dataclass
class PropertyGraphConfig:
    """Configuration for PropertyGraph integration."""
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str = "neo4j"
    entity_types: List[str] = None

    def __post_init__(self):
        if self.entity_types is None:
            # Legal-specific entity types
            self.entity_types = [
                "PERSON",
                "ORGANIZATION",
                "LAW_FIRM",
                "COURT",
                "JUDGE",
                "ATTORNEY",
                "CASE",
                "STATUTE",
                "REGULATION",
                "DATE",
                "MONEY",
                "CITATION"
            ]


class PropertyGraphWrapper:
    """
    Wrapper around LlamaIndex PropertyGraph for future extensibility.

    This class provides:
    1. Standardized interface to PropertyGraph operations
    2. Integration with existing Neo4j graph
    3. Advanced entity extraction using LlamaIndex extractors
    4. Query engine integration for RAG workflows

    Status: EXPERIMENTAL - Not yet used in production
    """

    def __init__(self, config: PropertyGraphConfig):
        """
        Initialize PropertyGraph wrapper.

        Args:
            config: PropertyGraph configuration

        Raises:
            ImportError: If LlamaIndex dependencies not available
        """
        if not LLAMAINDEX_AVAILABLE:
            raise ImportError(
                "LlamaIndex PropertyGraph dependencies not available. "
                "Install: pip install llama-index-graph-stores-neo4j"
            )

        self.config = config
        self.graph_store = None
        self.index = None

        logger.info("PropertyGraph wrapper initialized (experimental)")

    def initialize_graph_store(self) -> None:
        """
        Initialize Neo4j PropertyGraph store.

        This connects to the existing Neo4j database and provides
        a PropertyGraph abstraction layer.
        """
        if not LLAMAINDEX_AVAILABLE:
            logger.error("Cannot initialize - LlamaIndex not available")
            return

        try:
            self.graph_store = Neo4jPropertyGraphStore(
                username=self.config.neo4j_user,
                password=self.config.neo4j_password,
                url=self.config.neo4j_uri,
                database=self.config.neo4j_database
            )
            logger.info("Neo4j PropertyGraph store initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PropertyGraph store: {e}")
            raise

    def create_index_from_documents(
        self,
        documents: List[Any],
        entity_extractor: Optional[Any] = None
    ) -> None:
        """
        Create PropertyGraph index from documents.

        This uses LlamaIndex's entity extraction to build a knowledge graph.

        Args:
            documents: List of LlamaIndex Document objects
            entity_extractor: Custom entity extractor (defaults to SimpleLLMPathExtractor)

        Note: This is for future use when we want to leverage LlamaIndex's
        automatic entity extraction instead of our custom GLiNER/LexNLP pipeline.
        """
        if not self.graph_store:
            self.initialize_graph_store()

        try:
            # Use simple extractor if none provided
            if entity_extractor is None:
                entity_extractor = SimpleLLMPathExtractor()

            # Create index with entity extraction
            self.index = PropertyGraphIndex.from_documents(
                documents=documents,
                property_graph_store=self.graph_store,
                kg_extractors=[entity_extractor],
                show_progress=True
            )

            logger.info(f"Created PropertyGraph index from {len(documents)} documents")

        except Exception as e:
            logger.error(f"Failed to create PropertyGraph index: {e}")
            raise

    def load_from_existing_graph(self) -> None:
        """
        Load PropertyGraph index from existing Neo4j graph.

        This allows us to use LlamaIndex query engines on our existing
        knowledge graph without rebuilding.
        """
        if not self.graph_store:
            self.initialize_graph_store()

        try:
            self.index = PropertyGraphIndex.from_existing(
                property_graph_store=self.graph_store
            )
            logger.info("Loaded PropertyGraph index from existing graph")

        except Exception as e:
            logger.error(f"Failed to load PropertyGraph from existing graph: {e}")
            raise

    def get_retriever(
        self,
        retriever_type: str = "vector",
        similarity_top_k: int = 5,
        include_text: bool = True
    ) -> Optional[Any]:
        """
        Get a PropertyGraph retriever for RAG workflows.

        Retriever types:
        - "vector": VectorContextRetriever (semantic search on graph nodes)
        - "llm": LLMSynonymRetriever (query expansion with synonyms)
        - "cypher": TextToCypherRetriever (natural language to Cypher)
        - "hybrid": Combination of multiple retrievers

        Args:
            retriever_type: Type of retriever to create
            similarity_top_k: Number of top results to retrieve
            include_text: Include source text in results

        Returns:
            PropertyGraph retriever or None if not available
        """
        if not self.index:
            logger.warning("PropertyGraph index not initialized")
            return None

        try:
            retriever = self.index.as_retriever(
                include_text=include_text,
                similarity_top_k=similarity_top_k
            )

            logger.info(f"Created {retriever_type} retriever")
            return retriever

        except Exception as e:
            logger.error(f"Failed to create retriever: {e}")
            return None

    def get_query_engine(
        self,
        include_text: bool = True,
        similarity_top_k: int = 5
    ) -> Optional[Any]:
        """
        Get a PropertyGraph query engine for RAG.

        The query engine combines graph retrieval with LLM response generation.

        Args:
            include_text: Include source text in context
            similarity_top_k: Number of top results for context

        Returns:
            Query engine or None if not available
        """
        if not self.index:
            logger.warning("PropertyGraph index not initialized")
            return None

        try:
            query_engine = self.index.as_query_engine(
                include_text=include_text,
                similarity_top_k=similarity_top_k
            )

            logger.info("Created PropertyGraph query engine")
            return query_engine

        except Exception as e:
            logger.error(f"Failed to create query engine: {e}")
            return None

    def query_graph(
        self,
        query: str,
        use_query_engine: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Query the PropertyGraph using natural language.

        Args:
            query: Natural language query
            use_query_engine: Use query engine (LLM) vs retriever (no LLM)

        Returns:
            Query results or None
        """
        try:
            if use_query_engine:
                engine = self.get_query_engine()
                if engine:
                    response = engine.query(query)
                    return {
                        "response": str(response),
                        "source_nodes": response.source_nodes
                    }
            else:
                retriever = self.get_retriever()
                if retriever:
                    nodes = retriever.retrieve(query)
                    return {
                        "nodes": nodes,
                        "count": len(nodes)
                    }

            return None

        except Exception as e:
            logger.error(f"PropertyGraph query failed: {e}")
            return None

    def get_graph_schema(self) -> Optional[Dict[str, Any]]:
        """
        Get the PropertyGraph schema.

        Returns:
            Schema information including node types, relationships, etc.
        """
        if not self.graph_store:
            return None

        try:
            # Get schema from graph store
            # This would return node labels, relationship types, properties, etc.
            # Implementation depends on Neo4jPropertyGraphStore API

            logger.info("Retrieved PropertyGraph schema")
            return {
                "status": "Schema retrieval not yet implemented",
                "entity_types": self.config.entity_types
            }

        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            return None


def create_property_graph_wrapper(
    neo4j_uri: Optional[str] = None,
    neo4j_user: Optional[str] = None,
    neo4j_password: Optional[str] = None
) -> PropertyGraphWrapper:
    """
    Factory function to create PropertyGraph wrapper.

    Args:
        neo4j_uri: Neo4j connection URI (defaults to settings)
        neo4j_user: Neo4j username (defaults to settings)
        neo4j_password: Neo4j password (defaults to settings)

    Returns:
        Configured PropertyGraph wrapper

    Raises:
        ImportError: If LlamaIndex dependencies not available
    """
    config = PropertyGraphConfig(
        neo4j_uri=neo4j_uri or settings.NEO4J_URI,
        neo4j_user=neo4j_user or settings.NEO4J_USER,
        neo4j_password=neo4j_password or settings.NEO4J_PASSWORD
    )

    return PropertyGraphWrapper(config=config)


# Example usage (for future reference)
"""
# Initialize wrapper
pg_wrapper = create_property_graph_wrapper()

# Option 1: Load from existing Neo4j graph
pg_wrapper.load_from_existing_graph()

# Option 2: Create from documents
from llama_index.core import Document
from app.core.logging_config import get_logger
documents = [Document(text="Sample legal document...")]
pg_wrapper.create_index_from_documents(documents)

# Query using retriever (no LLM)
retriever = pg_wrapper.get_retriever(retriever_type="vector")
results = retriever.retrieve("Find cases about contract disputes")

# Query using query engine (with LLM)
results = pg_wrapper.query_graph("Find cases about contract disputes")
"""
