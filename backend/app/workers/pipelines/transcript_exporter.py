"""
Professional Legal Transcript Exporter

Exports transcription segments to professionally formatted DOCX documents
using docxtpl templates. Designed for legal proceedings, depositions, and
court transcripts.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from docxtpl import DocxTemplate

logger = logging.getLogger(__name__)


@dataclass
class Speaker:
    """Represents a speaker in the transcript."""
    id: str
    label: str
    role: Optional[str] = None
    affiliation: Optional[str] = None


@dataclass
class TranscriptSegment:
    """Represents a single segment of transcribed speech."""
    speaker_id: str
    speaker_label: str
    text: str
    start_time: float
    end_time: float
    segment_number: int
    confidence: Optional[float] = None


class TranscriptExporter:
    """
    Professional legal transcript exporter using DOCX templates.

    Features:
    - Speaker identification and labeling
    - Precise timestamps for each segment
    - Professional legal formatting
    - Case metadata header
    - Table of speakers/participants
    - Page numbering and headers
    - Suitable for court submissions
    """

    def __init__(self, template_path: Optional[str] = None):
        """
        Initialize the transcript exporter.

        Args:
            template_path: Path to custom DOCX template. If None, uses default template.
        """
        if template_path:
            self.template_path = Path(template_path)
        else:
            # Default template path relative to this file
            self.template_path = (
                Path(__file__).parent.parent / "templates" / "transcript_template.docx"
            )

        if not self.template_path.exists():
            raise FileNotFoundError(
                f"Template file not found: {self.template_path}. "
                "Please ensure the template exists or provide a custom template path."
            )

        logger.info(f"Initialized TranscriptExporter with template: {self.template_path}")

    def export_to_docx(
        self,
        segments: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        output_path: str,
    ) -> bool:
        """
        Export transcript segments to a professionally formatted DOCX file.

        Args:
            segments: List of transcript segments with speaker, text, and timing info.
                     Each segment should have:
                     - speaker_id: Speaker identifier
                     - speaker_label: Speaker display name
                     - text: Transcribed text
                     - start_time: Start timestamp in seconds
                     - end_time: End timestamp in seconds
            metadata: Case and document metadata:
                     - case_number: Case identification number
                     - case_name: Name of the case
                     - client: Client name
                     - matter_type: Type of legal matter
                     - document_name: Name of the audio/video file
                     - date: Date of recording/proceeding
                     - location: Location of proceeding (optional)
                     - witness: Primary witness/deponent (optional)
                     - duration: Total duration in seconds
            output_path: Path where the DOCX file should be saved

        Returns:
            True if export was successful, False otherwise
        """
        try:
            logger.info(f"Exporting transcript with {len(segments)} segments to {output_path}")

            # Load the template
            doc = DocxTemplate(str(self.template_path))

            # Prepare speaker information
            speakers = self._extract_speakers(segments)

            # Prepare formatted segments
            formatted_segments = self._format_segments(segments)

            # Prepare metadata with defaults
            export_metadata = self._prepare_metadata(metadata, len(segments))

            # Prepare context for template rendering
            context = {
                # Case information
                "case_number": export_metadata.get("case_number", "N/A"),
                "case_name": export_metadata.get("case_name", "N/A"),
                "client": export_metadata.get("client", "N/A"),
                "matter_type": export_metadata.get("matter_type", "N/A"),

                # Document information
                "document_name": export_metadata.get("document_name", "N/A"),
                "proceeding_date": export_metadata.get("date", "N/A"),
                "location": export_metadata.get("location", "N/A"),
                "witness": export_metadata.get("witness", "N/A"),

                # Transcript information
                "total_duration": self._format_duration(export_metadata.get("duration", 0)),
                "segment_count": len(segments),
                "export_date": datetime.now().strftime("%B %d, %Y"),
                "export_time": datetime.now().strftime("%I:%M %p"),

                # Speakers table
                "speakers": speakers,
                "speaker_count": len(speakers),

                # Transcript segments
                "segments": formatted_segments,
            }

            # Render the template with context
            doc.render(context)

            # Save the document
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path_obj))

            logger.info(f"Successfully exported transcript to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting transcript: {e}", exc_info=True)
            return False

    def _extract_speakers(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract unique speakers from segments.

        Args:
            segments: List of transcript segments

        Returns:
            List of speaker dictionaries with id and label
        """
        speakers_map = {}

        for segment in segments:
            speaker_id = segment.get("speaker_id", "UNKNOWN")
            speaker_label = segment.get("speaker_label", f"Speaker {speaker_id}")

            if speaker_id not in speakers_map:
                speakers_map[speaker_id] = {
                    "id": speaker_id,
                    "label": speaker_label,
                    "role": segment.get("speaker_role"),
                    "affiliation": segment.get("speaker_affiliation"),
                    "appearance_count": 0,
                }

            speakers_map[speaker_id]["appearance_count"] += 1

        # Convert to sorted list
        speakers = sorted(
            speakers_map.values(),
            key=lambda x: x["appearance_count"],
            reverse=True
        )

        return speakers

    def _format_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format transcript segments for template rendering.

        Args:
            segments: Raw transcript segments

        Returns:
            List of formatted segment dictionaries
        """
        formatted = []

        for i, segment in enumerate(segments, start=1):
            start_time = segment.get("start_time", 0)
            end_time = segment.get("end_time", 0)

            formatted.append({
                "number": i,
                "speaker_label": segment.get("speaker_label", "Unknown Speaker"),
                "text": segment.get("text", "").strip(),
                "timestamp": self._format_timestamp(start_time),
                "time_range": f"{self._format_timestamp(start_time)} - {self._format_timestamp(end_time)}",
                "duration": self._format_duration(end_time - start_time),
                "confidence": segment.get("confidence"),
            })

        return formatted

    def _prepare_metadata(
        self, metadata: Dict[str, Any], segment_count: int
    ) -> Dict[str, Any]:
        """
        Prepare and validate metadata for export.

        Args:
            metadata: Raw metadata dictionary
            segment_count: Number of segments

        Returns:
            Prepared metadata dictionary with defaults
        """
        prepared = metadata.copy()

        # Set defaults
        if "date" not in prepared:
            prepared["date"] = datetime.now().strftime("%B %d, %Y")
        elif isinstance(prepared["date"], datetime):
            prepared["date"] = prepared["date"].strftime("%B %d, %Y")

        if "segment_count" not in prepared:
            prepared["segment_count"] = segment_count

        return prepared

    def _format_timestamp(self, seconds: float) -> str:
        """
        Format seconds into HH:MM:SS timestamp.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _format_duration(self, seconds: float) -> str:
        """
        Format duration in a human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
        if seconds < 60:
            return f"{int(seconds)} seconds"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes} min {secs} sec"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours} hr {minutes} min"

    def export_segments_list(
        self,
        segments: List[TranscriptSegment],
        metadata: Dict[str, Any],
        output_path: str,
    ) -> bool:
        """
        Export transcript segments from TranscriptSegment dataclass instances.

        Args:
            segments: List of TranscriptSegment instances
            metadata: Case and document metadata
            output_path: Path where the DOCX file should be saved

        Returns:
            True if export was successful, False otherwise
        """
        # Convert TranscriptSegment instances to dictionaries
        segment_dicts = [
            {
                "speaker_id": seg.speaker_id,
                "speaker_label": seg.speaker_label,
                "text": seg.text,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "segment_number": seg.segment_number,
                "confidence": seg.confidence,
            }
            for seg in segments
        ]

        return self.export_to_docx(segment_dicts, metadata, output_path)


def export_transcript(
    segments: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    output_path: str,
    template_path: Optional[str] = None,
) -> bool:
    """
    Convenience function to export a transcript.

    Args:
        segments: List of transcript segments
        metadata: Case and document metadata
        output_path: Path where the DOCX file should be saved
        template_path: Optional custom template path

    Returns:
        True if export was successful, False otherwise
    """
    exporter = TranscriptExporter(template_path=template_path)
    return exporter.export_to_docx(segments, metadata, output_path)


# Example usage
if __name__ == "__main__":
    # Example transcript data
    example_segments = [
        {
            "speaker_id": "1",
            "speaker_label": "Attorney Johnson",
            "text": "Good morning. Please state your name for the record.",
            "start_time": 0.0,
            "end_time": 3.5,
            "confidence": 0.95,
        },
        {
            "speaker_id": "2",
            "speaker_label": "Dr. Emily Chen",
            "text": "My name is Emily Chen, C-H-E-N.",
            "start_time": 4.0,
            "end_time": 7.2,
            "confidence": 0.98,
        },
        {
            "speaker_id": "1",
            "speaker_label": "Attorney Johnson",
            "text": "Thank you. Dr. Chen, can you describe your professional background?",
            "start_time": 8.0,
            "end_time": 12.5,
            "confidence": 0.96,
        },
    ]

    example_metadata = {
        "case_number": "2025-CV-12345",
        "case_name": "Smith v. Johnson Medical Center",
        "client": "Smith Family Trust",
        "matter_type": "Medical Malpractice",
        "document_name": "Deposition_Chen_Emily_20250109.mp3",
        "date": "January 9, 2025",
        "location": "Law Offices of Johnson & Associates",
        "witness": "Dr. Emily Chen",
        "duration": 3600,  # 1 hour
    }

    # Export the transcript
    success = export_transcript(
        segments=example_segments,
        metadata=example_metadata,
        output_path="/tmp/example_transcript.docx",
    )

    if success:
        print("Transcript exported successfully!")
    else:
        print("Failed to export transcript.")
