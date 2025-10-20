"""
CommunicationConverter component for Haystack pipelines.

Converts communication entities (messages, emails, chats) into Haystack Documents.
"""

import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict

from haystack import component, Document

from app.domain.evidence.entities.communication import Communication

logger = logging.getLogger(__name__)


@component
class CommunicationConverter:
    """
    Haystack component that converts Communication entities to Documents.

    Converts Communication entities from forensic exports (Cellebrite)
    into Haystack Documents with proper metadata for participant and
    thread-based filtering.

    Features:
    - Participant information preservation
    - Thread grouping metadata
    - Platform and device tracking
    - Attachment metadata

    Usage:
        >>> converter = CommunicationConverter()
        >>> result = converter.run(
        ...     communications=[comm1, comm2],
        ...     case_id=case_uuid
        ... )
        >>> documents = result["documents"]
    """

    def __init__(
        self,
        min_body_length: int = 1,
        include_attachments: bool = True,
    ):
        """
        Initialize the communication converter.

        Args:
            min_body_length: Minimum message body length to keep
            include_attachments: Whether to include attachment metadata
        """
        self.min_body_length = min_body_length
        self.include_attachments = include_attachments

        logger.info(
            f"Initialized CommunicationConverter "
            f"(min_body_length={min_body_length}, "
            f"include_attachments={include_attachments})"
        )

    @component.output_types(documents=List[Document], communication_count=int)
    def run(
        self,
        communications: List[Communication],
        case_id: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Convert communications to Haystack Documents.

        Args:
            communications: List of Communication entities
            case_id: UUID of the case
            meta: Optional additional metadata to add to all documents

        Returns:
            Dictionary with:
                - documents: List of Haystack Documents
                - communication_count: Number of communications converted
        """
        if not communications:
            logger.warning("No communications provided to CommunicationConverter")
            return {"documents": [], "communication_count": 0}

        documents = []

        for i, comm in enumerate(communications):
            try:
                # Skip empty messages
                if len(comm.body.strip()) < self.min_body_length:
                    logger.debug(
                        f"Skipping empty communication {comm.id} "
                        f"({len(comm.body)} chars)"
                    )
                    continue

                # Build metadata
                comm_meta = {
                    "case_id": case_id,
                    "communication_id": str(comm.id),
                    "thread_id": comm.thread_id,
                    "sender_id": comm.sender.identifier,
                    "sender_name": comm.sender.name or comm.sender.identifier,
                    "participant_ids": [p.identifier for p in comm.participants],
                    "participant_names": [
                        p.name or p.identifier for p in comm.participants
                    ],
                    "timestamp": comm.timestamp.isoformat(),
                    "platform": comm.platform.value,
                    "communication_type": comm.communication_type.value,
                    "device_id": comm.device_id,
                    "has_attachments": comm.has_attachments(),
                    "position": i,
                }

                # Add attachment details if enabled
                if self.include_attachments and comm.has_attachments():
                    comm_meta["attachment_count"] = comm.get_attachment_count()
                    comm_meta["attachment_filenames"] = [
                        att.filename for att in comm.attachments
                    ]
                    comm_meta["attachment_types"] = [
                        att.mime_type for att in comm.attachments
                    ]

                # Add metadata from communication entity
                comm_meta.update(comm.metadata)

                # Add user metadata
                if meta:
                    comm_meta.update(meta)

                # Create Haystack Document
                document = Document(
                    content=comm.body,
                    meta=comm_meta,
                )

                documents.append(document)

            except Exception as e:
                logger.error(
                    f"Failed to convert communication {comm.id}: {e}",
                    exc_info=True
                )
                continue

        logger.info(
            f"Converted {len(documents)} communications "
            f"from {len(communications)} total communications"
        )

        return {
            "documents": documents,
            "communication_count": len(documents),
        }


@component
class ThreadGrouper:
    """
    Haystack component that groups messages by thread.

    Groups consecutive messages in the same thread for better context
    during embedding and search. This is especially useful for
    conversational communications like text messages and chats.

    Features:
    - Thread-based grouping
    - Configurable max messages per group
    - Time-window support
    - Metadata aggregation

    Usage:
        >>> grouper = ThreadGrouper(max_messages_per_group=10)
        >>> result = grouper.run(documents=[doc1, doc2, doc3])
        >>> grouped_docs = result["documents"]
    """

    def __init__(
        self,
        max_messages_per_group: int = 10,
        max_time_gap_seconds: Optional[float] = None,
        merge_threads: bool = True,
    ):
        """
        Initialize the thread grouper.

        Args:
            max_messages_per_group: Maximum messages to include in a group
            max_time_gap_seconds: Maximum time gap between messages (None = no limit)
            merge_threads: Whether to merge messages in same thread
        """
        self.max_messages_per_group = max_messages_per_group
        self.max_time_gap_seconds = max_time_gap_seconds
        self.merge_threads = merge_threads

        logger.info(
            f"Initialized ThreadGrouper "
            f"(max_messages_per_group={max_messages_per_group}, "
            f"max_time_gap_seconds={max_time_gap_seconds})"
        )

    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Group documents by thread.

        Args:
            documents: List of communication Documents

        Returns:
            Dictionary with:
                - documents: List of grouped Documents
        """
        if not documents:
            logger.warning("No documents provided to ThreadGrouper")
            return {"documents": []}

        if not self.merge_threads:
            # No grouping needed
            logger.debug("Thread merging disabled, returning original documents")
            return {"documents": documents}

        # Group documents by thread_id
        threads = defaultdict(list)
        for doc in documents:
            thread_id = doc.meta.get("thread_id", "unknown")
            threads[thread_id].append(doc)

        # Sort each thread by timestamp
        for thread_id in threads:
            threads[thread_id].sort(
                key=lambda d: d.meta.get("timestamp", "")
            )

        # Create grouped documents
        grouped_documents = []

        for thread_id, thread_docs in threads.items():
            # Group messages within thread
            current_group = []
            current_meta = None

            for doc in thread_docs:
                # Check if we should start a new group
                should_split = (
                    # Group is full
                    len(current_group) >= self.max_messages_per_group
                    # Or time gap is too large (if configured)
                    or (
                        self.max_time_gap_seconds is not None
                        and current_group
                        and self._time_gap_exceeded(current_group[-1], doc)
                    )
                )

                if should_split and current_group:
                    # Save current group
                    group_doc = self._create_group_document(
                        current_group,
                        thread_id
                    )
                    grouped_documents.append(group_doc)

                    # Reset
                    current_group = []
                    current_meta = None

                # Add to current group
                current_group.append(doc)

            # Save final group
            if current_group:
                group_doc = self._create_group_document(
                    current_group,
                    thread_id
                )
                grouped_documents.append(group_doc)

        logger.info(
            f"Grouped {len(documents)} messages into "
            f"{len(grouped_documents)} thread groups"
        )

        return {"documents": grouped_documents}

    def _time_gap_exceeded(self, doc1: Document, doc2: Document) -> bool:
        """
        Check if time gap between documents exceeds threshold.

        Args:
            doc1: First document
            doc2: Second document

        Returns:
            True if time gap exceeds threshold
        """
        from datetime import datetime

        try:
            time1 = datetime.fromisoformat(doc1.meta.get("timestamp", ""))
            time2 = datetime.fromisoformat(doc2.meta.get("timestamp", ""))
            gap = abs((time2 - time1).total_seconds())
            return gap > self.max_time_gap_seconds
        except Exception:
            return False

    def _create_group_document(
        self,
        docs: List[Document],
        thread_id: str
    ) -> Document:
        """
        Create a grouped document from multiple messages.

        Args:
            docs: List of documents to group
            thread_id: Thread identifier

        Returns:
            Grouped Haystack Document
        """
        # Combine message bodies
        combined_text = "\n".join(
            f"[{doc.meta.get('sender_name', 'Unknown')}]: {doc.content}"
            for doc in docs
        )

        # Aggregate metadata
        first_doc = docs[0]
        last_doc = docs[-1]

        group_meta = {
            **first_doc.meta,
            "thread_id": thread_id,
            "message_count": len(docs),
            "start_timestamp": first_doc.meta.get("timestamp"),
            "end_timestamp": last_doc.meta.get("timestamp"),
            "grouped": True,
            # Aggregate participants
            "all_senders": list(set(
                doc.meta.get("sender_name", "Unknown")
                for doc in docs
            )),
        }

        return Document(
            content=combined_text,
            meta=group_meta,
        )
