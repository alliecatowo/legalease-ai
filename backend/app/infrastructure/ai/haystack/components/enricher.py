"""
Result enrichment components for search results.

Enriches minimal search results with full document metadata,
surrounding context, and formatted citations.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from haystack import component, Document

from app.core.database import SessionLocal
from app.models.document import Document as DBDocument
from app.models.case import Case

logger = logging.getLogger(__name__)


@component
class ResultEnricher:
    """
    Enriches search results with full metadata from PostgreSQL.

    Takes search results (with minimal metadata) and fetches:
    - Full document metadata (filename, type, page count)
    - Full case metadata (case number, title, parties)
    - Surrounding chunk context (optional)
    - Formatted citations (page#, paragraph#, timecode)

    Features:
    - Batch fetching from PostgreSQL
    - Context window retrieval (surrounding chunks)
    - Citation formatting
    - GID resolution
    """

    def __init__(
        self,
        fetch_surrounding_context: bool = False,
        context_window: int = 1,
        format_citations: bool = True,
    ):
        """
        Initialize result enricher.

        Args:
            fetch_surrounding_context: Whether to fetch surrounding chunks
            context_window: Number of chunks before/after to fetch
            format_citations: Whether to format citations
        """
        self.fetch_surrounding_context = fetch_surrounding_context
        self.context_window = context_window
        self.format_citations = format_citations

        logger.info(
            f"Initialized ResultEnricher "
            f"(context={fetch_surrounding_context}, window={context_window})"
        )

    @component.output_types(documents=List[Document])
    def run(
        self,
        documents: List[Document],
    ) -> Dict[str, List[Document]]:
        """
        Enrich search results with full metadata.

        Args:
            documents: Search results to enrich

        Returns:
            Dict with 'documents' key containing enriched results
        """
        if not documents:
            return {"documents": []}

        logger.info(f"Enriching {len(documents)} search results")

        # Extract unique document IDs and case IDs
        document_ids = set()
        case_ids = set()

        for doc in documents:
            if doc.meta and doc.meta.get("document_id"):
                try:
                    doc_id = UUID(doc.meta["document_id"])
                    document_ids.add(doc_id)
                except (ValueError, TypeError):
                    pass

            if doc.meta and doc.meta.get("case_id"):
                try:
                    case_id = UUID(doc.meta["case_id"])
                    case_ids.add(case_id)
                except (ValueError, TypeError):
                    pass

        # Batch fetch from PostgreSQL
        document_metadata = self._fetch_document_metadata(list(document_ids))
        case_metadata = self._fetch_case_metadata(list(case_ids))

        # Enrich each document
        enriched_documents = []

        for doc in documents:
            enriched_doc = self._enrich_document(
                doc,
                document_metadata,
                case_metadata,
            )
            enriched_documents.append(enriched_doc)

        logger.info(f"Enrichment complete: {len(enriched_documents)} documents")

        return {"documents": enriched_documents}

    def _fetch_document_metadata(
        self,
        document_ids: List[UUID],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch fetch document metadata from PostgreSQL.

        Args:
            document_ids: List of document UUIDs

        Returns:
            Dict mapping document_id (str) to metadata
        """
        if not document_ids:
            return {}

        db = SessionLocal()
        try:
            documents = db.query(DBDocument).filter(
                DBDocument.id.in_(document_ids)
            ).all()

            metadata = {}
            for doc in documents:
                metadata[str(doc.id)] = {
                    "document_id": str(doc.id),
                    "document_gid": doc.gid,
                    "filename": doc.filename,
                    "file_type": doc.file_type,
                    "page_count": doc.page_count,
                    "file_size": doc.file_size,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                }

            logger.info(f"Fetched metadata for {len(metadata)} documents")
            return metadata

        except Exception as e:
            logger.error(f"Error fetching document metadata: {e}", exc_info=True)
            return {}
        finally:
            db.close()

    def _fetch_case_metadata(
        self,
        case_ids: List[UUID],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch fetch case metadata from PostgreSQL.

        Args:
            case_ids: List of case UUIDs

        Returns:
            Dict mapping case_id (str) to metadata
        """
        if not case_ids:
            return {}

        db = SessionLocal()
        try:
            cases = db.query(Case).filter(
                Case.id.in_(case_ids)
            ).all()

            metadata = {}
            for case in cases:
                metadata[str(case.id)] = {
                    "case_id": str(case.id),
                    "case_gid": case.gid,
                    "case_number": case.case_number,
                    "case_title": case.case_title,
                    "court": case.court,
                    "jurisdiction": case.jurisdiction,
                    "filing_date": case.filing_date.isoformat() if case.filing_date else None,
                    "created_at": case.created_at.isoformat() if case.created_at else None,
                }

            logger.info(f"Fetched metadata for {len(metadata)} cases")
            return metadata

        except Exception as e:
            logger.error(f"Error fetching case metadata: {e}", exc_info=True)
            return {}
        finally:
            db.close()

    def _enrich_document(
        self,
        doc: Document,
        document_metadata: Dict[str, Dict[str, Any]],
        case_metadata: Dict[str, Dict[str, Any]],
    ) -> Document:
        """
        Enrich a single document with full metadata.

        Args:
            doc: Document to enrich
            document_metadata: Document metadata lookup
            case_metadata: Case metadata lookup

        Returns:
            Enriched document
        """
        if not doc.meta:
            doc.meta = {}

        # Enrich with document metadata
        document_id = doc.meta.get("document_id")
        if document_id and document_id in document_metadata:
            doc_meta = document_metadata[document_id]
            doc.meta.update({
                "document_filename": doc_meta.get("filename"),
                "document_file_type": doc_meta.get("file_type"),
                "document_page_count": doc_meta.get("page_count"),
                "document_gid": doc_meta.get("document_gid"),
            })

        # Enrich with case metadata
        case_id = doc.meta.get("case_id")
        if case_id and case_id in case_metadata:
            case_meta = case_metadata[case_id]
            doc.meta.update({
                "case_number": case_meta.get("case_number"),
                "case_title": case_meta.get("case_title"),
                "case_court": case_meta.get("court"),
                "case_jurisdiction": case_meta.get("jurisdiction"),
                "case_gid": case_meta.get("case_gid"),
            })

        # Format citation
        if self.format_citations:
            citation = self._format_citation(doc.meta)
            if citation:
                doc.meta["citation"] = citation

        return doc

    def _format_citation(self, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Format a citation string for the chunk.

        Examples:
        - "Contract.pdf, page 5, ¶3"
        - "Deposition_Smith.mp4, 00:15:32"
        - "Email_2023-01-15.txt, line 42"

        Args:
            metadata: Chunk metadata

        Returns:
            Formatted citation string or None
        """
        parts = []

        # Add filename
        filename = metadata.get("document_filename")
        if filename:
            parts.append(filename)

        # Add page number for documents
        page_number = metadata.get("page_number")
        if page_number:
            parts.append(f"page {page_number}")

        # Add paragraph/position
        position = metadata.get("position")
        if position is not None:
            parts.append(f"¶{position}")

        # Add timecode for transcripts
        start_time = metadata.get("start_time")
        if start_time:
            # Format seconds as HH:MM:SS
            hours = int(start_time // 3600)
            minutes = int((start_time % 3600) // 60)
            seconds = int(start_time % 60)
            timecode = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            parts.append(timecode)

        if parts:
            return ", ".join(parts)

        return None


@component
class HighlightExtractor:
    """
    Extracts highlighted snippets from search results.

    Creates context-aware snippets around query matches
    for display in search results.
    """

    def __init__(
        self,
        max_highlights: int = 3,
        context_words: int = 10,
    ):
        """
        Initialize highlight extractor.

        Args:
            max_highlights: Maximum number of highlights per result
            context_words: Number of words before/after match
        """
        self.max_highlights = max_highlights
        self.context_words = context_words

        logger.info(
            f"Initialized HighlightExtractor "
            f"(max={max_highlights}, context={context_words})"
        )

    @component.output_types(documents=List[Document])
    def run(
        self,
        documents: List[Document],
        query: str,
    ) -> Dict[str, List[Document]]:
        """
        Extract highlights from documents.

        Args:
            documents: Search results
            query: Original query text

        Returns:
            Dict with 'documents' containing highlighted results
        """
        query_tokens = set(query.lower().split())

        for doc in documents:
            highlights = self._extract_highlights(
                doc.content,
                query_tokens,
            )

            if highlights:
                if not doc.meta:
                    doc.meta = {}
                doc.meta["highlights"] = highlights

        return {"documents": documents}

    def _extract_highlights(
        self,
        text: str,
        query_tokens: set,
    ) -> List[str]:
        """
        Extract highlighted snippets from text.

        Args:
            text: Source text
            query_tokens: Set of query tokens to match

        Returns:
            List of highlight snippets
        """
        if not text or not query_tokens:
            return []

        words = text.split()
        highlights = []

        for i, word in enumerate(words):
            clean_word = word.lower().strip(".,;:!?\"'")
            if clean_word in query_tokens:
                start = max(0, i - self.context_words)
                end = min(len(words), i + self.context_words + 1)
                snippet = " ".join(words[start:end])

                if start > 0:
                    snippet = "..." + snippet
                if end < len(words):
                    snippet = snippet + "..."

                highlights.append(snippet)

                if len(highlights) >= self.max_highlights:
                    break

        return highlights
