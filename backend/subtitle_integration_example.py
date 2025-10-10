"""
Subtitle Generator Integration Example

Demonstrates how to integrate the SubtitleGenerator with the transcription pipeline.
"""

from typing import List, Dict, Any
from app.workers.pipelines import SubtitleGenerator, create_subtitle_generator


def example_1_basic_usage():
    """Basic subtitle generation from transcription segments."""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)

    # Simulated transcription output from Whisper/WhisperX
    segments = [
        {
            "text": "This court is now in session. Case number 2024-CV-1234.",
            "start": 0.0,
            "end": 5.2,
            "speaker": "Judge",
            "confidence": 0.99
        },
        {
            "text": "Your Honor, the plaintiff is ready to proceed.",
            "start": 5.8,
            "end": 9.5,
            "speaker": "Plaintiff Attorney",
            "confidence": 0.97
        },
        {
            "text": "The defense is also ready, Your Honor.",
            "start": 10.0,
            "end": 12.5,
            "speaker": "Defense Attorney",
            "confidence": 0.98
        }
    ]

    # Create generator and export all formats
    generator = SubtitleGenerator(chars_per_caption=42)
    paths = generator.export_all(segments, "/tmp/courtroom_session")

    print("\nGenerated subtitle files:")
    for fmt, path in paths.items():
        print(f"  {fmt.upper()}: {path}")


def example_2_custom_caption_length():
    """Generate subtitles with different caption lengths for different platforms."""
    print("\n" + "=" * 60)
    print("Example 2: Platform-Specific Caption Lengths")
    print("=" * 60)

    segments = [
        {
            "text": "The court will now hear arguments on the motion to dismiss filed by the defense.",
            "start": 0.0,
            "end": 6.0,
            "speaker": "Judge"
        }
    ]

    # Mobile platform (short captions)
    mobile_gen = SubtitleGenerator(chars_per_caption=30)
    mobile_paths = mobile_gen.export_all(segments, "/tmp/mobile_subtitles")
    print("\nMobile (30 chars):", mobile_paths['srt'])

    # Desktop platform (standard captions)
    desktop_gen = SubtitleGenerator(chars_per_caption=60)
    desktop_paths = desktop_gen.export_all(segments, "/tmp/desktop_subtitles")
    print("Desktop (60 chars):", desktop_paths['srt'])


