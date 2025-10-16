"""
Importance Scoring Service

Machine learning-based importance scoring for discovery items in legal cases.
Scores items from 0.0-1.0 based on relevance to legal proceedings using
rule-based scoring with configurable rules. Extensible for ML models.

Features:
- Rule-based scoring for photos, videos, social media, emails, and call logs
- Configurable scoring rules for different content types
- Explainable scoring with detailed breakdowns
- Fast execution without heavy ML inference
- Extensible architecture for future ML model integration

Usage:
    ```python
    from app.services.importance_scoring_service import ImportanceScorer

    scorer = ImportanceScorer()

    # Score a photo
    photo_score = scorer.calculate_photo_importance(
        detected_objects=["weapon", "money", "car"],
        detected_scenes=["crime_scene"],
        detected_activities=["transaction"],
        sensitive_flags={"violence": True, "weapons": True},
        metadata={"has_location": True, "has_timestamp": True}
    )

    # Score a social media post
    social_score = scorer.calculate_social_post_importance(
        post_text="Meeting at 10pm with the cash",
        platform="snapchat",
        engagement_metrics={"views": 1000, "likes": 50},
        post_timestamp=datetime(2024, 3, 15, 22, 0),
        incident_date=datetime(2024, 3, 15)
    )

    # Get explanation for score
    explanation = scorer.explain_score(features, score)
    ```
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import re

logger = logging.getLogger(__name__)


# Default scoring rules configuration
DEFAULT_SCORING_RULES = {
    "objects": {
        # Weapons - highest priority
        "weapon": 0.4,
        "gun": 0.5,
        "firearm": 0.5,
        "rifle": 0.5,
        "pistol": 0.5,
        "knife": 0.4,
        "blade": 0.4,
        "ammunition": 0.4,
        "bullet": 0.4,

        # Drugs and paraphernalia
        "drugs": 0.4,
        "narcotics": 0.4,
        "pills": 0.3,
        "marijuana": 0.4,
        "cocaine": 0.5,
        "heroin": 0.5,
        "methamphetamine": 0.5,
        "syringe": 0.3,
        "pipe": 0.2,
        "bong": 0.3,

        # Money and valuables
        "money": 0.3,
        "cash": 0.3,
        "currency": 0.3,
        "bills": 0.3,
        "jewelry": 0.2,
        "gold": 0.2,
        "diamonds": 0.2,

        # Documents and evidence
        "document": 0.2,
        "contract": 0.3,
        "receipt": 0.2,
        "invoice": 0.2,
        "letter": 0.2,
        "note": 0.2,
        "id card": 0.2,
        "license": 0.2,
        "passport": 0.2,

        # Technology
        "phone": 0.1,
        "computer": 0.1,
        "laptop": 0.1,
        "tablet": 0.1,
        "camera": 0.1,

        # Vehicles
        "car": 0.1,
        "vehicle": 0.1,
        "motorcycle": 0.1,
        "truck": 0.1,
        "van": 0.1,

        # Other relevant objects
        "license plate": 0.2,
        "blood": 0.4,
        "injury": 0.3,
        "damage": 0.2,
    },

    "scenes": {
        "crime scene": 0.3,
        "accident": 0.3,
        "surveillance": 0.2,
        "parking lot": 0.1,
        "street": 0.1,
        "indoor": 0.05,
        "outdoor": 0.05,
        "nighttime": 0.1,
        "store": 0.1,
        "bank": 0.2,
        "atm": 0.2,
    },

    "activities": {
        "fighting": 0.4,
        "altercation": 0.4,
        "assault": 0.5,
        "violence": 0.5,
        "transaction": 0.3,
        "exchange": 0.3,
        "handoff": 0.3,
        "meeting": 0.2,
        "driving": 0.1,
        "running": 0.2,
        "fleeing": 0.3,
        "hiding": 0.2,
        "smoking": 0.1,
        "drinking": 0.1,
    },

    "sensitive_flags": {
        "violence": 0.4,
        "weapons": 0.4,
        "explicit": 0.2,
        "drugs": 0.4,
        "gore": 0.3,
        "injury": 0.3,
    },

    "keywords": {
        # Threats and violence
        "threat": 0.4,
        "threaten": 0.4,
        "kill": 0.5,
        "murder": 0.5,
        "assault": 0.4,
        "attack": 0.4,
        "fight": 0.3,
        "hurt": 0.3,
        "harm": 0.3,
        "beat": 0.3,

        # Weapons
        "weapon": 0.4,
        "gun": 0.4,
        "knife": 0.4,
        "shoot": 0.4,
        "stab": 0.4,

        # Drugs
        "drugs": 0.3,
        "weed": 0.3,
        "marijuana": 0.3,
        "cocaine": 0.4,
        "heroin": 0.4,
        "meth": 0.4,
        "pills": 0.2,
        "deal": 0.3,
        "dealer": 0.3,

        # Money and crime
        "money": 0.2,
        "cash": 0.2,
        "payment": 0.2,
        "pay": 0.1,
        "steal": 0.3,
        "rob": 0.4,
        "robbery": 0.4,
        "theft": 0.3,
        "fraud": 0.3,

        # Legal terms
        "lawsuit": 0.3,
        "sue": 0.3,
        "lawyer": 0.2,
        "attorney": 0.2,
        "court": 0.2,
        "police": 0.2,
        "cop": 0.2,
        "arrest": 0.3,

        # Conspiracy and planning
        "plan": 0.2,
        "meet": 0.1,
        "meeting": 0.1,
        "conspiracy": 0.4,
        "scheme": 0.3,
        "plot": 0.3,
    }
}


class ImportanceScorer:
    """
    Importance scoring engine for discovery items.

    Provides rule-based scoring for different types of discovery items
    (photos, videos, social media, emails, call logs) with configurable
    rules and explainable results.

    Attributes:
        rules: Dictionary of scoring rules for different content types
    """

    def __init__(self, rules: Optional[Dict] = None):
        """
        Initialize the importance scorer.

        Args:
            rules: Custom scoring rules (uses DEFAULT_SCORING_RULES if None)
        """
        self.rules = rules or DEFAULT_SCORING_RULES
        logger.info("ImportanceScorer initialized")

    def normalize_score(self, score: float) -> float:
        """
        Normalize score to 0.0-1.0 range.

        Args:
            score: Raw score value

        Returns:
            Normalized score clamped to [0.0, 1.0]
        """
        return max(0.0, min(1.0, score))

    def apply_rules(
        self,
        items: List[str],
        rule_dict: Dict[str, float],
        case_sensitive: bool = False
    ) -> Dict[str, float]:
        """
        Apply scoring rules to a list of items.

        Args:
            items: List of items to score (objects, keywords, etc.)
            rule_dict: Dictionary mapping items to scores
            case_sensitive: Whether to match case-sensitively

        Returns:
            Dictionary mapping matched items to their scores
        """
        matches = {}

        for item in items:
            item_key = item if case_sensitive else item.lower()

            # Check for exact match
            for rule_key, rule_score in rule_dict.items():
                rule_match_key = rule_key if case_sensitive else rule_key.lower()

                if item_key == rule_match_key or rule_match_key in item_key:
                    matches[item] = rule_score
                    break

        return matches

    def extract_keywords_from_text(self, text: str) -> List[str]:
        """
        Extract potential keywords from text.

        Args:
            text: Text to extract keywords from

        Returns:
            List of keywords found in text
        """
        if not text:
            return []

        text_lower = text.lower()
        found_keywords = []

        for keyword in self.rules["keywords"].keys():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found_keywords.append(keyword)

        return found_keywords

    def calculate_photo_importance(
        self,
        detected_objects: Optional[List[str]] = None,
        detected_scenes: Optional[List[str]] = None,
        detected_activities: Optional[List[str]] = None,
        sensitive_flags: Optional[Dict[str, bool]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate importance score for a photo.

        Args:
            detected_objects: List of detected objects
            detected_scenes: List of detected scenes
            detected_activities: List of detected activities
            sensitive_flags: Dictionary of sensitive content flags
            metadata: Additional metadata (has_text, has_location, etc.)

        Returns:
            Importance score (0.0-1.0)
        """
        score = 0.0

        # Score detected objects
        if detected_objects:
            object_matches = self.apply_rules(
                detected_objects,
                self.rules["objects"]
            )
            score += sum(object_matches.values())

        # Score detected scenes
        if detected_scenes:
            scene_matches = self.apply_rules(
                detected_scenes,
                self.rules["scenes"]
            )
            score += sum(scene_matches.values())

        # Score detected activities
        if detected_activities:
            activity_matches = self.apply_rules(
                detected_activities,
                self.rules["activities"]
            )
            score += sum(activity_matches.values())

        # Score sensitive flags
        if sensitive_flags:
            for flag, is_present in sensitive_flags.items():
                if is_present:
                    flag_score = self.rules["sensitive_flags"].get(flag.lower(), 0.0)
                    score += flag_score

        # Score metadata features
        if metadata:
            # Text presence in image (documents, signs, etc.)
            if metadata.get("has_text"):
                score += 0.2

            # Location metadata (geotagged)
            if metadata.get("has_location"):
                score += 0.1

            # Timestamp metadata
            if metadata.get("has_timestamp"):
                score += 0.05

        return self.normalize_score(score)

    def calculate_video_importance(
        self,
        video_summary: Optional[str] = None,
        visual_contents: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate importance score for a video.

        Aggregates scores from individual frames and video-level features.

        Args:
            video_summary: Text summary of video content
            visual_contents: List of visual content analyses for frames
            metadata: Video metadata (duration, has_audio, etc.)

        Returns:
            Importance score (0.0-1.0)
        """
        score = 0.0
        frame_count = 0

        # Aggregate frame-level scores
        if visual_contents:
            for frame in visual_contents:
                frame_score = self.calculate_photo_importance(
                    detected_objects=frame.get("detected_objects"),
                    detected_scenes=frame.get("detected_scenes"),
                    detected_activities=frame.get("detected_activities"),
                    sensitive_flags=frame.get("sensitive_flags"),
                    metadata=None  # Metadata handled at video level
                )
                score += frame_score
                frame_count += 1

            # Average frame scores
            if frame_count > 0:
                score = score / frame_count

        # Score video summary keywords
        if video_summary:
            keywords = self.extract_keywords_from_text(video_summary)
            keyword_matches = self.apply_rules(
                keywords,
                self.rules["keywords"]
            )
            # Add keyword bonus (up to 0.3)
            keyword_score = min(0.3, sum(keyword_matches.values()))
            score += keyword_score

        # Score metadata
        if metadata:
            # Long duration videos may be more important
            duration = metadata.get("duration", 0)
            if duration > 300:  # > 5 minutes
                score += 0.1

            # Audio presence
            if metadata.get("has_audio"):
                score += 0.05

            # Location metadata
            if metadata.get("has_location"):
                score += 0.1

        return self.normalize_score(score)

    def calculate_social_post_importance(
        self,
        post_text: Optional[str] = None,
        platform: Optional[str] = None,
        engagement_metrics: Optional[Dict[str, int]] = None,
        post_timestamp: Optional[datetime] = None,
        incident_date: Optional[datetime] = None,
        author: Optional[str] = None,
        known_persons: Optional[List[str]] = None
    ) -> float:
        """
        Calculate importance score for a social media post.

        Args:
            post_text: Text content of the post
            platform: Social media platform
            engagement_metrics: Dictionary with likes, shares, views, etc.
            post_timestamp: When the post was created
            incident_date: Date of relevant incident for temporal relevance
            author: Post author username
            known_persons: List of known persons of interest

        Returns:
            Importance score (0.0-1.0)
        """
        score = 0.0

        # Score keywords in text
        if post_text:
            keywords = self.extract_keywords_from_text(post_text)
            keyword_matches = self.apply_rules(
                keywords,
                self.rules["keywords"]
            )
            score += sum(keyword_matches.values())

        # Score engagement (high engagement may indicate importance)
        if engagement_metrics:
            total_engagement = sum(engagement_metrics.values())

            if total_engagement > 100:
                score += 0.1
            elif total_engagement > 1000:
                score += 0.2

        # Score temporal relevance
        if post_timestamp and incident_date:
            time_delta = abs((post_timestamp - incident_date).total_seconds())
            days_delta = time_delta / 86400  # Convert to days

            # Posts within 1 day of incident are highly relevant
            if days_delta <= 1:
                score += 0.3
            # Posts within 1 week are moderately relevant
            elif days_delta <= 7:
                score += 0.2
            # Posts within 1 month are somewhat relevant
            elif days_delta <= 30:
                score += 0.1

        # Score author relevance
        if author and known_persons:
            if author.lower() in [p.lower() for p in known_persons]:
                score += 0.2

        return self.normalize_score(score)

    def calculate_email_importance(
        self,
        subject: Optional[str] = None,
        body_text: Optional[str] = None,
        sender: Optional[str] = None,
        recipients: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None,
        incident_date: Optional[datetime] = None,
        has_attachments: bool = False,
        known_persons: Optional[List[str]] = None
    ) -> float:
        """
        Calculate importance score for an email.

        Args:
            subject: Email subject line
            body_text: Email body content
            sender: Sender email address
            recipients: List of recipient email addresses
            timestamp: When email was sent
            incident_date: Date of relevant incident
            has_attachments: Whether email has attachments
            known_persons: List of known persons of interest

        Returns:
            Importance score (0.0-1.0)
        """
        score = 0.0

        # Score keywords in subject
        if subject:
            subject_keywords = self.extract_keywords_from_text(subject)
            subject_matches = self.apply_rules(
                subject_keywords,
                self.rules["keywords"]
            )
            # Subject keywords get higher weight
            score += sum(subject_matches.values()) * 1.2

        # Score keywords in body
        if body_text:
            body_keywords = self.extract_keywords_from_text(body_text)
            body_matches = self.apply_rules(
                body_keywords,
                self.rules["keywords"]
            )
            score += sum(body_matches.values())

        # Score sender/recipient relevance
        if known_persons:
            all_parties = []
            if sender:
                all_parties.append(sender)
            if recipients:
                all_parties.extend(recipients)

            for party in all_parties:
                for person in known_persons:
                    if person.lower() in party.lower():
                        score += 0.15
                        break

        # Score attachments
        if has_attachments:
            score += 0.1

        # Score temporal relevance
        if timestamp and incident_date:
            time_delta = abs((timestamp - incident_date).total_seconds())
            days_delta = time_delta / 86400

            if days_delta <= 1:
                score += 0.3
            elif days_delta <= 7:
                score += 0.2
            elif days_delta <= 30:
                score += 0.1

        return self.normalize_score(score)

    def calculate_call_importance(
        self,
        caller: Optional[str] = None,
        recipient: Optional[str] = None,
        duration: int = 0,
        timestamp: Optional[datetime] = None,
        incident_date: Optional[datetime] = None,
        call_type: Optional[str] = None,
        known_persons: Optional[List[str]] = None,
        call_frequency: int = 1
    ) -> float:
        """
        Calculate importance score for a call log entry.

        Args:
            caller: Caller phone number or ID
            recipient: Recipient phone number or ID
            duration: Call duration in seconds
            timestamp: When call occurred
            incident_date: Date of relevant incident
            call_type: Type of call (INCOMING, OUTGOING, MISSED, VOICEMAIL)
            known_persons: List of known persons of interest
            call_frequency: Number of calls between these parties in timeframe

        Returns:
            Importance score (0.0-1.0)
        """
        score = 0.0

        # Score duration (longer calls may be more important)
        if duration > 300:  # > 5 minutes
            score += 0.1
        elif duration > 600:  # > 10 minutes
            score += 0.15
        elif duration > 1800:  # > 30 minutes
            score += 0.2

        # Score time of day (late night/early morning calls suspicious)
        if timestamp:
            hour = timestamp.hour
            if hour >= 22 or hour <= 5:  # 10 PM - 5 AM
                score += 0.1

        # Score temporal relevance to incident
        if timestamp and incident_date:
            time_delta = abs((timestamp - incident_date).total_seconds())
            days_delta = time_delta / 86400

            # Calls on same day as incident
            if days_delta <= 1:
                score += 0.3
            # Calls within 1 week
            elif days_delta <= 7:
                score += 0.2
            # Calls within 1 month
            elif days_delta <= 30:
                score += 0.1

        # Score party relevance
        if known_persons:
            all_parties = []
            if caller:
                all_parties.append(caller)
            if recipient:
                all_parties.append(recipient)

            for party in all_parties:
                for person in known_persons:
                    if person.lower() in party.lower():
                        score += 0.15
                        break

        # Score call frequency (frequent calls may indicate relationship)
        if call_frequency > 5:
            score += 0.1
        elif call_frequency > 10:
            score += 0.15
        elif call_frequency > 20:
            score += 0.2

        # Score missed calls (may indicate avoidance)
        if call_type == "MISSED":
            score += 0.05

        return self.normalize_score(score)

    def explain_score(
        self,
        item_type: str,
        score: float,
        features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate explanation for a given importance score.

        Args:
            item_type: Type of item (photo, video, social_post, email, call_log)
            score: Calculated importance score
            features: Dictionary of features used for scoring

        Returns:
            Dictionary with score breakdown and explanation
        """
        explanation = {
            "score": score,
            "item_type": item_type,
            "breakdown": [],
            "summary": ""
        }

        # Extract and explain contributing factors
        if item_type in ["photo", "video"]:
            if features.get("detected_objects"):
                matches = self.apply_rules(
                    features["detected_objects"],
                    self.rules["objects"]
                )
                if matches:
                    explanation["breakdown"].append({
                        "factor": "Detected Objects",
                        "items": list(matches.keys()),
                        "contribution": sum(matches.values())
                    })

            if features.get("detected_activities"):
                matches = self.apply_rules(
                    features["detected_activities"],
                    self.rules["activities"]
                )
                if matches:
                    explanation["breakdown"].append({
                        "factor": "Detected Activities",
                        "items": list(matches.keys()),
                        "contribution": sum(matches.values())
                    })

            if features.get("sensitive_flags"):
                active_flags = [k for k, v in features["sensitive_flags"].items() if v]
                if active_flags:
                    contribution = sum(
                        self.rules["sensitive_flags"].get(f.lower(), 0.0)
                        for f in active_flags
                    )
                    explanation["breakdown"].append({
                        "factor": "Sensitive Content Flags",
                        "items": active_flags,
                        "contribution": contribution
                    })

        if item_type in ["social_post", "email"]:
            text = features.get("post_text") or features.get("body_text", "")
            if text:
                keywords = self.extract_keywords_from_text(text)
                matches = self.apply_rules(keywords, self.rules["keywords"])
                if matches:
                    explanation["breakdown"].append({
                        "factor": "Keywords",
                        "items": list(matches.keys()),
                        "contribution": sum(matches.values())
                    })

        # Generate summary
        if score >= 0.7:
            explanation["summary"] = "High importance - Contains critical evidence or indicators"
        elif score >= 0.4:
            explanation["summary"] = "Moderate importance - Contains relevant information"
        elif score >= 0.2:
            explanation["summary"] = "Low importance - May have peripheral relevance"
        else:
            explanation["summary"] = "Minimal importance - Limited apparent relevance"

        return explanation

    def update_rules(self, new_rules: Dict[str, Any]) -> None:
        """
        Update scoring rules dynamically.

        Allows for case-specific rule customization.

        Args:
            new_rules: Dictionary of new or updated rules
        """
        for category, rules in new_rules.items():
            if category in self.rules:
                self.rules[category].update(rules)
            else:
                self.rules[category] = rules

        logger.info(f"Updated scoring rules for categories: {list(new_rules.keys())}")

    def get_rules(self) -> Dict[str, Any]:
        """
        Get current scoring rules.

        Returns:
            Dictionary of current scoring rules
        """
        return self.rules.copy()


# Singleton instance
_scorer_instance: Optional[ImportanceScorer] = None


def get_importance_scorer(rules: Optional[Dict] = None) -> ImportanceScorer:
    """
    Get or create singleton ImportanceScorer instance.

    Args:
        rules: Custom scoring rules (only used on first creation)

    Returns:
        ImportanceScorer singleton instance
    """
    global _scorer_instance

    if _scorer_instance is None:
        _scorer_instance = ImportanceScorer(rules=rules)
        logger.info("Created ImportanceScorer singleton")

    return _scorer_instance


def reset_importance_scorer() -> None:
    """
    Reset singleton instance (mainly for testing).
    """
    global _scorer_instance
    _scorer_instance = None
    logger.info("ImportanceScorer singleton reset")
