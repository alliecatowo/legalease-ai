"""
Speaker Name Identification Pipeline

A modular, conversation-aware system for identifying speaker names from transcripts.

Architecture:
- Strategy pattern for multiple extraction methods (spaCy NER, patterns, filename)
- Full conversation context analysis (not just first N segments)
- Evidence-based confidence scoring
- SOLID principles: each class has single responsibility
- Async/concurrent processing for scalability

Usage:
    pipeline = SpeakerIdentificationPipeline()
    speaker_names = await pipeline.identify_speakers(segments, filename)
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict, Counter
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class NameContextType(Enum):
    """Type of context in which a name appears"""
    SELF_IDENTIFICATION = "self_id"  # "I'm John" - speaker identifies themselves
    VOCATIVE = "vocative"  # "John?" - addressing someone
    POSSESSIVE = "possessive"  # "John's car" - possessive reference
    MENTION = "mention"  # "John said..." - third-person mention
    FILENAME = "filename"  # From audio/video filename
    UNKNOWN = "unknown"


@dataclass
class NameEvidence:
    """Evidence for a name appearing in the conversation"""
    name: str
    context_type: NameContextType
    speaker_id: Optional[str]  # Which speaker said/exhibited this
    segment_index: int
    text_snippet: str
    confidence: float  # 0.0 to 1.0
    timestamp: float  # When in the conversation
    linguistic_features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """
    Full conversation context for holistic analysis.

    This captures the entire conversation state, not just isolated segments,
    enabling proper co-reference resolution and speaker pattern analysis.
    """
    segments: List[Dict[str, Any]]
    speakers: List[str]
    filename: Optional[str]
    duration: float

    # Computed fields
    speaker_turns: Dict[str, List[int]] = field(default_factory=dict)  # speaker -> segment indices
    speaker_word_counts: Dict[str, int] = field(default_factory=dict)
    interaction_patterns: Dict[Tuple[str, str], int] = field(default_factory=dict)  # (speaker_a, speaker_b) -> count

    def __post_init__(self):
        """Compute conversation-level features"""
        self._compute_speaker_turns()
        self._compute_interaction_patterns()

    def _compute_speaker_turns(self):
        """Analyze speaker turn-taking patterns"""
        for idx, segment in enumerate(self.segments):
            speaker = segment.get('speaker')
            if speaker:
                if speaker not in self.speaker_turns:
                    self.speaker_turns[speaker] = []
                self.speaker_turns[speaker].append(idx)

                # Count words
                text = segment.get('text', '')
                word_count = len(text.split())
                self.speaker_word_counts[speaker] = self.speaker_word_counts.get(speaker, 0) + word_count

    def _compute_interaction_patterns(self):
        """Analyze who talks to whom (useful for vocative detection)"""
        prev_speaker = None
        for segment in self.segments:
            curr_speaker = segment.get('speaker')
            if prev_speaker and curr_speaker and prev_speaker != curr_speaker:
                pair = tuple(sorted([prev_speaker, curr_speaker]))
                self.interaction_patterns[pair] = self.interaction_patterns.get(pair, 0) + 1
            prev_speaker = curr_speaker

    def get_speaker_context_window(self, segment_index: int, window_size: int = 3) -> List[Dict[str, Any]]:
        """Get surrounding segments for context analysis"""
        start = max(0, segment_index - window_size)
        end = min(len(self.segments), segment_index + window_size + 1)
        return self.segments[start:end]


class NameExtractionStrategy(ABC):
    """Abstract base for name extraction strategies (Strategy Pattern)"""

    @abstractmethod
    async def extract(self, context: ConversationContext) -> List[NameEvidence]:
        """Extract name evidence from conversation context"""
        pass


class SpacyNERExtractor(NameExtractionStrategy):
    """
    Extract names using spaCy's NER with linguistic understanding.

    Advantages over regex:
    - Understands POS tags (PROPN vs PRON)
    - Built-in entity recognition
    - Context-aware (not just pattern matching)
    - No manual stopword lists needed
    """

    def __init__(self):
        self.nlp = None
        self._initialized = False

        # Dependency labels used for grammatical role detection
        self._subject_deps = {"nsubj", "nsubjpass"}
        self._object_deps = {"dobj", "obj", "iobj", "dative", "pobj", "obl"}
        self._complement_deps = {"attr", "oprd", "acomp", "appos"}

    async def _initialize(self):
        """Lazy-load spaCy model"""
        if self._initialized:
            return

        try:
            import spacy
            # Use small model for speed (12MB, fast on CPU)
            self.nlp = spacy.load("en_core_web_sm")
            self._initialized = True
            logger.info("Initialized spaCy NER extractor with en_core_web_sm")
        except Exception as e:
            logger.warning(f"Failed to load spaCy model: {e}. Name extraction will use fallback methods.")
            self.nlp = None

    async def extract(self, context: ConversationContext) -> List[NameEvidence]:
        """Extract PERSON entities using spaCy NER"""
        await self._initialize()

        if not self.nlp:
            return []

        evidence_list = []

        for idx, segment in enumerate(context.segments):
            text = segment.get('text', '')
            speaker = segment.get('speaker')
            start_time = segment.get('start', 0.0)

            if not text.strip():
                continue

            # Process with spaCy
            doc = self.nlp(text)

            # Extract PERSON entities
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    logger.debug(f"spaCy found PERSON: '{ent.text}' in segment {idx}: {text[:50]}")

                    normalized_name = self._normalize_entity_text(ent)
                    if not normalized_name:
                        continue
                    if normalized_name.lower() not in text.lower():
                        continue

                    # Determine context type using linguistic analysis
                    context_type = self._classify_context(ent, doc, text)

                    # Confidence based on NER confidence and context clarity
                    confidence = self._compute_confidence(ent, context_type)

                    logger.debug(f"  -> Context: {context_type.value}, Confidence: {confidence:.2f}")

                    evidence = NameEvidence(
                        name=normalized_name,
                        context_type=context_type,
                        speaker_id=speaker,
                        segment_index=idx,
                        text_snippet=text[:100],
                        confidence=confidence,
                        timestamp=start_time,
                        linguistic_features={
                            'pos_tags': [token.pos_ for token in ent],
                            'dep_tags': [token.dep_ for token in ent],
                            'entity_label': ent.label_,
                            'entity_kb_id': ent.kb_id_,
                            'raw_text': ent.text
                        }
                    )
                    evidence_list.append(evidence)

        logger.info(f"spaCy NER extracted {len(evidence_list)} name instances")
        return evidence_list

    def _classify_context(self, entity, doc, text: str) -> NameContextType:
        """
        Classify how the name is being used (vocative vs self-ID vs mention).

        Uses linguistic features:
        - Dependency parsing (vocative has distinct dep pattern)
        - Surrounding tokens (pronouns, verbs)
        - Punctuation patterns
        """
        ent_tokens = list(entity)
        if not ent_tokens:
            return NameContextType.UNKNOWN

        # Use entity root for dependency checks (e.g., last token in "Detective Molly")
        root_token = entity.root

        # Check for self-identification patterns
        # "I'm John", "My name is John", "Call me John"
        if self._is_self_identification(root_token, doc):
            return NameContextType.SELF_IDENTIFICATION

        # Check for vocative (direct address)
        # Linguistic markers: greeting word, punctuation, vocative dep tag
        if self._is_vocative_usage(root_token, doc, text):
            return NameContextType.VOCATIVE

        # Check for possessive
        if any(token.dep_ == 'poss' for token in ent_tokens):
            return NameContextType.POSSESSIVE

        # Default to mention
        return NameContextType.MENTION

    def _is_self_identification(self, entity_root, doc) -> bool:
        """Heuristics to detect when a speaker is identifying themselves."""
        if entity_root.dep_ not in self._complement_deps and entity_root.head.dep_ != "ROOT":
            # Require the entity to function as a predicate/complement in the clause
            return False

        verb_candidates = []
        head = entity_root.head

        if head is not None:
            verb_candidates.append(head)
            # Sometimes the root's head is another verb (e.g., compound predicates)
            if head.head is not head and head.head is not None:
                verb_candidates.append(head.head)

        for verb in verb_candidates:
            if verb is None:
                continue

            if self._has_first_person_subject(verb):
                return True

            if self._has_first_person_object(verb):
                return True

        # Fallback: look for pattern like "I am <entity>"
        # Fallback: check for auxiliary copula linking entity and first-person pronoun
        for token in doc[entity_root.i : entity_root.i + 3]:
            if token.dep_ == "cop" and self._has_first_person_subject(token.head):
                return True

        return False

    def _has_first_person_subject(self, verb_token) -> bool:
        """Check if a verb has a first-person subject or possessed subject."""
        for child in verb_token.children:
            if child.dep_ not in self._subject_deps:
                continue

            if self._is_first_person(child):
                return True

            # Handle "My name is John" -> subject "name" with poss "my"
            if any(grandchild.dep_ == "poss" and self._is_first_person(grandchild) for grandchild in child.children):
                return True

        return False

    def _has_first_person_object(self, verb_token) -> bool:
        """Check if a verb like 'call' has a first-person object (e.g., 'Call me John')."""
        for child in verb_token.children:
            if child.dep_ not in self._object_deps:
                continue

            if self._is_first_person(child):
                return True

            # Handle pronouns inside prepositional objects
            if any(self._is_first_person(grandchild) for grandchild in child.children):
                return True

        return False

    def _is_first_person(self, token) -> bool:
        """Determine whether a token refers to the first person using morphological features."""
        persons = token.morph.get("Person")
        return bool(persons and "1" in persons)

    def _is_vocative_usage(self, entity_root, doc, text: str) -> bool:
        """Detect if the name is being used to address someone (vocative)."""
        if entity_root.dep_ == "vocative":
            return True

        # Check for interjection or discourse markers immediately before the entity
        if entity_root.i > 0:
            prev_token = doc[entity_root.i - 1]
            if prev_token.pos_ == "INTJ" or prev_token.dep_ == "discourse":
                return True

        # Entity governed by an interjection/root can signal direct address
        if entity_root.head.pos_ == "INTJ" or entity_root.head.dep_ == "discourse":
            return True

        # Check for punctuation like commas or exclamations immediately after the entity
        next_tokens = doc[entity_root.i + 1:entity_root.i + 3]
        if any(token.text in {",", "!", "?"} for token in next_tokens):
            return True

        return False

    def _normalize_entity_text(self, entity) -> str:
        """
        Clean up entity text by removing trailing verbs/adverbs and retaining proper nouns.

        Prevents cases like "Vincent happens" from being treated as the full name.
        """
        tokens = [token for token in entity if token.text.strip()]
        if not tokens:
            return entity.text.strip()

        filtered_tokens = []
        for token in tokens:
            if token.pos_ in {"PROPN", "NOUN"} or token.text[:1].isupper():
                filtered_tokens.append(token.text)

        if not filtered_tokens:
            filtered_tokens = [tokens[0].text]

        return " ".join(filtered_tokens).strip()

    def _compute_confidence(self, entity, context_type: NameContextType) -> float:
        """Compute confidence score based on entity and context"""
        base_confidence = 0.7  # spaCy PERSON entities are generally reliable

        # Adjust based on context type certainty
        context_boost = {
            NameContextType.SELF_IDENTIFICATION: 0.2,  # High confidence
            NameContextType.VOCATIVE: 0.1,
            NameContextType.POSSESSIVE: 0.05,
            NameContextType.MENTION: 0.0,
            NameContextType.UNKNOWN: -0.1
        }

        confidence = base_confidence + context_boost.get(context_type, 0.0)
        return max(0.0, min(1.0, confidence))


class PatternBasedExtractor(NameExtractionStrategy):
    """
    Fallback pattern-based extractor for when spaCy is unavailable.

    Uses regex patterns but with improved context classification.
    """

    # Comprehensive stopword set for filtering
    STOPWORDS = {
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'my', 'your', 'his', 'hers', 'its', 'our', 'their', 'mine', 'yours', 'ours', 'theirs',
        'this', 'that', 'these', 'those',
        'what', 'when', 'where', 'which', 'who', 'whom', 'whose', 'why', 'how',
        'okay', 'yeah', 'sure', 'right', 'well', 'oh', 'um', 'uh', 'like', 'just',
        'very', 'really', 'actually', 'basically', 'literally', 'definitely', 'probably',
        'can', 'could', 'will', 'would', 'should', 'shall', 'may', 'might', 'must',
        'do', 'does', 'did', 'have', 'has', 'had', 'is', 'are', 'was', 'were', 'been', 'being',
        'so', 'but', 'and', 'or', 'if', 'then', 'because', 'since', 'unless', 'until', 'while',
        'for', 'to', 'from', 'with', 'about', 'as', 'at', 'by', 'in', 'of', 'on', 'off', 'out',
        'there', 'here', 'now', 'then', 'yes', 'no', 'not',
        'know', 'think', 'mean', 'see', 'get', 'go', 'come', 'want', 'need', 'try', 'make', 'take'
    }

    async def extract(self, context: ConversationContext) -> List[NameEvidence]:
        """Extract names using pattern matching with context classification"""
        evidence_list = []

        # ULTRA-CONSERVATIVE patterns to avoid false positives
        # Only match when there's STRONG evidence of a name (proper name context)
        patterns = {
            # Only "My name is X" and "Call me X" (strongest indicators)
            'self_id': r'\b(?:my name is|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
            # Greeting with name ONLY if it's not sentence-initial
            'greeting': r'(?<!^)\b(?:hi|hello|hey)\s+([A-Z][a-z]+)\b',
            # Vocative removed entirely - too error prone
            # Possessive removed - not reliable
        }

        for idx, segment in enumerate(context.segments):
            text = segment.get('text', '')
            speaker = segment.get('speaker')
            start_time = segment.get('start', 0.0)

            for pattern_name, pattern in patterns.items():
                matches = re.finditer(pattern, text, re.IGNORECASE)

                for match in matches:
                    name = match.group(1)

                    # Filter stopwords
                    if name.lower() in self.STOPWORDS or len(name) <= 1:
                        continue

                    # Map pattern to context type
                    context_type = self._pattern_to_context_type(pattern_name, text, match)

                    evidence = NameEvidence(
                        name=name,
                        context_type=context_type,
                        speaker_id=speaker,
                        segment_index=idx,
                        text_snippet=text[:100],
                        confidence=0.6,  # Lower than spaCy
                        timestamp=start_time
                    )
                    evidence_list.append(evidence)

        logger.info(f"Pattern extractor found {len(evidence_list)} name instances")
        return evidence_list

    def _pattern_to_context_type(self, pattern_name: str, text: str, match) -> NameContextType:
        """Map pattern name to context type"""
        mapping = {
            'self_id': NameContextType.SELF_IDENTIFICATION,
            'greeting': NameContextType.VOCATIVE,  # "Hi John" is addressing
            'vocative': NameContextType.VOCATIVE,
            'possessive': NameContextType.POSSESSIVE,
        }
        return mapping.get(pattern_name, NameContextType.UNKNOWN)


class FilenameExtractor(NameExtractionStrategy):
    """Extract potential names from audio/video filename"""

    async def extract(self, context: ConversationContext) -> List[NameEvidence]:
        """Extract names from filename"""
        if not context.filename:
            return []

        evidence_list = []

        # Clean filename
        filename_clean = re.sub(r'\.(mp3|wav|m4a|mp4|avi|mov|mkv)$', '', context.filename.lower())
        parts = re.split(r'[_\-\s\.]+', filename_clean)

        # Common non-name words in filenames
        skip_words = {'conversation', 'interview', 'call', 'meeting', 'recording',
                     'audio', 'video', 'transcript', 'session', 'deposition'}

        for part in parts:
            if len(part) > 2 and part not in skip_words:
                name = part.capitalize()
                evidence = NameEvidence(
                    name=name,
                    context_type=NameContextType.FILENAME,
                    speaker_id=None,  # Unknown which speaker
                    segment_index=-1,
                    text_snippet=f"filename: {context.filename}",
                    confidence=0.4,  # Lower confidence from filename
                    timestamp=0.0
                )
                evidence_list.append(evidence)

        logger.info(f"Filename extractor found {len(evidence_list)} potential names")
        return evidence_list


class EvidenceAggregator:
    """
    Aggregates name evidence across the full conversation to infer speaker identities.

    Uses holistic analysis:
    - Self-ID statements strongly indicate speaker identity
    - Vocative patterns suggest who's being addressed (useful for narrowing)
    - Frequency and temporal distribution of names
    - Speaker turn patterns and interaction analysis
    """

    def aggregate(
        self,
        all_evidence: List[NameEvidence],
        context: ConversationContext
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate evidence to produce speaker -> name mappings with confidence.

        Returns:
            Dict mapping speaker_id to {name, confidence, evidence_count, reasoning}
        """
        # Group evidence by speaker
        speaker_evidence: Dict[str, List[NameEvidence]] = defaultdict(list)

        for evidence in all_evidence:
            if evidence.speaker_id:
                speaker_evidence[evidence.speaker_id].append(evidence)

        speaker_names = {}

        for speaker_id, evidence_list in speaker_evidence.items():
            name_result = self._infer_name_for_speaker(speaker_id, evidence_list, context)
            if name_result:
                speaker_names[speaker_id] = name_result

        return speaker_names

    def _infer_name_for_speaker(
        self,
        speaker_id: str,
        evidence_list: List[NameEvidence],
        context: ConversationContext
    ) -> Optional[Dict[str, Any]]:
        """Infer the most likely name for a speaker from evidence"""

        if not evidence_list:
            return None

        # Score each unique name
        name_scores: Dict[str, float] = defaultdict(float)
        name_evidence_counts: Dict[str, int] = defaultdict(int)

        for evidence in evidence_list:
            weight = self._compute_evidence_weight(evidence)
            weight = min(1.0, max(0.0, weight))
            current = name_scores[evidence.name]
            name_scores[evidence.name] = current + weight * (1.0 - current)
            name_evidence_counts[evidence.name] += 1

        if not name_scores:
            return None

        # Get top name
        best_name = max(name_scores, key=name_scores.get)
        total_score = name_scores[best_name]
        evidence_count = name_evidence_counts[best_name]

        matching_evidence = [ev for ev in evidence_list if ev.name == best_name]
        context_counts = Counter(ev.context_type for ev in matching_evidence)

        confidence = total_score
        if context_counts.get(NameContextType.SELF_IDENTIFICATION, 0) == 0:
            # Without a self-ID we require multiple reinforcing signals
            if context_counts.get(NameContextType.VOCATIVE, 0) == 0:
                if evidence_count <= 1 or confidence < 0.6:
                    return None
                confidence = min(confidence, 0.45)
            else:
                confidence = min(confidence, 0.55)

        confidence = max(0.0, min(1.0, confidence))

        if confidence < 0.3:
            return None

        return {
            'name': best_name,
            'confidence': confidence,
            'evidence_count': evidence_count,
            'total_score': total_score,
            'reasoning': self._generate_reasoning(best_name, evidence_list)
        }

    def _compute_evidence_weight(self, evidence: NameEvidence) -> float:
        """Compute weight for a piece of evidence"""
        base_weight = evidence.confidence

        # Strong boost for self-identification
        if evidence.context_type == NameContextType.SELF_IDENTIFICATION:
            return base_weight * 3.0

        # Moderate boost for filename
        elif evidence.context_type == NameContextType.FILENAME:
            return 0.0  # filenames are hints but should not drive identity

        # Small boost for possessive (indirect indicator)
        elif evidence.context_type == NameContextType.POSSESSIVE:
            return base_weight * 0.8

        # Penalize vocative (name is being addressed, not speaking)
        elif evidence.context_type == NameContextType.VOCATIVE:
            return base_weight * 0.3

        return base_weight

    def _generate_reasoning(self, name: str, evidence_list: List[NameEvidence]) -> str:
        """Generate human-readable reasoning for the inference"""
        context_counts = Counter(e.context_type for e in evidence_list if e.name == name)

        reasons = []
        if context_counts.get(NameContextType.SELF_IDENTIFICATION, 0) > 0:
            reasons.append(f"{context_counts[NameContextType.SELF_IDENTIFICATION]} self-identification(s)")
        if context_counts.get(NameContextType.FILENAME, 0) > 0:
            reasons.append("mentioned in filename")
        if context_counts.get(NameContextType.POSSESSIVE, 0) > 0:
            reasons.append(f"{context_counts[NameContextType.POSSESSIVE]} possessive reference(s)")

        return ", ".join(reasons) if reasons else "pattern matching"


