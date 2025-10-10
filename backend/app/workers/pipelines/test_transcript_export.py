"""
Test script for TranscriptExporter

Demonstrates how to use the TranscriptExporter to create professional
legal transcripts from transcription data.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.workers.pipelines.transcript_exporter import (
    TranscriptExporter,
    export_transcript,
)


def test_basic_export():
    """Test basic transcript export functionality."""
    print("Testing basic transcript export...")

    # Sample transcript data (as would come from WhisperX or other transcription)
    segments = [
        {
            "speaker_id": "1",
            "speaker_label": "Attorney Sarah Johnson",
            "speaker_role": "Plaintiff's Counsel",
            "text": "Good morning, Dr. Martinez. Thank you for being here today. Please state your full name and occupation for the record.",
            "start_time": 0.0,
            "end_time": 8.5,
            "confidence": 0.96,
        },
        {
            "speaker_id": "2",
            "speaker_label": "Dr. Carlos Martinez",
            "speaker_role": "Expert Witness",
            "speaker_affiliation": "Stanford Medical Center",
            "text": "Good morning. My name is Carlos Eduardo Martinez, M-A-R-T-I-N-E-Z. I am a board-certified orthopedic surgeon at Stanford Medical Center.",
            "start_time": 9.0,
            "end_time": 20.3,
            "confidence": 0.98,
        },
        {
            "speaker_id": "1",
            "speaker_label": "Attorney Sarah Johnson",
            "speaker_role": "Plaintiff's Counsel",
            "text": "Dr. Martinez, how long have you been practicing orthopedic surgery?",
            "start_time": 21.0,
            "end_time": 25.8,
            "confidence": 0.97,
        },
        {
            "speaker_id": "2",
            "speaker_label": "Dr. Carlos Martinez",
            "speaker_role": "Expert Witness",
            "speaker_affiliation": "Stanford Medical Center",
            "text": "I have been practicing for fifteen years. I completed my residency at Johns Hopkins in 2010 and have been at Stanford since 2012.",
            "start_time": 26.5,
            "end_time": 36.2,
            "confidence": 0.95,
        },
        {
            "speaker_id": "3",
            "speaker_label": "Attorney Michael Chen",
            "speaker_role": "Defense Counsel",
            "text": "Objection. Relevance.",
            "start_time": 37.0,
            "end_time": 39.1,
            "confidence": 0.99,
        },
        {
            "speaker_id": "4",
            "speaker_label": "Judge Rebecca Williams",
            "speaker_role": "Presiding Judge",
            "text": "Overruled. Please continue, Counsel.",
            "start_time": 40.0,
            "end_time": 43.5,
            "confidence": 0.98,
        },
        {
            "speaker_id": "1",
            "speaker_label": "Attorney Sarah Johnson",
            "speaker_role": "Plaintiff's Counsel",
            "text": "Thank you, Your Honor. Dr. Martinez, in your professional opinion, what are the standard practices for treating a complex fracture of the tibia?",
            "start_time": 44.0,
            "end_time": 53.7,
            "confidence": 0.94,
        },
        {
            "speaker_id": "2",
            "speaker_label": "Dr. Carlos Martinez",
            "speaker_role": "Expert Witness",
            "speaker_affiliation": "Stanford Medical Center",
            "text": "The standard of care requires immediate imaging, typically CT scans, followed by surgical stabilization within 24 to 48 hours to prevent complications such as compartment syndrome or infection.",
            "start_time": 54.5,
            "end_time": 69.8,
            "confidence": 0.93,
        },
    ]

    # Case metadata
    metadata = {
        "case_number": "2025-CV-45678",
        "case_name": "Anderson v. Metropolitan Hospital",
        "client": "Jennifer Anderson",
        "matter_type": "Medical Malpractice - Surgical Error",
        "document_name": "Expert_Deposition_Martinez_20250109.mp4",
        "date": "January 9, 2025",
        "location": "Law Offices of Johnson & Associates, San Francisco, CA",
        "witness": "Dr. Carlos Eduardo Martinez",
        "duration": 3600,  # 1 hour total
    }

    # Export the transcript
    output_path = "/tmp/legal_transcript_test.docx"
    success = export_transcript(
        segments=segments,
        metadata=metadata,
        output_path=output_path,
    )

    if success:
        print(f"✓ Transcript exported successfully to: {output_path}")
        print(f"  - {len(segments)} segments")
        print(f"  - {len(set(s['speaker_id'] for s in segments))} unique speakers")
        return True
    else:
        print("✗ Failed to export transcript")
        return False


def test_exporter_class():
    """Test using the TranscriptExporter class directly."""
    print("\nTesting TranscriptExporter class...")

    exporter = TranscriptExporter()

    # Simple deposition transcript
    segments = [
        {
            "speaker_id": "attorney",
            "speaker_label": "Attorney",
            "text": "Please describe the events of March 15th, 2024.",
            "start_time": 0.0,
            "end_time": 4.2,
        },
        {
            "speaker_id": "witness",
            "speaker_label": "John Doe",
            "text": "I was driving westbound on Highway 101 when the accident occurred at approximately 3:30 PM.",
            "start_time": 5.0,
            "end_time": 12.8,
        },
        {
            "speaker_id": "attorney",
            "speaker_label": "Attorney",
            "text": "What happened next?",
            "start_time": 13.5,
            "end_time": 15.0,
        },
        {
            "speaker_id": "witness",
            "speaker_label": "John Doe",
            "text": "I saw the other vehicle cross the center line and enter my lane. I immediately applied my brakes but was unable to avoid the collision.",
            "start_time": 15.8,
            "end_time": 25.3,
        },
    ]

    metadata = {
        "case_number": "2024-PI-98765",
        "case_name": "Doe v. Smith",
        "client": "John Doe",
        "matter_type": "Personal Injury - Auto Accident",
        "document_name": "Deposition_Doe_John_20250108.mp3",
        "date": "January 8, 2025",
        "witness": "John Doe",
        "duration": 1800,
    }

    output_path = "/tmp/deposition_test.docx"
    success = exporter.export_to_docx(segments, metadata, output_path)

    if success:
        print(f"✓ Deposition exported successfully to: {output_path}")
        return True
    else:
        print("✗ Failed to export deposition")
        return False


def test_timestamp_formatting():
    """Test timestamp formatting."""
    print("\nTesting timestamp formatting...")

    from app.workers.pipelines.transcript_exporter import TranscriptExporter

    exporter = TranscriptExporter()

    test_cases = [
        (30, "00:00:30"),
        (90, "00:01:30"),
        (3661, "01:01:01"),
        (7200, "02:00:00"),
    ]

    all_passed = True
    for seconds, expected in test_cases:
        result = exporter._format_timestamp(seconds)
        if result == expected:
            print(f"  ✓ {seconds}s -> {result}")
        else:
            print(f"  ✗ {seconds}s -> {result} (expected {expected})")
            all_passed = False

    return all_passed


def test_duration_formatting():
    """Test duration formatting."""
    print("\nTesting duration formatting...")

    from app.workers.pipelines.transcript_exporter import TranscriptExporter

    exporter = TranscriptExporter()

    test_cases = [
        (30, "30 seconds"),
        (90, "1 min 30 sec"),
        (3661, "1 hr 1 min"),
        (7200, "2 hr 0 min"),
    ]

    all_passed = True
    for seconds, expected in test_cases:
        result = exporter._format_duration(seconds)
        if result == expected:
            print(f"  ✓ {seconds}s -> {result}")
        else:
            print(f"  ✗ {seconds}s -> {result} (expected {expected})")
            all_passed = False

    return all_passed


def main():
    """Run all tests."""
    print("=" * 60)
    print("TRANSCRIPT EXPORTER TEST SUITE")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Basic Export", test_basic_export()))
    results.append(("Exporter Class", test_exporter_class()))
    results.append(("Timestamp Formatting", test_timestamp_formatting()))
    results.append(("Duration Formatting", test_duration_formatting()))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    exit(main())
