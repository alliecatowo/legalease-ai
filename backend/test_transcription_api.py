"""
Test script for the Transcription Management API.

This script demonstrates how to use the transcription API endpoints.
"""

import requests
import json
from pathlib import Path
import io

# API Base URL
BASE_URL = "http://localhost:8000/api/v1"

# Test data
CASE_ID = 1  # Update this with a valid case ID


def create_test_case():
    """Create a test case for transcription uploads."""
    print("Creating test case...")

    case_data = {
        "name": "Audio Transcription Test Case",
        "case_number": "AUDIO-TEST-001",
        "client": "Test Client",
        "matter_type": "Deposition",
    }

    response = requests.post(f"{BASE_URL}/cases", json=case_data)

    if response.status_code == 201:
        case = response.json()
        print(f"✓ Case created: ID={case['id']}, Number={case['case_number']}")
        return case["id"]
    else:
        print(f"✗ Failed to create case: {response.status_code}")
        print(response.text)
        return None


def upload_audio_file(case_id: int, filename: str = "test_audio.mp3"):
    """Upload an audio file for transcription."""
    print(f"\nUploading audio file '{filename}' to case {case_id}...")

    # Create a mock audio file
    # In real usage, you would use actual audio/video files
    mock_audio_content = b"Mock audio file content for testing"

    files = {
        "file": (filename, io.BytesIO(mock_audio_content), "audio/mpeg")
    }

    response = requests.post(
        f"{BASE_URL}/cases/{case_id}/transcriptions",
        files=files,
    )

    if response.status_code == 201:
        result = response.json()
        print(f"✓ Audio uploaded successfully:")
        print(f"  Document ID: {result['document_id']}")
        print(f"  Status: {result['status']}")
        print(f"  Message: {result['message']}")
        return result["document_id"]
    else:
        print(f"✗ Failed to upload audio: {response.status_code}")
        print(response.text)
        return None


def create_mock_transcription(document_id: int):
    """Create a mock transcription in the database (simulating background processing)."""
    print(f"\nCreating mock transcription for document {document_id}...")

    # This would normally be done by a background Celery task
    # For testing, we'll directly insert it via a database connection
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.models.transcription import Transcription
    from app.models.document import Document
    import os

    # Get database URL from environment
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://legalease_user:legalease_password@localhost:5432/legalease_db",
    )

    engine = create_engine(db_url)

    with Session(engine) as session:
        # Check if document exists
        document = session.query(Document).filter(Document.id == document_id).first()
        if not document:
            print(f"✗ Document {document_id} not found")
            return None

        # Create transcription
        transcription = Transcription(
            document_id=document_id,
            format="mp3",
            duration=125.5,  # 2 minutes 5.5 seconds
            speakers=[
                {"speaker_id": "SPEAKER_00", "label": "Attorney", "confidence": 0.95},
                {"speaker_id": "SPEAKER_01", "label": "Witness", "confidence": 0.92},
            ],
            segments=[
                {
                    "start": 0.0,
                    "end": 5.2,
                    "text": "Please state your full name for the record.",
                    "speaker": "SPEAKER_00",
                    "confidence": 0.98,
                },
                {
                    "start": 5.5,
                    "end": 8.3,
                    "text": "My name is John Michael Smith.",
                    "speaker": "SPEAKER_01",
                    "confidence": 0.96,
                },
                {
                    "start": 9.0,
                    "end": 13.5,
                    "text": "And what is your current occupation?",
                    "speaker": "SPEAKER_00",
                    "confidence": 0.97,
                },
                {
                    "start": 14.0,
                    "end": 20.8,
                    "text": "I am a project manager at Tech Solutions Incorporated.",
                    "speaker": "SPEAKER_01",
                    "confidence": 0.95,
                },
                {
                    "start": 21.5,
                    "end": 28.0,
                    "text": "How long have you been employed in that position?",
                    "speaker": "SPEAKER_00",
                    "confidence": 0.99,
                },
                {
                    "start": 28.5,
                    "end": 34.2,
                    "text": "I have been with the company for approximately seven years.",
                    "speaker": "SPEAKER_01",
                    "confidence": 0.94,
                },
            ],
        )

        session.add(transcription)
        session.commit()
        session.refresh(transcription)

        print(f"✓ Mock transcription created: ID={transcription.id}")
        return transcription.id