class SpeakerIdentificationPipeline:
    """
    Main orchestrator for speaker name identification.

    Follows SOLID principles:
    - Single Responsibility: Each extractor handles one method
    - Open/Closed: Easy to add new extractors without modifying existing code
    - Dependency Inversion: Depends on NameExtractionStrategy abstraction

    Processing flow:
    1. Build full conversation context
    2. Run all extractors concurrently
    3. Aggregate evidence with confidence scoring
    4. Return speaker -> name mappings
    """

    def __init__(self, use_spacy: bool = True, use_patterns: bool = False, use_filename: bool = False):
        """
        Initialize pipeline with extractors.

        Args:
            use_spacy: Whether to use spaCy NER (recommended)
        """
        self.extractors: List[NameExtractionStrategy] = []

        if use_spacy:
            self.extractors.append(SpacyNERExtractor())
        if use_patterns:
            self.extractors.append(PatternBasedExtractor())
        if use_filename:
            self.extractors.append(FilenameExtractor())

        self.aggregator = EvidenceAggregator()

    async def identify_speakers(
        self,
        segments: List[Dict[str, Any]],
        speakers: List[str],
        filename: Optional[str] = None,
        duration: float = 0.0
    ) -> Dict[str, Dict[str, Any]]:
        """
        Identify speaker names from full conversation.

        Args:
            segments: Full list of transcription segments
            speakers: List of unique speaker IDs
            filename: Optional audio/video filename
            duration: Total conversation duration

        Returns:
            Dict mapping speaker_id to {name, confidence, evidence_count, reasoning}
        """
        # Build full conversation context
        context = ConversationContext(
            segments=segments,
            speakers=speakers,
            filename=filename,
            duration=duration
        )

        logger.info(
            f"Starting speaker identification: {len(segments)} segments, "
            f"{len(speakers)} speakers, {len(self.extractors)} extractors"
        )

        # Run all extractors concurrently
        extraction_tasks = [extractor.extract(context) for extractor in self.extractors]
        evidence_lists = await asyncio.gather(*extraction_tasks, return_exceptions=True)

        # Flatten evidence (handle exceptions)
        all_evidence = []
        for evidence in evidence_lists:
            if isinstance(evidence, Exception):
                logger.error(f"Extractor failed: {evidence}")
            elif evidence:
                all_evidence.extend(evidence)

        logger.info(f"Collected {len(all_evidence)} pieces of name evidence")

        # Aggregate evidence to infer names
        speaker_names = self.aggregator.aggregate(all_evidence, context)

        logger.info(f"Identified names for {len(speaker_names)}/{len(speakers)} speakers")

        return speaker_names


# Convenience function for backward compatibility
async def identify_speaker_names(
    segments: List[Dict[str, Any]],
    speakers: List[str],
    filename: Optional[str] = None,
    duration: float = 0.0
) -> Dict[str, Dict[str, Any]]:
    """
    Identify speaker names from transcription segments.

    This is the main entry point for the speaker identification system.
    """
    pipeline = SpeakerIdentificationPipeline(use_spacy=True)
    return await pipeline.identify_speakers(segments, speakers, filename, duration)
