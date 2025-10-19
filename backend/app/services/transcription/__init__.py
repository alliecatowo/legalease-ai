"""Transcription service - clean exports for all modules."""

from app.services.transcription.core import TranscriptionCoreService
from app.services.transcription.storage import TranscriptionStorageService
from app.services.transcription.export import TranscriptionExportService


class TranscriptionService:
    """
    Unified TranscriptionService that delegates to specialized sub-services.

    This maintains backward compatibility while internally delegating to:
    - TranscriptionCoreService: CRUD operations
    - TranscriptionStorageService: MinIO operations
    - TranscriptionExportService: Export formats
    """

    # Expose supported formats from storage service
    SUPPORTED_FORMATS = TranscriptionStorageService.SUPPORTED_FORMATS

    # CRUD operations (core.py)
    get_transcription = staticmethod(TranscriptionCoreService.get_transcription)
    list_case_transcriptions = staticmethod(TranscriptionCoreService.list_case_transcriptions)
    get_transcription_details = staticmethod(TranscriptionCoreService.get_transcription_details)
    reprocess_transcription = staticmethod(TranscriptionCoreService.reprocess_transcription)
    delete_transcription = staticmethod(TranscriptionCoreService.delete_transcription)
    toggle_key_moment = staticmethod(TranscriptionCoreService.toggle_key_moment)
    get_key_moments = staticmethod(TranscriptionCoreService.get_key_moments)
    update_speaker = staticmethod(TranscriptionCoreService.update_speaker)

    # Storage operations (storage.py)
    upload_audio_for_transcription = staticmethod(TranscriptionStorageService.upload_audio_for_transcription)
    download_audio = staticmethod(TranscriptionStorageService.download_audio)
    get_media_info = staticmethod(TranscriptionStorageService.get_media_info)
    stream_media_range = staticmethod(TranscriptionStorageService.stream_media_range)

    # Export operations (export.py)
    export_as_json = staticmethod(TranscriptionExportService.export_as_json)
    export_as_docx = staticmethod(TranscriptionExportService.export_as_docx)
    export_as_srt = staticmethod(TranscriptionExportService.export_as_srt)
    export_as_vtt = staticmethod(TranscriptionExportService.export_as_vtt)
    export_as_txt = staticmethod(TranscriptionExportService.export_as_txt)


# Also export individual services for direct use
__all__ = [
    'TranscriptionService',
    'TranscriptionCoreService',
    'TranscriptionStorageService',
    'TranscriptionExportService',
]
