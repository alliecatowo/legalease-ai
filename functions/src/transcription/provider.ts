import type { TranscriptionRequest, TranscriptionResult } from './types.js'

/**
 * Services that must use production (cannot use emulators)
 */
export interface ProductionRequirements {
  /**
   * Storage must be production GCS (not emulator)
   * Example: Chirp/Speech API requires real GCS URIs
   */
  storage: boolean
}

/**
 * Describes what features a provider supports
 */
export interface ProviderCapabilities {
  /** Supports speaker diarization (identifying who said what) */
  diarization: boolean

  /** Supports real-time streaming transcription */
  streaming: boolean

  /** Supports automatic language detection */
  languageDetection: boolean

  /** Number of languages supported */
  languageCount: number

  /** Supports direct URL input (vs requiring GCS/S3 upload) */
  directUrlInput: boolean

  /** Maximum audio duration in seconds (undefined = unlimited) */
  maxDurationSeconds?: number

  /** Supports multimodal input (video with visual context) */
  multimodal: boolean

  /**
   * Services that MUST use production (cannot use emulators)
   * Used for routing decisions in development
   */
  requiresProduction: ProductionRequirements
}

/**
 * Interface that all transcription providers must implement
 */
export interface TranscriptionProvider {
  /** Unique name for this provider (e.g., 'chirp', 'whisper', 'deepgram') */
  readonly name: string

  /** Human-readable display name */
  readonly displayName: string

  /** Provider capabilities for feature detection */
  readonly capabilities: ProviderCapabilities

  /**
   * Check if this provider can handle the given request
   * (e.g., some providers only support certain URI schemes or languages)
   */
  canHandle(request: TranscriptionRequest): boolean

  /**
   * Transcribe media and return standardized result
   */
  transcribe(request: TranscriptionRequest): Promise<TranscriptionResult>
}
