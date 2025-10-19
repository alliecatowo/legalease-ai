"""
GID/UUID Resolution and Caching

Handles resolution between document/case UUIDs and GIDs with in-memory caching.
"""

from typing import Dict, Optional, Any
import logging
from uuid import UUID

from app.core.database import SessionLocal
from app.models.document import Document
from app.models.case import Case

logger = logging.getLogger(__name__)


class GidResolver:
    """
    Resolves between UUIDs and GIDs for documents and cases.

    Provides simple in-memory caching for ID lookups within a single process.
    """

    def __init__(self):
        """Initialize the resolver with empty caches."""
        # Simple in-memory caches for ID↔GID lookups within a single process
        self._document_gid_cache: Dict[str, Optional[str]] = {}
        self._case_gid_cache: Dict[str, Optional[str]] = {}
        self._document_uuid_cache: Dict[str, Optional[str]] = {}
        self._case_uuid_cache: Dict[str, Optional[str]] = {}

    def resolve_document_gid(self, document_id: Any) -> Optional[str]:
        """
        Resolve document UUID to GID with simple caching.

        Args:
            document_id: Document UUID (as string or UUID object)

        Returns:
            Document GID or None if not found
        """
        if document_id is None:
            return None

        doc_key = str(document_id)
        if doc_key in self._document_gid_cache:
            return self._document_gid_cache[doc_key]

        try:
            uuid_val = UUID(doc_key)
        except (ValueError, TypeError):
            self._document_gid_cache[doc_key] = None
            return None

        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == uuid_val).first()
            gid = document.gid if document else None
        except Exception as exc:
            logger.error(f"Failed to resolve document GID for {doc_key}: {exc}", exc_info=True)
            gid = None
        finally:
            db.close()

        self._document_gid_cache[doc_key] = gid
        return gid

    def resolve_case_gid(self, case_id: Any) -> Optional[str]:
        """
        Resolve case UUID to GID with simple caching.

        Args:
            case_id: Case UUID (as string or UUID object)

        Returns:
            Case GID or None if not found
        """
        if case_id is None:
            return None

        case_key = str(case_id)
        if case_key in self._case_gid_cache:
            return self._case_gid_cache[case_key]

        try:
            uuid_val = UUID(case_key)
        except (ValueError, TypeError):
            self._case_gid_cache[case_key] = None
            return None

        db = SessionLocal()
        try:
            case = db.query(Case).filter(Case.id == uuid_val).first()
            gid = case.gid if case else None
        except Exception as exc:
            logger.error(f"Failed to resolve case GID for {case_key}: {exc}", exc_info=True)
            gid = None
        finally:
            db.close()

        self._case_gid_cache[case_key] = gid
        return gid

    def resolve_document_uuid_from_gid(self, document_gid: str) -> Optional[str]:
        """
        Resolve document GID back to UUID string with caching.

        Args:
            document_gid: Document GID

        Returns:
            Document UUID as string or None if not found
        """
        if not document_gid:
            return None

        if document_gid in self._document_uuid_cache:
            return self._document_uuid_cache[document_gid]

        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.gid == document_gid).first()
            uuid_value = str(document.id) if document else None
        except Exception as exc:
            logger.error(f"Failed to resolve document UUID for GID {document_gid}: {exc}", exc_info=True)
            uuid_value = None
        finally:
            db.close()

        self._document_uuid_cache[document_gid] = uuid_value
        return uuid_value

    def resolve_case_uuid_from_gid(self, case_gid: str) -> Optional[str]:
        """
        Resolve case GID back to UUID string with caching.

        Args:
            case_gid: Case GID

        Returns:
            Case UUID as string or None if not found
        """
        if not case_gid:
            return None

        if case_gid in self._case_uuid_cache:
            return self._case_uuid_cache[case_gid]

        db = SessionLocal()
        try:
            case = db.query(Case).filter(Case.gid == case_gid).first()
            uuid_value = str(case.id) if case else None
        except Exception as exc:
            logger.error(f"Failed to resolve case UUID for GID {case_gid}: {exc}", exc_info=True)
            uuid_value = None
        finally:
            db.close()

        self._case_uuid_cache[case_gid] = uuid_value
        return uuid_value
