"""
Transcript Summarization Service

Provides comprehensive analysis and summarization of legal transcripts using
local Ollama LLM (7B models). Includes:
- Executive summaries
- Key moments extraction
- Timeline creation
- Speaker analysis
- Action items extraction
- Topics and entities identification
"""
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import timedelta
from collections import defaultdict

from app.core.ollama import OllamaClient, ensure_model_available
from app.core.config import settings

logger = logging.getLogger(__name__)


class TranscriptSummarizer:
    """Handles comprehensive transcript summarization and analysis."""

    def __init__(self, model: Optional[str] = None):
        """
        Initialize summarizer with Ollama model.

        Args:
            model: Ollama model name (default: from settings)
        """
        self.model = model or settings.OLLAMA_MODEL_SUMMARIZATION
        self.client = OllamaClient()

    async def ensure_model(self) -> bool:
        """Ensure the model is available."""
        return await ensure_model_available(self.model)

    async def close(self):
        """Close the Ollama client."""
        await self.client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.ensure_model()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _prepare_transcript_text(
        self,
        segments: List[Dict[str, Any]],
        include_timestamps: bool = True,
        include_speakers: bool = True,
        max_chars: int = 8000
    ) -> str:
        """
        Convert transcript segments to formatted text for LLM processing.

        Args:
            segments: List of transcript segments
            include_timestamps: Include timestamps in output
            include_speakers: Include speaker labels in output
            max_chars: Maximum characters to return (truncates if needed)

        Returns:
            Formatted transcript text
        """
        lines = []

        for segment in segments:
            parts = []

            # Add timestamp
            if include_timestamps and 'start' in segment:
                timestamp = self._format_timestamp(segment['start'])
                parts.append(f"[{timestamp}]")

            # Add speaker
            if include_speakers and 'speaker' in segment:
                parts.append(f"{segment['speaker']}:")

            # Add text
            text = segment.get('text', '').strip()
            if text:
                parts.append(text)

            if parts:
                lines.append(' '.join(parts))

        full_text = '\n'.join(lines)

        # Truncate if needed
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "\n[...truncated...]"

        return full_text

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format seconds to HH:MM:SS."""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    async def generate_executive_summary(
        self,
        segments: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a 200-300 word executive summary of the transcript.

        Args:
            segments: List of transcript segments
            metadata: Optional metadata (case name, date, etc.)

        Returns:
            Executive summary text
        """
        logger.info("Generating executive summary")

        # Prepare transcript text
        transcript_text = self._prepare_transcript_text(
            segments,
            include_timestamps=False,
            include_speakers=True,
            max_chars=12000
        )

        # Build context from metadata
        context = ""
        if metadata:
            if 'case_name' in metadata:
                context += f"Case: {metadata['case_name']}\n"
            if 'date' in metadata:
                context += f"Date: {metadata['date']}\n"
            if 'type' in metadata:
                context += f"Type: {metadata['type']}\n"

        system_prompt = """You are a legal transcript analyzer specializing in summarizing depositions, hearings, and legal proceedings. Create concise, accurate executive summaries that capture the essential points, key testimony, and overall purpose of the proceeding."""

        prompt = f"""Analyze this legal transcript and create a concise executive summary (200-300 words).

{context}
Transcript:
{transcript_text}

Provide a well-structured executive summary covering:
1. Type of proceeding and participants
2. Main topics discussed
3. Key testimony or statements
4. Important decisions or outcomes
5. Notable developments or issues

Executive Summary:"""

        try:
            summary = await self.client.generate(
                model=self.model,
                prompt=prompt,
                system=system_prompt,
                options={
                    "temperature": 0.3,  # Lower for more factual
                    "num_predict": 400   # Limit length
                }
            )
            return summary.strip()
        except Exception as e:
            logger.error(f"Failed to generate executive summary: {e}")
            return "Error generating summary"

    async def extract_key_moments(
        self,
        segments: List[Dict[str, Any]],
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Extract the top N key moments from the transcript.

        Args:
            segments: List of transcript segments
            top_n: Number of key moments to extract

        Returns:
            List of key moments with timestamps and descriptions
        """
        logger.info(f"Extracting top {top_n} key moments")

        transcript_text = self._prepare_transcript_text(
            segments,
            include_timestamps=True,
            include_speakers=True,
            max_chars=10000
        )

        system_prompt = """You are a legal analyst identifying critical moments in legal proceedings. Focus on testimony that reveals important facts, contradictions, admissions, objections, rulings, or significant exchanges."""

        prompt = f"""Analyze this legal transcript and identify the {top_n} most important moments.

Transcript:
{transcript_text}

For each key moment, provide:
- Timestamp (from the transcript)
- Brief description (1-2 sentences)
- Reason for importance

Return as JSON array with format:
[
  {{
    "timestamp": "HH:MM:SS",
    "description": "Brief description",
    "importance": "Reason this moment is significant"
  }}
]

JSON:"""

        try:
            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                system=system_prompt,
                format="json",
                options={
                    "temperature": 0.3,
                    "num_predict": 1000
                }
            )

            key_moments = json.loads(response)

            # Ensure it's a list
            if not isinstance(key_moments, list):
                key_moments = []

            return key_moments[:top_n]

        except Exception as e:
            logger.error(f"Failed to extract key moments: {e}")
            return []

    async def create_timeline(
        self,
        segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create a chronological timeline of events discussed in the transcript.

        Args:
            segments: List of transcript segments

        Returns:
            List of timeline events with dates and descriptions
        """
        logger.info("Creating timeline from transcript")

        transcript_text = self._prepare_transcript_text(
            segments,
            include_timestamps=True,
            include_speakers=True,
            max_chars=10000
        )

        system_prompt = """You are a legal analyst extracting chronological events from testimony and legal proceedings. Identify dates, events, and their sequence as discussed in the transcript."""

        prompt = f"""Analyze this legal transcript and extract all significant events mentioned, creating a chronological timeline.

Transcript:
{transcript_text}

For each event, provide:
- Date (if mentioned, or "Unknown")
- Event description
- Reference (who mentioned it or context)

Return as JSON array sorted chronologically:
[
  {{
    "date": "YYYY-MM-DD or description",
    "event": "What happened",
    "reference": "Who mentioned it or source"
  }}
]

JSON:"""

        try:
            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                system=system_prompt,
                format="json",
                options={
                    "temperature": 0.3,
                    "num_predict": 1500
                }
            )

            timeline = json.loads(response)

            # Ensure it's a list
            if not isinstance(timeline, list):
                timeline = []

            return timeline

        except Exception as e:
            logger.error(f"Failed to create timeline: {e}")
            return []

    def analyze_speakers(
        self,
        segments: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze speaker statistics (speaking time, word count, etc.).

        This is a computational analysis, not LLM-based.

        Args:
            segments: List of transcript segments

        Returns:
            Dict mapping speaker IDs to their statistics
        """
        logger.info("Analyzing speaker statistics")

        speaker_stats = defaultdict(lambda: {
            'speaking_time': 0.0,
            'segment_count': 0,
            'word_count': 0,
            'avg_segment_length': 0.0,
            'total_chars': 0
        })

        for segment in segments:
            speaker = segment.get('speaker', 'UNKNOWN')
            text = segment.get('text', '')
            start = segment.get('start', 0.0)
            end = segment.get('end', 0.0)

            duration = end - start
            words = len(text.split())
            chars = len(text)

            speaker_stats[speaker]['speaking_time'] += duration
            speaker_stats[speaker]['segment_count'] += 1
            speaker_stats[speaker]['word_count'] += words
            speaker_stats[speaker]['total_chars'] += chars

        # Calculate averages
        for speaker, stats in speaker_stats.items():
            if stats['segment_count'] > 0:
                stats['avg_segment_length'] = stats['speaking_time'] / stats['segment_count']

        # Convert to regular dict and add percentages
        total_time = sum(s['speaking_time'] for s in speaker_stats.values())
        total_words = sum(s['word_count'] for s in speaker_stats.values())

        result = {}
        for speaker, stats in speaker_stats.items():
            result[speaker] = {
                'speaking_time_seconds': round(stats['speaking_time'], 2),
                'speaking_time_formatted': self._format_timestamp(stats['speaking_time']),
                'speaking_time_percentage': round((stats['speaking_time'] / total_time * 100) if total_time > 0 else 0, 1),
                'segment_count': stats['segment_count'],
                'word_count': stats['word_count'],
                'word_percentage': round((stats['word_count'] / total_words * 100) if total_words > 0 else 0, 1),
                'avg_segment_length_seconds': round(stats['avg_segment_length'], 2),
                'total_characters': stats['total_chars']
            }

        return result

    async def extract_action_items(
        self,
        segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract action items, decisions, agreements, and follow-ups.

        Args:
            segments: List of transcript segments

        Returns:
            List of action items with details
        """
        logger.info("Extracting action items")

        transcript_text = self._prepare_transcript_text(
            segments,
            include_timestamps=True,
            include_speakers=True,
            max_chars=10000
        )

        system_prompt = """You are a legal analyst identifying commitments, decisions, agreements, and action items from legal proceedings. Focus on explicit statements of intent, court orders, stipulations, and agreed-upon next steps."""

        prompt = f"""Analyze this legal transcript and extract all action items, decisions, and commitments.

Transcript:
{transcript_text}

For each action item, provide:
- Type (decision, agreement, order, follow-up, etc.)
- Description
- Responsible party (if identified)
- Deadline or timing (if mentioned)
- Timestamp (from transcript)

Return as JSON array:
[
  {{
    "type": "Type of action",
    "description": "What needs to be done",
    "responsible": "Who is responsible",
    "deadline": "When it's due (if mentioned)",
    "timestamp": "HH:MM:SS"
  }}
]

JSON:"""

        try:
            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                system=system_prompt,
                format="json",
                options={
                    "temperature": 0.3,
                    "num_predict": 1200
                }
            )

            action_items = json.loads(response)

            # Ensure it's a list
            if not isinstance(action_items, list):
                action_items = []

            return action_items

        except Exception as e:
            logger.error(f"Failed to extract action items: {e}")
            return []

    async def extract_topics_and_entities(
        self,
        segments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract topics, parties, dates, legal terms, and citations.

        Args:
            segments: List of transcript segments

        Returns:
            Dict containing topics, entities, dates, citations, etc.
        """
        logger.info("Extracting topics and entities")

        transcript_text = self._prepare_transcript_text(
            segments,
            include_timestamps=False,
            include_speakers=True,
            max_chars=10000
        )

        system_prompt = """You are a legal entity and topic extractor. Identify all relevant legal information including parties, dates, legal concepts, citations, and key topics from legal proceedings."""

        prompt = f"""Analyze this legal transcript and extract structured information.

Transcript:
{transcript_text}

Extract and return JSON with:
- topics: Main topics/subjects discussed (list of strings)
- parties: People and organizations mentioned (list of strings)
- dates: Important dates mentioned (list of strings)
- legal_terms: Legal concepts/terminology used (list of strings)
- citations: Case citations or legal references (list of strings)
- locations: Court locations, addresses, places (list of strings)
- exhibits: Documents or evidence referenced (list of strings)

JSON:"""

        try:
            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                system=system_prompt,
                format="json",
                options={
                    "temperature": 0.3,
                    "num_predict": 1200
                }
            )

            entities = json.loads(response)

            # Ensure proper structure
            default_structure = {
                'topics': [],
                'parties': [],
                'dates': [],
                'legal_terms': [],
                'citations': [],
                'locations': [],
                'exhibits': []
            }

            # Merge with defaults
            if isinstance(entities, dict):
                for key in default_structure:
                    if key not in entities:
                        entities[key] = []
                    elif not isinstance(entities[key], list):
                        entities[key] = []
            else:
                entities = default_structure

            return entities

        except Exception as e:
            logger.error(f"Failed to extract topics and entities: {e}")
            return {
                'topics': [],
                'parties': [],
                'dates': [],
                'legal_terms': [],
                'citations': [],
                'locations': [],
                'exhibits': []
            }

    async def generate_full_analysis(
        self,
        segments: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        include_components: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive transcript analysis with all components.

        Args:
            segments: List of transcript segments
            metadata: Optional metadata about the transcript
            include_components: List of components to include, or None for all
                Options: 'summary', 'key_moments', 'timeline', 'speakers',
                        'action_items', 'topics_entities'

        Returns:
            Dict containing all analysis results
        """
        logger.info("Generating full transcript analysis")

        # Default to all components
        if include_components is None:
            include_components = [
                'summary', 'key_moments', 'timeline',
                'speakers', 'action_items', 'topics_entities'
            ]

        result = {
            'metadata': metadata or {},
            'analysis': {}
        }

        # Executive Summary
        if 'summary' in include_components:
            result['analysis']['executive_summary'] = await self.generate_executive_summary(
                segments, metadata
            )

        # Key Moments
        if 'key_moments' in include_components:
            result['analysis']['key_moments'] = await self.extract_key_moments(segments)

        # Timeline
        if 'timeline' in include_components:
            result['analysis']['timeline'] = await self.create_timeline(segments)

        # Speaker Analysis
        if 'speakers' in include_components:
            result['analysis']['speaker_stats'] = self.analyze_speakers(segments)

        # Action Items
        if 'action_items' in include_components:
            result['analysis']['action_items'] = await self.extract_action_items(segments)

        # Topics and Entities
        if 'topics_entities' in include_components:
            topics_entities = await self.extract_topics_and_entities(segments)
            result['analysis']['topics'] = topics_entities.get('topics', [])
            result['analysis']['entities'] = {
                'parties': topics_entities.get('parties', []),
                'dates': topics_entities.get('dates', []),
                'legal_terms': topics_entities.get('legal_terms', []),
                'citations': topics_entities.get('citations', []),
                'locations': topics_entities.get('locations', []),
                'exhibits': topics_entities.get('exhibits', [])
            }

        logger.info("Full transcript analysis completed")
        return result


# Convenience functions
async def summarize_transcript(
    segments: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive transcript summary and analysis.

    Args:
        segments: List of transcript segments
        metadata: Optional metadata
        model: Optional Ollama model name

    Returns:
        Full analysis results
    """
    async with TranscriptSummarizer(model=model) as summarizer:
        return await summarizer.generate_full_analysis(segments, metadata)


async def quick_summary(
    segments: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None
) -> str:
    """
    Generate just the executive summary.

    Args:
        segments: List of transcript segments
        metadata: Optional metadata
        model: Optional Ollama model name

    Returns:
        Executive summary text
    """
    async with TranscriptSummarizer(model=model) as summarizer:
        return await summarizer.generate_executive_summary(segments, metadata)
