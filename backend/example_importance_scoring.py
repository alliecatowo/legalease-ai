#!/usr/bin/env python3
"""
Example usage of the ImportanceScorer service.

Demonstrates scoring for different types of discovery items:
- Photos with detected objects and scenes
- Videos with multiple frames
- Social media posts with keywords
- Emails with relevant content
- Call logs with temporal relevance
"""

from datetime import datetime, timedelta
from app.services.importance_scoring_service import ImportanceScorer


def main():
    # Initialize the scorer
    scorer = ImportanceScorer()

    print("=" * 80)
    print("IMPORTANCE SCORING SERVICE - EXAMPLES")
    print("=" * 80)
    print()

    # Example 1: Photo with weapon and money
    print("Example 1: Photo Evidence - Weapon and Cash")
    print("-" * 80)
    photo_score = scorer.calculate_photo_importance(
        detected_objects=["gun", "money", "car", "phone"],
        detected_scenes=["parking lot", "nighttime"],
        detected_activities=["transaction"],
        sensitive_flags={"weapons": True},
        metadata={"has_location": True, "has_timestamp": True}
    )
    print(f"Score: {photo_score:.3f}")

    explanation = scorer.explain_score(
        item_type="photo",
        score=photo_score,
        features={
            "detected_objects": ["gun", "money", "car", "phone"],
            "detected_activities": ["transaction"],
            "sensitive_flags": {"weapons": True}
        }
    )
    print(f"Summary: {explanation['summary']}")
    print("\nBreakdown:")
    for item in explanation['breakdown']:
        print(f"  - {item['factor']}: {item['items']} (contribution: {item['contribution']:.3f})")
    print()

    # Example 2: Social Media Post - Threatening Language
    print("Example 2: Social Media Post - Threatening Content")
    print("-" * 80)
    incident_date = datetime(2024, 3, 15, 23, 0)
    post_date = datetime(2024, 3, 15, 22, 30)  # 30 minutes before incident

    social_score = scorer.calculate_social_post_importance(
        post_text="Meet me at the spot at 11pm. Bring the money or there will be problems. "
                  "Don't make me do something we'll both regret.",
        platform="snapchat",
        engagement_metrics={"views": 50, "likes": 5},
        post_timestamp=post_date,
        incident_date=incident_date,
        author="suspect123",
        known_persons=["suspect123", "victim456"]
    )
    print(f"Score: {social_score:.3f}")

    explanation = scorer.explain_score(
        item_type="social_post",
        score=social_score,
        features={
            "post_text": "Meet me at the spot at 11pm. Bring the money or there will be problems."
        }
    )
    print(f"Summary: {explanation['summary']}")
    print("\nBreakdown:")
    for item in explanation['breakdown']:
        print(f"  - {item['factor']}: {item['items']} (contribution: {item['contribution']:.3f})")
    print()

    # Example 3: Email - Legal Discussion
    print("Example 3: Email - Lawsuit Discussion")
    print("-" * 80)
    email_date = datetime(2024, 3, 14, 10, 0)

    email_score = scorer.calculate_email_importance(
        subject="RE: Settlement Discussion - Urgent",
        body_text="We need to discuss the lawsuit before the court date. "
                  "The attorney mentioned possible fraud charges. "
                  "Can we meet to go over the documents?",
        sender="john.doe@example.com",
        recipients=["jane.smith@example.com", "lawyer@lawfirm.com"],
        timestamp=email_date,
        incident_date=incident_date,
        has_attachments=True,
        known_persons=["john.doe", "jane.smith"]
    )
    print(f"Score: {email_score:.3f}")

    explanation = scorer.explain_score(
        item_type="email",
        score=email_score,
        features={
            "body_text": "lawsuit court fraud attorney documents"
        }
    )
    print(f"Summary: {explanation['summary']}")
    print("\nBreakdown:")
    for item in explanation['breakdown']:
        print(f"  - {item['factor']}: {item['items']} (contribution: {item['contribution']:.3f})")
    print()

    # Example 4: Call Log - Late Night Calls
    print("Example 4: Call Log - Suspicious Timing")
    print("-" * 80)
    call_date = datetime(2024, 3, 15, 23, 45)  # 11:45 PM on incident day

    call_score = scorer.calculate_call_importance(
        caller="+1-555-0123",
        recipient="+1-555-0456",
        duration=420,  # 7 minutes
        timestamp=call_date,
        incident_date=incident_date,
        call_type="OUTGOING",
        known_persons=["+1-555-0123"],
        call_frequency=15  # 15 calls between these numbers
    )
    print(f"Score: {call_score:.3f}")
    print(f"Summary: Call on incident day, late night (11:45 PM), 7 minute duration")
    print(f"Additional factors: Frequent caller (15 calls), known person of interest")
    print()

    # Example 5: Video with Multiple Concerning Frames
    print("Example 5: Video - Altercation Captured")
    print("-" * 80)
    video_frames = [
        {
            "detected_objects": ["person", "person", "car"],
            "detected_activities": ["meeting"],
            "sensitive_flags": {}
        },
        {
            "detected_objects": ["person", "person", "weapon"],
            "detected_activities": ["altercation"],
            "sensitive_flags": {"violence": True, "weapons": True}
        },
        {
            "detected_objects": ["person", "blood", "phone"],
            "detected_activities": ["fleeing"],
            "sensitive_flags": {"violence": True, "gore": True}
        }
    ]

    video_score = scorer.calculate_video_importance(
        video_summary="Security camera footage showing two individuals meeting in parking lot. "
                    "Altercation escalates with weapon visible. One person flees the scene.",
        visual_contents=video_frames,
        metadata={"duration": 180, "has_audio": True, "has_location": True}
    )
    print(f"Score: {video_score:.3f}")
    print(f"Summary: 3-minute video capturing escalating altercation")
    print(f"Key frames: Meeting -> Weapon displayed -> Violence -> Fleeing")
    print()

    # Example 6: Low Importance Item
    print("Example 6: Low Importance - Routine Photo")
    print("-" * 80)
    routine_score = scorer.calculate_photo_importance(
        detected_objects=["person", "table", "chair"],
        detected_scenes=["indoor"],
        detected_activities=["sitting"],
        sensitive_flags={},
        metadata={}
    )
    print(f"Score: {routine_score:.3f}")
    print(f"Summary: Routine indoor photo with no concerning elements")
    print()

    # Demonstrate custom rules
    print("=" * 80)
    print("CUSTOM RULES EXAMPLE")
    print("=" * 80)
    print()

    # Create scorer with custom rules for specific case
    custom_rules = {
        "keywords": {
            "specific_location": 0.5,  # Case-specific location
            "specific_person_name": 0.4,  # Person of interest
        },
        "objects": {
            "red_car": 0.4,  # Suspect vehicle color
        }
    }

    custom_scorer = ImportanceScorer()
    custom_scorer.update_rules(custom_rules)

    custom_post_score = custom_scorer.calculate_social_post_importance(
        post_text="Saw John at specific_location yesterday with the red_car"
    )
    print(f"Custom scoring for case-specific keywords: {custom_post_score:.3f}")
    print()

    print("=" * 80)
    print("SCORING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