def example_3_celery_task_integration():
    """Simulate Celery task integration."""
    print("\n" + "=" * 60)
    print("Example 3: Celery Task Integration Pattern")
    print("=" * 60)

    def process_transcription_subtitles(
        transcription_id: int,
        segments: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Process transcription and generate subtitles.
        This would typically be a Celery task.
        """
        # Create subtitle generator
        generator = create_subtitle_generator(chars_per_caption=42)

        # Generate subtitles
        base_path = f"/transcriptions/{transcription_id}/subtitles"
        subtitle_paths = generator.export_all(
            segments,
            base_path,
            include_speaker=True
        )

        return subtitle_paths

    # Example usage
    transcription_segments = [
        {
            "text": "The witness will please take the stand.",
            "start": 0.0,
            "end": 3.0,
            "speaker": "Judge",
            "confidence": 0.99
        },
        {
            "text": "Do you swear to tell the truth?",
            "start": 3.5,
            "end": 5.5,
            "speaker": "Court Clerk",
            "confidence": 0.98
        },
        {
            "text": "I do.",
            "start": 6.0,
            "end": 6.5,
            "speaker": "Witness",
            "confidence": 0.99
        }
    ]

    result = process_transcription_subtitles(12345, transcription_segments)
    print("\nGenerated subtitle files:")
    for fmt, path in result.items():
        print(f"  {fmt}: {path}")


def example_4_minio_storage_integration():
    """Example of uploading generated subtitles to MinIO."""
    print("\n" + "=" * 60)
    print("Example 4: MinIO Storage Integration Pattern")
    print("=" * 60)

    def generate_and_store_subtitles(
        case_id: str,
        document_id: int,
        segments: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Generate subtitles and store them in MinIO.
        Returns URLs/paths to stored files.
        """
        import tempfile
        from pathlib import Path

        # Create temporary directory for generation
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate subtitles locally
            generator = SubtitleGenerator(chars_per_caption=42)
            base_path = Path(temp_dir) / "subtitle"

            local_paths = generator.export_all(segments, str(base_path))

            # Simulate uploading to MinIO (would use actual minio_client)
            storage_paths = {}
            for fmt, local_path in local_paths.items():
                # Simulated MinIO path
                minio_path = f"cases/{case_id}/documents/{document_id}/subtitles/transcript.{fmt}"
                storage_paths[fmt] = minio_path

                # In real implementation:
                # with open(local_path, 'rb') as f:
                #     minio_client.upload_file(
                #         file_data=f,
                #         object_name=minio_path,
                #         content_type=get_content_type(fmt)
                #     )

                print(f"  Would upload: {local_path} -> {minio_path}")

            return storage_paths

    # Example usage
    test_segments = [
        {
            "text": "Please state your full name for the record.",
            "start": 0.0,
            "end": 3.0,
            "speaker": "Attorney"
        },
        {
            "text": "My name is Sarah Johnson.",
            "start": 3.5,
            "end": 5.0,
            "speaker": "Witness"
        }
    ]

    paths = generate_and_store_subtitles("CASE-2024-001", 789, test_segments)
    print("\nStored subtitle paths in MinIO:")
    for fmt, path in paths.items():
        print(f"  {fmt}: {path}")


def example_5_whisper_integration():
    """Example showing integration with Whisper transcription output."""
    print("\n" + "=" * 60)
    print("Example 5: Whisper/WhisperX Integration Pattern")
    print("=" * 60)

    def process_whisper_output(whisper_result: Dict[str, Any]) -> Dict[str, str]:
        """
        Convert Whisper output to subtitle formats.

        Args:
            whisper_result: Output from Whisper/WhisperX transcription

        Returns:
            Dictionary of subtitle file paths
        """
        # Extract segments from Whisper result
        segments = []

        for segment in whisper_result.get('segments', []):
            segments.append({
                'text': segment.get('text', '').strip(),
                'start': segment.get('start', 0.0),
                'end': segment.get('end', 0.0),
                'speaker': segment.get('speaker', 'Unknown'),
                'confidence': segment.get('confidence', 0.0)
            })

        # Generate subtitles
        generator = SubtitleGenerator(chars_per_caption=42)
        subtitle_paths = generator.export_all(
            segments,
            "/tmp/transcription/subtitle"
        )

        return subtitle_paths

    # Simulated Whisper output
    whisper_output = {
        'text': 'Complete transcription text...',
        'language': 'en',
        'segments': [
            {
                'id': 0,
                'start': 0.0,
                'end': 4.5,
                'text': 'This is the opening statement.',
                'speaker': 'SPEAKER_01',
                'confidence': 0.95
            },
            {
                'id': 1,
                'start': 5.0,
                'end': 8.0,
                'text': 'I would like to present evidence.',
                'speaker': 'SPEAKER_02',
                'confidence': 0.93
            }
        ]
    }

    result = process_whisper_output(whisper_output)
    print("\nSubtitle files generated from Whisper output:")
    for fmt, path in result.items():
        print(f"  {fmt}: {path}")


def example_6_format_specific_export():
    """Export only specific formats."""
    print("\n" + "=" * 60)
    print("Example 6: Format-Specific Export")
    print("=" * 60)

    segments = [
        {
            "text": "We will now hear closing arguments.",
            "start": 0.0,
            "end": 3.0,
            "speaker": "Judge"
        }
    ]

    generator = SubtitleGenerator()

    # Export only SRT (for video players)
    srt_path = generator.export_srt(segments, "/tmp/video_subtitles.srt")
    print(f"\nSRT only: {srt_path}")

    # Export only VTT (for web players)
    vtt_path = generator.export_vtt(segments, "/tmp/web_subtitles.vtt")
    print(f"VTT only: {vtt_path}")

    # Export only JSON (for API/data processing)
    json_path = generator.export_json(segments, "/tmp/data_export.json")
    print(f"JSON only: {json_path}")

    # Export selected formats using export_all
    selected_paths = generator.export_all(
        segments,
        "/tmp/selected_formats",
        formats=["srt", "json"]  # Only SRT and JSON
    )
    print(f"\nSelected formats: {list(selected_paths.keys())}")


def example_7_no_speaker_labels():
    """Generate subtitles without speaker identification."""
    print("\n" + "=" * 60)
    print("Example 7: Subtitles Without Speaker Labels")
    print("=" * 60)

    # Segments without speaker info
    segments = [
        {"text": "This is a generic subtitle.", "start": 0.0, "end": 2.5},
        {"text": "No speaker identification needed.", "start": 3.0, "end": 5.5},
    ]

    generator = SubtitleGenerator()

    # Export without speaker labels
    paths = generator.export_all(
        segments,
        "/tmp/generic_subtitles",
        include_speaker=False
    )

    print("\nGenerated subtitles without speaker labels:")
    for fmt, path in paths.items():
        print(f"  {fmt}: {path}")


def example_8_timestamp_utilities():
    """Demonstrate timestamp formatting utilities."""
    print("\n" + "=" * 60)
    print("Example 8: Timestamp Formatting Utilities")
    print("=" * 60)

    generator = SubtitleGenerator()

    test_times = [0.0, 65.5, 3665.789, 7325.123]

    print("\nTimestamp Formatting:")
    print("\nSeconds -> SRT (HH:MM:SS,mmm) -> VTT (HH:MM:SS.mmm)")
    print("-" * 60)

    for seconds in test_times:
        srt = generator.format_timestamp_srt(seconds)
        vtt = generator.format_timestamp_vtt(seconds)
        print(f"{seconds:10.3f}s -> {srt} -> {vtt}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("SUBTITLE GENERATOR INTEGRATION EXAMPLES")
    print("=" * 70)

    try:
        example_1_basic_usage()
        example_2_custom_caption_length()
        example_3_celery_task_integration()
        example_4_minio_storage_integration()
        example_5_whisper_integration()
        example_6_format_specific_export()
        example_7_no_speaker_labels()
        example_8_timestamp_utilities()

        print("\n" + "=" * 70)
        print("✓ All examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
