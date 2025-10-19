#!/usr/bin/env python3
"""
Test the new SpeakerIdentificationPipeline on existing transcription data.

Usage:
    python scripts/test_speaker_identification.py <transcription_gid>
"""

import sys
import os
import asyncio
import json

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.workers.pipelines.speaker_identification import SpeakerIdentificationPipeline


async def test_pipeline(transcription_gid: str):
    """Test the speaker identification pipeline on an existing transcription"""

    # Connect to database
    database_url = os.getenv("DATABASE_URL", "postgresql://legalease:legalease@localhost:5432/legalease")
    engine = create_engine(database_url)

    # Fetch transcription data
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT filename, duration, segments, speakers FROM transcriptions WHERE gid = :gid"),
            {"gid": transcription_gid}
        )
        row = result.fetchone()

        if not row:
            print(f"❌ Transcription {transcription_gid} not found")
            return

        filename, duration, segments_json, speakers_json = row
        segments = json.loads(segments_json) if isinstance(segments_json, str) else segments_json
        current_speakers = json.loads(speakers_json) if isinstance(speakers_json, str) else speakers_json

    print(f"\n{'='*80}")
    print(f"Testing Speaker Identification Pipeline")
    print(f"{'='*80}")
    print(f"\n📄 Transcription: {transcription_gid}")
    print(f"🎬 Filename: {filename}")
    print(f"⏱️  Duration: {duration:.1f}s" if duration else "⏱️  Duration: N/A")
    print(f"💬 Segments: {len(segments)}")
    print(f"🎤 Speakers: {len(current_speakers)}")

    print(f"\n📊 Current Speaker Names:")
    for speaker in current_speakers:
        print(f"   {speaker['id']}: {speaker['name']} ({speaker.get('segments_count', 0)} segments)")

    # Extract speaker IDs
    speaker_ids = [s['id'] for s in current_speakers]

    print(f"\n🚀 Running SpeakerIdentificationPipeline...")
    print(f"   - spaCy NER extractor (linguistic analysis)")
    print(f"   - Pattern-based extractor (fallback)")
    print(f"   - Filename extractor")

    # Run the pipeline
    pipeline = SpeakerIdentificationPipeline(use_spacy=True)
    inferred_names = await pipeline.identify_speakers(
        segments=segments,
        speakers=speaker_ids,
        filename=filename,
        duration=duration or 0.0
    )

    print(f"\n✅ Pipeline completed!")
    print(f"\n🎯 Inferred Names:")

    if not inferred_names:
        print("   ❌ No names inferred (no evidence above confidence threshold)")
    else:
        for speaker_id, inference in inferred_names.items():
            name = inference.get('name', 'Unknown')
            confidence = inference.get('confidence', 0.0)
            evidence_count = inference.get('evidence_count', 0)
            reasoning = inference.get('reasoning', 'No reasoning')

            print(f"\n   {speaker_id}:")
            print(f"      Name: {name}")
            print(f"      Confidence: {confidence:.2%}")
            print(f"      Evidence: {evidence_count} instance(s)")
            print(f"      Reasoning: {reasoning}")

            # Compare with current name
            current = next((s for s in current_speakers if s['id'] == speaker_id), None)
            if current:
                if confidence > 0.6:
                    print(f"      ✅ Would apply: '{current['name']}' → '{name}'")
                else:
                    print(f"      ⏭️  Would skip: confidence {confidence:.2%} < 60% threshold")

    print(f"\n{'='*80}")
    print(f"Test complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_speaker_identification.py <transcription_gid>")
        print("\nAvailable transcriptions:")

        # Show recent transcriptions
        database_url = os.getenv("DATABASE_URL", "postgresql://legalease:legalease@localhost:5432/legalease")
        engine = create_engine(database_url)

        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT gid, filename, duration
                    FROM transcriptions
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
            )
            for row in result:
                gid, filename, duration = row
                duration_str = f"{duration:.1f}s" if duration else "N/A"
                print(f"  {gid} - {filename} ({duration_str})")

        sys.exit(1)

    transcription_gid = sys.argv[1]
    asyncio.run(test_pipeline(transcription_gid))
