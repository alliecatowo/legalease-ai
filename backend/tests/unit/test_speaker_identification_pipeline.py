import pytest

from app.workers.pipelines.speaker_identification import (
    ConversationContext,
    NameContextType,
    SpacyNERExtractor,
    SpeakerIdentificationPipeline,
)


@pytest.mark.asyncio
async def test_spacy_self_identification_detected():
    segments = [
        {"speaker": "SPEAKER_01", "text": "I'm Detective Molly.", "start": 0.0},
    ]

    context = ConversationContext(
        segments=segments,
        speakers=["SPEAKER_01"],
        filename=None,
        duration=5.0,
    )

    extractor = SpacyNERExtractor()
    evidence = await extractor.extract(context)

    assert evidence, "Expected spaCy to extract at least one entity"
    self_id_evidence = [ev for ev in evidence if ev.context_type == NameContextType.SELF_IDENTIFICATION]
    assert self_id_evidence, "Expected self-identification context for 'I'm Detective Molly.'"
    assert self_id_evidence[0].confidence >= 0.85, "Self-identification evidence should have high confidence"


@pytest.mark.asyncio
async def test_spacy_vocative_not_misclassified_as_self_id():
    segments = [
        {"speaker": "SPEAKER_02", "text": "Hi Molly, thanks for meeting.", "start": 0.0},
    ]

    context = ConversationContext(
        segments=segments,
        speakers=["SPEAKER_02"],
        filename=None,
        duration=5.0,
    )

    extractor = SpacyNERExtractor()
    evidence = await extractor.extract(context)

    assert evidence, "Expected spaCy to extract the addressed name"
    assert evidence[0].context_type == NameContextType.VOCATIVE
    assert evidence[0].confidence < 0.9, "Vocative confidence should be lower than self-identification"


@pytest.mark.asyncio
async def test_pipeline_applies_self_identification_name():
    segments = [
        {"speaker": "SPEAKER_01", "text": "I'm Detective Molly.", "start": 0.0},
        {"speaker": "SPEAKER_02", "text": "Hi Molly, thanks for meeting.", "start": 1.0},
    ]

    pipeline = SpeakerIdentificationPipeline(use_spacy=True)
    result = await pipeline.identify_speakers(segments, ["SPEAKER_01", "SPEAKER_02"])

    assert "SPEAKER_01" in result
    assert result["SPEAKER_01"]["name"] == "Detective Molly"
    assert result["SPEAKER_01"]["confidence"] >= 0.9

    # Ensure vocative evidence does not cause misattribution
    assert "SPEAKER_02" in result
    assert result["SPEAKER_02"]["confidence"] < 0.5
