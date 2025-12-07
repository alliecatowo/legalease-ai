/**
 * Transcription module - provider-agnostic speech-to-text
 *
 * Usage:
 *   import { transcribe, getProvider, listProviders } from './transcription'
 *
 *   // Use default provider (Chirp)
 *   const result = await transcribe({ mediaUri: 'gs://bucket/audio.mp3' })
 *
 *   // Use specific provider
 *   const result = await transcribe({ mediaUri: '...' }, 'whisper')
 *
 *   // Check provider capabilities
 *   const provider = getProvider('chirp')
 *   if (provider.capabilities.diarization) { ... }
 */

// Re-export types
export type {
  TranscriptionRequest,
  TranscriptionResult,
  Segment,
  Speaker
} from './types.js'

export type {
  TranscriptionProvider,
  ProviderCapabilities,
  ProductionRequirements
} from './provider.js'

export { applyDefaults } from './types.js'

// Re-export registry functions
export {
  registerProvider,
  getProvider,
  listProviders,
  getDefaultProviderName
} from './registry.js'

// Import and register providers
import { registerProvider } from './registry.js'
import { ChirpProvider } from './providers/chirp.js'
import { GeminiProvider } from './providers/gemini.js'

// Register all available providers
// Default is controlled by TRANSCRIPTION_PROVIDER env var (see config.ts)
registerProvider(new ChirpProvider())
registerProvider(new GeminiProvider())

// Future providers:
// import { WhisperProvider } from './providers/whisper.js'
// import { DeepgramProvider } from './providers/deepgram.js'
// registerProvider(new WhisperProvider())
// registerProvider(new DeepgramProvider())

/**
 * Transcribe media using the specified provider (or default)
 */
import { getProvider } from './registry.js'
import type { TranscriptionRequest, TranscriptionResult } from './types.js'

export async function transcribe(
  request: TranscriptionRequest,
  providerName?: string
): Promise<TranscriptionResult> {
  const provider = getProvider(providerName)

  if (!provider.canHandle(request)) {
    throw new Error(
      `Provider '${provider.name}' cannot handle this request. ` +
      `URI scheme or format may not be supported.`
    )
  }

  return provider.transcribe(request)
}
