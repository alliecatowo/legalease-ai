"""
Test script for SubtitleGenerator

Demonstrates subtitle generation in SRT, VTT, and JSON formats
with speaker labels and configurable caption settings.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.workers.pipelines.subtitle_generator import SubtitleGenerator, create_subtitle_generator


def test_basic_subtitle_generation():
    """Test basic subtitle generation with sample transcription data."""
    print("=" * 60)
    print("Testing SubtitleGenerator")
    print("=" * 60)

    # Sample transcription segments
    segments = [
        {
            "text": "Welcome to the courtroom. This hearing is now in session.",
            "start": 0.0,
            "end": 4.5,
            "speaker": "Judge",
            "confidence": 0.98
        },
        {
            "text": "Your Honor, the defense would like to present new evidence in this case.",
            "start": 5.0,
            "end": 9.2,
            "speaker": "Defense Attorney",
            "confidence": 0.95
        },
        {
            "text": "Objection, Your Honor! This evidence was not disclosed during discovery.",
            "start": 9.5,
            "end": 13.8,
            "speaker": "Prosecutor",
            "confidence": 0.97
        },
        {
            "text": "I'll allow it. Please proceed with your presentation of the evidence.",
            "start": 14.2,
            "end": 18.0,
            "speaker": "Judge",
            "confidence": 0.96
        },
        {
            "text": "Thank you, Your Honor. As you can see from Exhibit A, the defendant was not at the scene during the time of the alleged incident.",
            "start": 18.5,
            "end": 26.3,
            "speaker": "Defense Attorney",
            "confidence": 0.94
        },
    ]

    # Create subtitle generator
    generator = SubtitleGenerator(chars_per_caption=50)

    # Create output directory
    output_dir = Path(__file__).parent / "test_subtitles"
    output_dir.mkdir(exist_ok=True)

    print(f"\nOutput directory: {output_dir}\n")

    # Test 1: Export to SRT
    print("1. Generating SRT subtitle file...")
    srt_path = generator.export_srt(
        segments,
        str(output_dir / "courtroom_transcript.srt"),
        include_speaker=True
    )
    print(f"   ✓ SRT file created: {srt_path}")

    # Test 2: Export to VTT
    print("\n2. Generating VTT subtitle file...")
    vtt_path = generator.export_vtt(
        segments,
        str(output_dir / "courtroom_transcript.vtt"),
        include_speaker=True
    )
    print(f"   ✓ VTT file created: {vtt_path}")

    # Test 3: Export to JSON
    print("\n3. Generating JSON subtitle file...")
    json_path = generator.export_json(
        segments,
        str(output_dir / "courtroom_transcript.json"),
        pretty=True
    )
    print(f"   ✓ JSON file created: {json_path}")

    # Test 4: Export all formats at once
    print("\n4. Generating all formats at once...")
    all_paths = generator.export_all(
        segments,
        str(output_dir / "courtroom_all_formats"),
        include_speaker=True
    )
    print("   ✓ All formats created:")
    for format_type, path in all_paths.items():
        print(f"     - {format_type.upper()}: {path}")

    # Display file contents
    print("\n" + "=" * 60)
    print("Sample Output Files")
    print("=" * 60)

    print("\n--- SRT Format (courtroom_transcript.srt) ---")
    with open(srt_path, "r", encoding="utf-8") as f:
        print(f.read())

    print("\n--- VTT Format (courtroom_transcript.vtt) ---")
    with open(vtt_path, "r", encoding="utf-8") as f:
        print(f.read())

    print("\n--- JSON Format (courtroom_transcript.json) ---")
    with open(json_path, "r", encoding="utf-8") as f:
        print(f.read())


def test_timestamp_formatting():
    """Test timestamp formatting for different durations."""
    print("\n" + "=" * 60)
    print("Testing Timestamp Formatting")
    print("=" * 60)

    generator = SubtitleGenerator()

    test_times = [
        0.0,           # 00:00:00
        5.123,         # 00:00:05
        65.456,        # 00:01:05
        3665.789,      # 01:01:05
        7200.0,        # 02:00:00
        7325.555,      # 02:02:05
    ]

    print("\nSRT Format (HH:MM:SS,mmm):")
    for time_val in test_times:
        srt_format = generator.format_timestamp_srt(time_val)
        print(f"  {time_val:10.3f}s -> {srt_format}")

    print("\nVTT Format (HH:MM:SS.mmm):")
    for time_val in test_times:
        vtt_format = generator.format_timestamp_vtt(time_val)
        print(f"  {time_val:10.3f}s -> {vtt_format}")


def test_text_wrapping():
    """Test text wrapping with different caption lengths."""
    print("\n" + "=" * 60)
    print("Testing Text Wrapping")
    print("=" * 60)

    long_text = "This is a very long piece of text that needs to be wrapped into multiple lines based on the maximum character limit per caption to ensure readability."

    for max_chars in [30, 42, 60]:
        print(f"\nMax {max_chars} chars per line:")
        generator = SubtitleGenerator(chars_per_caption=max_chars)
        lines = generator.wrap_text(long_text)
        for i, line in enumerate(lines, 1):
            print(f"  Line {i} ({len(line)} chars): {line}")


def test_factory_function():
    """Test the factory function."""
    print("\n" + "=" * 60)
    print("Testing Factory Function")
    print("=" * 60)

    generator = create_subtitle_generator(chars_per_caption=35)
    print(f"\n✓ Created generator with chars_per_caption = {generator.chars_per_caption}")

    test_segment = [{
        "text": "This is a test of the factory function",
        "start": 0.0,
        "end": 3.0,
        "speaker": "Tester"
    }]

    output_dir = Path(__file__).parent / "test_subtitles"
    output_dir.mkdir(exist_ok=True)

    paths = generator.export_all(
        test_segment,
        str(output_dir / "factory_test")
    )
    print(f"✓ Generated files using factory function:")
    for fmt, path in paths.items():
        print(f"  - {fmt}: {path}")


def test_no_speaker_labels():
    """Test subtitle generation without speaker labels."""
    print("\n" + "=" * 60)
    print("Testing Without Speaker Labels")
    print("=" * 60)

    segments = [
        {"text": "First subtitle without speaker", "start": 0.0, "end": 2.0},
        {"text": "Second subtitle without speaker", "start": 2.5, "end": 4.5},
    ]

    generator = SubtitleGenerator()
    output_dir = Path(__file__).parent / "test_subtitles"
    output_dir.mkdir(exist_ok=True)

    srt_path = generator.export_srt(
        segments,
        str(output_dir / "no_speaker.srt"),
        include_speaker=False
    )

    print(f"\n✓ Generated SRT without speaker labels: {srt_path}")
    print("\nContent:")
    with open(srt_path, "r", encoding="utf-8") as f:
        print(f.read())


if __name__ == "__main__":
    try:
        test_basic_subtitle_generation()
        test_timestamp_formatting()
        test_text_wrapping()
        test_factory_function()
        test_no_speaker_labels()

        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
