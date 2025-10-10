"""
Neo4j Integration for Knowledge Graph

This module provides a client for interacting with Neo4j graph database
for storing entity relationships, citations, and document connections.
"""
import logging
from typing import Dict, List, Optional, Any
from neo4j import GraphDatabase, AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable

from .config import settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Client for Neo4j graph database"""

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD

        # Synchronous driver for most operations
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password)
        )

        # Async driver for async operations
        self.async_driver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password)
        )

    def close(self):
        """Close database connections"""
        self.driver.close()
        self.async_driver.close()

    async def aclose(self):
        """Async close"""
        await self.async_driver.close()
        self.driver.close()

    def health_check(self) -> bool:
        """Check if Neo4j is accessible"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1")
                return result.single()[0] == 1
        except ServiceUnavailable:
            return False
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False

    def create_constraints(self):
        """Create database constraints for performance"""
        constraints = [
            "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT entity_text IF NOT EXISTS FOR (e:Entity) REQUIRE e.text IS UNIQUE",
            "CREATE CONSTRAINT case_id IF NOT EXISTS FOR (c:Case) REQUIRE c.id IS UNIQUE",
        ]

        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    logger.warning(f"Failed to create constraint: {e}")

    def clear_database(self):
        """Clear all data (for testing)"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    # Document operations
    def create_document_node(self, doc_data: Dict[str, Any]) -> str:
        """Create a document node"""
        query = """
        MERGE (d:Document {id: $id})
        SET d.title = $title,
            d.filename = $filename,
            d.file_path = $file_path,
            d.mime_type = $mime_type,
            d.case_id = $case_id,
            d.created_at = $created_at,
            d.processed_at = $processed_at
        RETURN d.id
        """

        with self.driver.session() as session:
            result = session.run(query, **doc_data)
            return result.single()["d.id"]

    def create_case_node(self, case_data: Dict[str, Any]) -> str:
        """Create a case node"""
        query = """
        MERGE (c:Case {id: $id})
        SET c.name = $name,
            c.case_number = $case_number,
            c.client = $client,
            c.matter_type = $matter_type,
            c.created_at = $created_at,
            c.status = $status
        RETURN c.id
        """

        with self.driver.session() as session:
            result = session.run(query, **case_data)
            return result.single()["c.id"]

    # Entity operations
    def create_entity_node(self, entity_data: Dict[str, Any]) -> str:
        """Create an entity node"""
        query = """
        MERGE (e:Entity {text: $text})
        SET e.type = $type,
            e.label = $label,
            e.confidence = $confidence
        RETURN e.text
        """

        with self.driver.session() as session:
            result = session.run(query, **entity_data)
            return result.single()["e.text"]

    def link_document_entity(self, doc_id: str, entity_text: str, context: str = None):
        """Create relationship between document and entity"""
        query = """
        MATCH (d:Document {id: $doc_id})
        MATCH (e:Entity {text: $entity_text})
        MERGE (d)-[r:MENTIONS {context: $context}]->(e)
        """

        with self.driver.session() as session:
            session.run(query, doc_id=doc_id, entity_text=entity_text, context=context)

    # Citation operations
    def create_citation_relationship(self, citing_doc_id: str, cited_doc_id: str, citation_data: Dict[str, Any]):
        """Create citation relationship between documents"""
        query = """
        MATCH (d1:Document {id: $citing_doc_id})
        MATCH (d2:Document {id: $cited_doc_id})
        MERGE (d1)-[r:CITES {
            text: $text,
            context: $context,
            page: $page,
            paragraph: $paragraph
        }]->(d2)
        """

        with self.driver.session() as session:
            session.run(query, citing_doc_id=citing_doc_id, cited_doc_id=cited_doc_id, **citation_data)

    def find_citation_chain(self, doc_id: str, depth: int = 3) -> List[Dict]:
        """Find citation chain for a document"""
        query = """
        MATCH path = (d:Document {id: $doc_id})-[:CITES*1..$depth]->(cited:Document)
        RETURN path, length(path) as depth
        ORDER BY depth DESC
        LIMIT 50
        """

        with self.driver.session() as session:
            results = session.run(query, doc_id=doc_id, depth=depth)
            return [dict(record) for record in results]

    # Query operations
    def find_related_documents(self, entity_texts: List[str], case_id: Optional[str] = None) -> List[Dict]:
        """Find documents related to entities"""
        query = """
        MATCH (d:Document)-[:MENTIONS]->(e:Entity)
        WHERE e.text IN $entity_texts
        """

        if case_id:
            query += " AND d.case_id = $case_id"

        query += """
        RETURN d.id as doc_id, d.title as title, collect(e.text) as entities
        ORDER BY size(entities) DESC
        LIMIT 20
        """

        with self.driver.session() as session:
            results = session.run(query, entity_texts=entity_texts, case_id=case_id)
            return [dict(record) for record in results]

    def find_entity_connections(self, entity_text: str, case_id: Optional[str] = None) -> Dict[str, Any]:
        """Find all connections for an entity"""
        # Find co-occurring entities
        co_occurrence_query = """
        MATCH (d:Document)-[:MENTIONS]->(e1:Entity {text: $entity_text})
        MATCH (d)-[:MENTIONS]->(e2:Entity)
        WHERE e1 <> e2
        """

        if case_id:
            co_occurrence_query += " AND d.case_id = $case_id"

        co_occurrence_query += """
        RETURN e2.text as entity, e2.type as type, count(*) as frequency
        ORDER BY frequency DESC
        LIMIT 10
        """

        # Find documents mentioning this entity
        document_query = """
        MATCH (d:Document)-[:MENTIONS]->(e:Entity {text: $entity_text})
        """

        if case_id:
            document_query += " WHERE d.case_id = $case_id"

        document_query += """
        RETURN d.id as doc_id, d.title as title
        ORDER BY d.created_at DESC
        LIMIT 20
        """

        with self.driver.session() as session:
            co_occurrences = [dict(r) for r in session.run(co_occurrence_query, entity_text=entity_text, case_id=case_id)]
            documents = [dict(r) for r in session.run(document_query, entity_text=entity_text, case_id=case_id)]

            return {
                "entity": entity_text,
                "co_occurring_entities": co_occurrences,
                "documents": documents
            }

    def get_case_graph(self, case_id: str) -> Dict[str, Any]:
        """Get complete graph for a case"""
        # Get all documents in case
        docs_query = """
        MATCH (d:Document {case_id: $case_id})
        RETURN d.id as id, d.title as title, d.filename as filename
        """

        # Get all entities in case
        entities_query = """
        MATCH (d:Document {case_id: $case_id})-[:MENTIONS]->(e:Entity)
        RETURN distinct e.text as text, e.type as type, count(*) as frequency
        ORDER BY frequency DESC
        """

        # Get citation relationships
        citations_query = """
        MATCH (d1:Document {case_id: $case_id})-[r:CITES]->(d2:Document {case_id: $case_id})
        RETURN d1.id as from_doc, d2.id as to_doc, r.text as citation_text
        """

        with self.driver.session() as session:
            documents = [dict(r) for r in session.run(docs_query, case_id=case_id)]
            entities = [dict(r) for r in session.run(entities_query, case_id=case_id)]
            citations = [dict(r) for r in session.run(citations_query, case_id=case_id)]

            return {
                "documents": documents,
                "entities": entities,
                "citations": citations
            }


# Global client instance
neo4j_client = Neo4jClient()


async def init_neo4j():
    """Initialize Neo4j database with constraints"""
    try:
        neo4j_client.create_constraints()
        logger.info("Neo4j constraints created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Neo4j: {e}")
        raise