def list_transcriptions(case_id: int):
    """List all transcriptions for a case."""
    print(f"\nListing transcriptions for case {case_id}...")

    response = requests.get(f"{BASE_URL}/cases/{case_id}/transcriptions")

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Found {result['total']} transcription(s):")
        for trans in result["transcriptions"]:
            print(f"  - ID: {trans['id']}")
            print(f"    Filename: {trans['filename']}")
            print(f"    Duration: {trans['duration']}s")
            print(f"    Segments: {trans['segment_count']}")
            print(f"    Speakers: {trans['speaker_count']}")
            print(f"    Created: {trans['created_at']}")
        return result["transcriptions"]
    else:
        print(f"✗ Failed to list transcriptions: {response.status_code}")
        print(response.text)
        return []


def get_transcription_details(transcription_id: int):
    """Get detailed transcription information."""
    print(f"\nGetting transcription {transcription_id} details...")

    response = requests.get(f"{BASE_URL}/transcriptions/{transcription_id}")

    if response.status_code == 200:
        trans = response.json()
        print(f"✓ Transcription details:")
        print(f"  ID: {trans['id']}")
        print(f"  Document ID: {trans['document_id']}")
        print(f"  Case ID: {trans['case_id']}")
        print(f"  Filename: {trans['filename']}")
        print(f"  Duration: {trans['duration']}s")
        print(f"  Speakers: {len(trans.get('speakers', []))}")
        print(f"  Segments: {len(trans.get('segments', []))}")

        # Show first few segments
        if trans.get("segments"):
            print("\n  First segments:")
            for seg in trans["segments"][:3]:
                print(
                    f"    [{seg['start']:.1f}s - {seg['end']:.1f}s] {seg.get('speaker', 'Unknown')}: {seg['text']}"
                )

        return trans
    else:
        print(f"✗ Failed to get transcription: {response.status_code}")
        print(response.text)
        return None


def download_transcription(transcription_id: int, format: str = "json"):
    """Download transcription in specified format."""
    print(f"\nDownloading transcription {transcription_id} as {format.upper()}...")

    response = requests.get(
        f"{BASE_URL}/transcriptions/{transcription_id}/download/{format}"
    )

    if response.status_code == 200:
        # Save to file
        filename = response.headers.get("Content-Disposition", "").split("filename=")[-1].strip('"')
        if not filename:
            filename = f"transcription_{transcription_id}.{format}"

        output_path = Path(f"/tmp/{filename}")
        output_path.write_bytes(response.content)

        print(f"✓ Transcription downloaded successfully:")
        print(f"  Format: {format}")
        print(f"  Size: {len(response.content)} bytes")
        print(f"  Saved to: {output_path}")

        # Show preview for text formats
        if format in ["txt", "srt", "vtt", "json"]:
            preview = response.content.decode("utf-8")[:500]
            print(f"\n  Preview:")
            print("  " + "\n  ".join(preview.split("\n")[:10]))
            if len(response.content) > 500:
                print("  ...")

        return output_path
    else:
        print(f"✗ Failed to download transcription: {response.status_code}")
        print(response.text)
        return None


def delete_transcription(transcription_id: int):
    """Delete a transcription."""
    print(f"\nDeleting transcription {transcription_id}...")

    response = requests.delete(f"{BASE_URL}/transcriptions/{transcription_id}")

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Transcription deleted:")
        print(f"  ID: {result['id']}")
        print(f"  Filename: {result['filename']}")
        print(f"  Message: {result['message']}")
        return True
    else:
        print(f"✗ Failed to delete transcription: {response.status_code}")
        print(response.text)
        return False


def main():
    """Run the complete transcription API test flow."""
    print("=" * 60)
    print("Transcription Management API - Test Script")
    print("=" * 60)

    # 1. Create a test case
    case_id = create_test_case()
    if not case_id:
        print("\n✗ Failed to create test case. Exiting.")
        return

    # 2. Upload audio file
    document_id = upload_audio_file(case_id, "deposition_audio.mp3")
    if not document_id:
        print("\n✗ Failed to upload audio. Exiting.")
        return

    # 3. Create mock transcription (simulating background processing)
    transcription_id = create_mock_transcription(document_id)
    if not transcription_id:
        print("\n✗ Failed to create transcription. Exiting.")
        return

    # 4. List transcriptions
    transcriptions = list_transcriptions(case_id)

    # 5. Get transcription details
    if transcriptions:
        get_transcription_details(transcription_id)

    # 6. Download in different formats
    for format in ["json", "txt", "srt", "vtt", "docx"]:
        download_transcription(transcription_id, format)

    # 7. Delete transcription (optional - uncomment to test)
    # delete_transcription(transcription_id)

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
