/**
 * Standard transcription interfaces - provider agnostic
 *
 * These types define the contract between the transcription system and
 * any STT provider (Chirp, Whisper, Deepgram, etc.)
 */

/** Standard input for all transcription providers */
export interface TranscriptionRequest {
  /** Media URI - gs:// for GCS or https:// for URLs */
  mediaUri: string

  /** BCP-47 language code or 'auto' for detection (default: 'auto') */
  language?: string

  /** Enable speaker diarization (default: true) */
  enableDiarization?: boolean

  /** Maximum number of speakers to identify (default: 6) */
  maxSpeakers?: number

  /** Generate summary with transcription (default: false) */
  enableSummary?: boolean
}

/** A timestamped segment of transcribed text */
export interface Segment {
  /** Stable unique identifier */
  id: string

  /** Start time in seconds */
  startTime: number

  /** End time in seconds */
  endTime: number

  /** Transcribed text */
  text: string

  /** Speaker identifier (reference to Speaker.id) */
  speakerId?: string

  /** Confidence score 0-1 if available */
  confidence?: number
}

/** An identified speaker in the transcription */
export interface Speaker {
  /** Unique identifier (e.g., "speaker_1") */
  id: string

  /** Inferred name from context if available */
  name?: string
}

/** Standard output from all transcription providers */
export interface TranscriptionResult {
  /** Complete transcript text */
  text: string

  /** Timestamped segments grouped by speaker */
  segments: Segment[]

  /** Identified speakers */
  speakers: Speaker[]

  /** Total duration in seconds */
  duration?: number

  /** Detected or confirmed language */
  language?: string

  /** Brief summary if requested */
  summary?: string

  /** Which provider produced this result */
  provider: string

  /** Processing time in milliseconds */
  processingTimeMs?: number
}

/** Apply default values to a transcription request */
export function applyDefaults(request: TranscriptionRequest): Required<Omit<TranscriptionRequest, 'mediaUri'>> & Pick<TranscriptionRequest, 'mediaUri'> {
  return {
    mediaUri: request.mediaUri,
    language: request.language ?? 'auto',
    enableDiarization: request.enableDiarization ?? true,
    maxSpeakers: request.maxSpeakers ?? 6,
    enableSummary: request.enableSummary ?? false
  }
}
