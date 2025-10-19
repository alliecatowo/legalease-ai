"""
Pipeline modules for document processing, embeddings, and encoding.
"""

from app.workers.pipelines.embeddings import FastEmbedPipeline as EmbeddingPipeline
from app.workers.pipelines.bm25_encoder import BM25Encoder
from app.workers.pipelines.ocr_pipeline import OCRPipeline
from app.workers.pipelines.chunker import DocumentChunker, TextChunk
from app.workers.pipelines.indexer import QdrantIndexer
from app.workers.pipelines.document_pipeline import (
    DocumentProcessor,
    ProcessingResult,
    ProcessingStage,
)
from app.workers.pipelines.subtitle_generator import (
    SubtitleGenerator,
    TranscriptionSegment,
    create_subtitle_generator,
)
from app.workers.pipelines.audio_preprocessing import (
    AudioPreprocessor,
    AudioMetadata,
    preprocess_audio,
)
from app.workers.pipelines.whisperx_pipeline import (
    WhisperXPipeline,
    TranscriptionResult,
    transcribe_audio,
)
from app.workers.pipelines.transcript_exporter import (
    TranscriptExporter,
    TranscriptSegment,
    Speaker,
    export_transcript,
)

__all__ = [
    "EmbeddingPipeline",
    "BM25Encoder",
    "OCRPipeline",
    "DocumentChunker",
    "TextChunk",
    "QdrantIndexer",
    "DocumentProcessor",
    "ProcessingResult",
    "ProcessingStage",
    # Subtitle generation
    "SubtitleGenerator",
    "TranscriptionSegment",
    "create_subtitle_generator",
    # Audio preprocessing and transcription
    "AudioPreprocessor",
    "AudioMetadata",
    "preprocess_audio",
    "WhisperXPipeline",
    "TranscriptionResult",
    "transcribe_audio",
    # Transcript export
    "TranscriptExporter",
    "Speaker",
    "export_transcript",
]
