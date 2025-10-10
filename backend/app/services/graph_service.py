"""
Knowledge Graph Service

Provides knowledge graph functionality using Neo4j for entity relationships,
citations, and document connections in legal cases.
"""
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.neo4j import neo4j_client
from ..models.document import Document
from ..models.entity import Entity, EntityMention

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """Service for managing the legal knowledge graph"""

    def __init__(self):
        self.neo4j = neo4j_client

    async def build_document_graph(
        self,
        document_id: str,
        db: AsyncSession
    ) -> bool:
        """
        Build knowledge graph for a document

        Args:
            document_id: Document ID
            db: Database session

        Returns:
            Success status
        """
        try:
            # Get document info
            doc_query = select(Document).where(Document.id == document_id)
            doc_result = await db.execute(doc_query)
            document = doc_result.scalar_one_or_none()

            if not document:
                logger.error(f"Document {document_id} not found")
                return False

            # Get entities for document
            entity_query = (
                select(Entity, EntityMention)
                .join(EntityMention, Entity.id == EntityMention.entity_id)
                .where(EntityMention.document_id == document_id)
            )
            entity_result = await db.execute(entity_query)
            entities = entity_result.all()

            # Create document node
            doc_data = {
                "id": document.id,
                "title": document.filename or "Untitled",
                "file_path": document.file_path,
                "mime_type": document.mime_type,
                "case_id": document.case_id,
                "created_at": document.created_at.isoformat() if document.created_at else None,
                "processed_at": document.processed_at.isoformat() if document.processed_at else None
            }

            self.neo4j.create_document_node(doc_data)

            # Create entity nodes and relationships
            for entity, mention in entities:
                entity_data = {
                    "text": entity.text,
                    "type": entity.type,
                    "source": entity.source,
                    "confidence": mention.confidence
                }

                self.neo4j.create_entity_node(entity_data)
                self.neo4j.link_document_entity(document.id, entity.text, mention.context)

            logger.info(f"Built knowledge graph for document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to build document graph for {document_id}: {e}")
            return False

    async def build_case_graph(self, case_id: str, db: AsyncSession) -> Dict[str, Any]:
        """
        Build complete knowledge graph for a case

        Args:
            case_id: Case ID
            db: Database session

        Returns:
            Graph statistics
        """
        try:
            # Get all documents in case
            doc_query = select(Document).where(Document.case_id == case_id)
            doc_result = await db.execute(doc_query)
            documents = doc_result.scalars().all()

            total_docs = len(documents)
            processed_docs = 0
            total_entities = 0
            total_relationships = 0

            for doc in documents:
                success = await self.build_document_graph(doc.id, db)
                if success:
                    processed_docs += 1

                    # Count entities for this document
                    entity_count = len(await self._get_document_entities(doc.id, db))
                    total_entities += entity_count

            # Build citation relationships
            citation_count = await self._build_citation_graph(case_id, db)
            total_relationships += citation_count

            # Build entity co-occurrence relationships
            co_occurrence_count = await self._build_entity_relationships(case_id)
            total_relationships += co_occurrence_count

            stats = {
                "documents_processed": processed_docs,
                "total_documents": total_docs,
                "entities_extracted": total_entities,
                "relationships_created": total_relationships,
                "case_id": case_id
            }

            logger.info(f"Built knowledge graph for case {case_id}: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to build case graph for {case_id}: {e}")
            return {"error": str(e)}

    async def _build_citation_graph(self, case_id: str, db: AsyncSession) -> int:
        """Build citation relationships within a case"""
        try:
            # Get all documents in case
            doc_query = select(Document.id, Document.content).where(Document.case_id == case_id)
            doc_result = await db.execute(doc_query)
            documents = doc_result.all()

            citation_count = 0

            # Simple citation detection (can be enhanced with better parsing)
            for doc_id, content in documents:
                if not content:
                    continue

                # Look for citation patterns
                citations = self._extract_citations(content)

                for citation in citations:
                    # Try to find cited document in same case
                    cited_doc = await self._resolve_citation(citation, case_id, db)
                    if cited_doc and cited_doc != doc_id:
                        self.neo4j.create_citation_relationship(
                            doc_id, cited_doc, {
                                "text": citation.get("text", ""),
                                "context": citation.get("context", ""),
                                "page": citation.get("page"),
                                "paragraph": citation.get("paragraph")
                            }
                        )
                        citation_count += 1

            return citation_count

        except Exception as e:
            logger.error(f"Failed to build citation graph for case {case_id}: {e}")
            return 0

    def _extract_citations(self, text: str) -> List[Dict[str, Any]]:
        """Extract citations from text (simplified)"""
        citations = []

        # Look for common citation patterns
        patterns = [
            r'(\d{4})\s+(\w+)\s+(\d+)',  # Year Volume Page
            r'(\d+)\s+(\w+)\s+(\d+)',     # Volume Reporter Page
            r'(\d{2}[-]\d{4}[-]\w+)',     # Case numbers
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                citations.append({
                    "text": match.group(),
                    "context": text[max(0, match.start()-100):match.end()+100],
                    "start": match.start(),
                    "end": match.end()
                })

        return citations

    async def _resolve_citation(self, citation: Dict[str, Any], case_id: str, db: AsyncSession) -> Optional[str]:
        """Try to resolve citation to a document ID"""
        # This is a simplified implementation
        # In a real system, you'd have a citation resolver service
        citation_text = citation.get("text", "")

        # Look for documents with similar names or content
        doc_query = select(Document.id, Document.filename).where(Document.case_id == case_id)
        doc_result = await db.execute(doc_query)
        documents = doc_result.all()

        for doc_id, filename in documents:
            if filename and citation_text.lower() in filename.lower():
                return doc_id

        return None

    async def _build_entity_relationships(self, case_id: str) -> int:
        """Build entity co-occurrence relationships"""
        try:
            # Get all entity co-occurrences in documents
            query = """
            MATCH (d:Document {case_id: $case_id})-[:MENTIONS]->(e1:Entity)
            MATCH (d)-[:MENTIONS]->(e2:Entity)
            WHERE e1 <> e2
            RETURN e1.text as entity1, e2.text as entity2, count(*) as frequency
            """

            # Note: This would be implemented with Neo4j queries
            # For now, return a placeholder
            return 0

        except Exception as e:
            logger.error(f"Failed to build entity relationships for case {case_id}: {e}")
            return 0

    async def _get_document_entities(self, document_id: str, db: AsyncSession) -> List[Dict]:
        """Get entities for a document"""
        entity_query = (
            select(Entity)
            .join(EntityMention, Entity.id == EntityMention.entity_id)
            .where(EntityMention.document_id == document_id)
        )
        entity_result = await db.execute(entity_query)
        return [entity.__dict__ for entity in entity_result.scalars()]

    async def query_graph(
        self,
        case_id: str,
        query_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Query the knowledge graph

        Args:
            case_id: Case ID
            query_type: Type of query (entity_connections, citation_chain, etc.)
            parameters: Query parameters

        Returns:
            Query results
        """
        try:
            if query_type == "entity_connections":
                return await self._query_entity_connections(case_id, parameters)
            elif query_type == "citation_chain":
                return await self._query_citation_chain(case_id, parameters)
            elif query_type == "document_similarity":
                return await self._query_document_similarity(case_id, parameters)
            else:
                return {"error": f"Unknown query type: {query_type}"}

        except Exception as e:
            logger.error(f"Failed to query graph for case {case_id}: {e}")
            return {"error": str(e)}

    async def _query_entity_connections(
        self,
        case_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find entity connections"""
        entity_text = parameters.get("entity")

        if not entity_text:
            return {"error": "Entity text required"}

        return self.neo4j.find_entity_connections(entity_text, case_id)

    async def _query_citation_chain(
        self,
        case_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find citation chains"""
        doc_id = parameters.get("document_id")
        depth = parameters.get("depth", 3)

        if not doc_id:
            return {"error": "Document ID required"}

        chain = self.neo4j.find_citation_chain(doc_id, depth)
        return {"citation_chain": chain}

    async def _query_document_similarity(
        self,
        case_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find similar documents based on entity overlap"""
        doc_id = parameters.get("document_id")

        if not doc_id:
            return {"error": "Document ID required"}

        # Get entities for the document
        doc_entities = self._get_document_entities_neo4j(doc_id)

        # Find documents with similar entities
        similar_docs = self.neo4j.find_related_documents(doc_entities, case_id)

        return {"similar_documents": similar_docs}

    def _get_document_entities_neo4j(self, doc_id: str) -> List[str]:
        """Get entity texts for a document from Neo4j"""
        try:
            query = """
            MATCH (d:Document {id: $doc_id})-[:MENTIONS]->(e:Entity)
            RETURN e.text as entity_text
            """

            # This would execute the query and return results
            # Placeholder for now
            return []

        except Exception as e:
            logger.error(f"Failed to get entities for document {doc_id}: {e}")
            return []

    async def get_case_graph_stats(self, case_id: str) -> Dict[str, Any]:
        """Get statistics about the case knowledge graph"""
        try:
            stats = self.neo4j.get_case_graph(case_id)

            # Calculate some additional metrics
            if "documents" in stats:
                total_docs = len(stats["documents"])
                total_entities = len(set(entity["text"] for entity in stats["entities"]))
                total_citations = len(stats["citations"])

                stats.update({
                    "total_documents": total_docs,
                    "unique_entities": total_entities,
                    "citation_relationships": total_citations,
                    "connectivity_ratio": total_citations / total_docs if total_docs > 0 else 0
                })

            return stats

        except Exception as e:
            logger.error(f"Failed to get graph stats for case {case_id}: {e}")
            return {"error": str(e)}

    async def find_related_cases(
        self,
        case_id: str,
        similarity_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Find cases similar to the given case based on entity overlap

        Args:
            case_id: Case ID to find similar cases for
            similarity_threshold: Minimum similarity score

        Returns:
            List of similar cases with similarity scores
        """
        try:
            # Get entities for this case
            case_entities = set()
            query = """
            MATCH (d:Document {case_id: $case_id})-[:MENTIONS]->(e:Entity)
            RETURN distinct e.text as entity
            """

            # Get all entities in this case
            # This would be implemented with actual Neo4j queries

            # Find other cases with overlapping entities
            similar_cases = []
            # Implementation would calculate Jaccard similarity between cases

            return similar_cases

        except Exception as e:
            logger.error(f"Failed to find related cases for {case_id}: {e}")
            return []

    async def export_graph(
        self,
        case_id: str,
        format: str = "json"
    ) -> Optional[str]:
        """
        Export knowledge graph data

        Args:
            case_id: Case ID
            format: Export format (json, csv, graphml)

        Returns:
            Export data or None if failed
        """
        try:
            graph_data = self.neo4j.get_case_graph(case_id)

            if format == "json":
                import json
                return json.dumps(graph_data, indent=2, default=str)
            elif format == "csv":
                # Convert to CSV format
                return self._graph_to_csv(graph_data)
            else:
                return json.dumps(graph_data, default=str)

        except Exception as e:
            logger.error(f"Failed to export graph for case {case_id}: {e}")
            return None

    def _graph_to_csv(self, graph_data: Dict[str, Any]) -> str:
        """Convert graph data to CSV format"""
        # Simple CSV export of entities and relationships
        lines = ["Entity1,Entity2,Relationship_Type,Document"]

        for citation in graph_data.get("citations", []):
            lines.append(f"{citation['from_doc']},{citation['to_doc']},CITES,{citation.get('citation_text', '')}")

        return "\n".join(lines)


# Global service instance
graph_service = KnowledgeGraphService()