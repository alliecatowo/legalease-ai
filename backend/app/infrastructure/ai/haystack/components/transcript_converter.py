"""
TranscriptSegmentConverter component for Haystack pipelines.

Converts transcript segments into Haystack Documents for indexing.
"""

import logging
from typing import List, Dict, Any, Optional

from haystack import component, Document

from app.domain.evidence.entities.transcript import TranscriptSegment, Speaker

logger = logging.getLogger(__name__)


@component
class TranscriptSegmentConverter:
    """
    Haystack component that converts transcript segments to Documents.

    Converts TranscriptSegment entities into Haystack Documents with
    proper metadata for speaker identification and temporal filtering.

    Features:
    - Speaker information preservation
    - Timing metadata extraction
    - Segment type handling
    - Confidence score tracking

    Usage:
        >>> converter = TranscriptSegmentConverter()
        >>> result = converter.run(
        ...     segments=[seg1, seg2],
        ...     transcript_id=transcript_uuid,
        ...     case_id=case_uuid
        ... )
        >>> documents = result["documents"]
    """

    def __init__(
        self,
        include_speaker_turns: bool = True,
        min_segment_length: int = 5,
    ):
        """
        Initialize the transcript segment converter.

        Args:
            include_speaker_turns: Whether to include speaker turn metadata
            min_segment_length: Minimum text length to keep (shorter segments skipped)
        """
        self.include_speaker_turns = include_speaker_turns
        self.min_segment_length = min_segment_length

        logger.info(
            f"Initialized TranscriptSegmentConverter "
            f"(include_speaker_turns={include_speaker_turns}, "
            f"min_segment_length={min_segment_length})"
        )

    @component.output_types(documents=List[Document], segment_count=int)
    def run(
        self,
        segments: List[TranscriptSegment],
        transcript_id: str,
        case_id: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Convert transcript segments to Haystack Documents.

        Args:
            segments: List of TranscriptSegment entities
            transcript_id: UUID of the transcript
            case_id: UUID of the case
            meta: Optional additional metadata to add to all documents

        Returns:
            Dictionary with:
                - documents: List of Haystack Documents
                - segment_count: Number of segments converted
        """
        if not segments:
            logger.warning("No segments provided to TranscriptSegmentConverter")
            return {"documents": [], "segment_count": 0}

        documents = []

        for i, segment in enumerate(segments):
            try:
                # Skip short segments
                if len(segment.text.strip()) < self.min_segment_length:
                    logger.debug(
                        f"Skipping short segment {segment.id} "
                        f"({len(segment.text)} chars)"
                    )
                    continue

                # Build metadata
                segment_meta = {
                    "transcript_id": transcript_id,
                    "case_id": case_id,
                    "segment_id": segment.id,
                    "start_time": segment.start,
                    "end_time": segment.end,
                    "duration": segment.duration,
                    "segment_type": segment.segment_type.value,
                    "position": i,
                }

                # Add speaker information if available
                if segment.speaker:
                    segment_meta["speaker_id"] = segment.speaker.id
                    if segment.speaker.name:
                        segment_meta["speaker_name"] = segment.speaker.name
                    if segment.speaker.confidence is not None:
                        segment_meta["speaker_confidence"] = segment.speaker.confidence

                # Add confidence if available
                if segment.confidence is not None:
                    segment_meta["transcription_confidence"] = segment.confidence

                # Add word-level timing if available
                if segment.words:
                    segment_meta["word_count"] = len(segment.words)
                    segment_meta["has_word_timing"] = True

                # Add user metadata
                if meta:
                    segment_meta.update(meta)

                # Create Haystack Document
                document = Document(
                    content=segment.text,
                    meta=segment_meta,
                )

                documents.append(document)

            except Exception as e:
                logger.error(
                    f"Failed to convert segment {segment.id}: {e}",
                    exc_info=True
                )
                continue

        logger.info(
            f"Converted {len(documents)} transcript segments "
            f"from {len(segments)} total segments"
        )

        return {
            "documents": documents,
            "segment_count": len(documents),
        }


@component
class SpeakerAwareChunker:
    """
    Haystack component that chunks transcript segments by speaker turns.

    Groups consecutive segments from the same speaker into larger chunks
    for better context during embedding and search.

    Features:
    - Speaker turn detection
    - Configurable max chunk size
    - Overlap support for context
    - Metadata preservation

    Usage:
        >>> chunker = SpeakerAwareChunker(max_chunk_size=500)
        >>> result = chunker.run(documents=[doc1, doc2, doc3])
        >>> chunked_docs = result["documents"]
    """

    def __init__(
        self,
        max_chunk_size: int = 500,
        overlap_size: int = 50,
        merge_same_speaker: bool = True,
    ):
        """
        Initialize the speaker-aware chunker.

        Args:
            max_chunk_size: Maximum chunk size in characters
            overlap_size: Overlap between chunks in characters
            merge_same_speaker: Whether to merge consecutive segments from same speaker
        """
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.merge_same_speaker = merge_same_speaker

        logger.info(
            f"Initialized SpeakerAwareChunker "
            f"(max_chunk_size={max_chunk_size}, "
            f"overlap_size={overlap_size}, "
            f"merge_same_speaker={merge_same_speaker})"
        )

    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Chunk documents by speaker turns.

        Args:
            documents: List of transcript segment Documents

        Returns:
            Dictionary with:
                - documents: List of chunked Documents
        """
        if not documents:
            logger.warning("No documents provided to SpeakerAwareChunker")
            return {"documents": []}

        if not self.merge_same_speaker:
            # No chunking needed
            logger.debug("Speaker merging disabled, returning original documents")
            return {"documents": documents}

        # Sort documents by position (should already be sorted)
        sorted_docs = sorted(
            documents,
            key=lambda d: d.meta.get("position", 0)
        )

        chunked_documents = []
        current_chunk_text = []
        current_chunk_meta = None
        current_speaker = None
        current_start_time = None
        current_end_time = None

        for doc in sorted_docs:
            speaker_id = doc.meta.get("speaker_id")
            text = doc.content
            start_time = doc.meta.get("start_time")
            end_time = doc.meta.get("end_time")

            # Check if we need to start a new chunk
            should_split = (
                # Different speaker
                (speaker_id != current_speaker)
                # Or chunk is too large
                or (
                    current_chunk_text
                    and len(" ".join(current_chunk_text) + " " + text) > self.max_chunk_size
                )
            )

            if should_split and current_chunk_text:
                # Save current chunk
                chunk_text = " ".join(current_chunk_text)
                chunk_doc = Document(
                    content=chunk_text,
                    meta={
                        **current_chunk_meta,
                        "start_time": current_start_time,
                        "end_time": current_end_time,
                        "duration": current_end_time - current_start_time,
                        "chunked": True,
                        "chunk_segment_count": len(current_chunk_text),
                    },
                )
                chunked_documents.append(chunk_doc)

                # Reset
                current_chunk_text = []
                current_chunk_meta = None
                current_speaker = None

            # Add to current chunk
            if not current_chunk_text:
                # Start new chunk
                current_chunk_meta = doc.meta.copy()
                current_speaker = speaker_id
                current_start_time = start_time
                current_end_time = end_time
            else:
                # Update end time
                current_end_time = end_time

            current_chunk_text.append(text)

        # Save final chunk
        if current_chunk_text:
            chunk_text = " ".join(current_chunk_text)
            chunk_doc = Document(
                content=chunk_text,
                meta={
                    **current_chunk_meta,
                    "start_time": current_start_time,
                    "end_time": current_end_time,
                    "duration": current_end_time - current_start_time,
                    "chunked": True,
                    "chunk_segment_count": len(current_chunk_text),
                },
            )
            chunked_documents.append(chunk_doc)

        logger.info(
            f"Chunked {len(documents)} segments into {len(chunked_documents)} chunks"
        )

        return {"documents": chunked_documents}
