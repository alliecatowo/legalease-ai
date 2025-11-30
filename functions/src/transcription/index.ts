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
  ProviderCapabilities
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

// Register default providers
registerProvider(new ChirpProvider())

// Future providers:
// import { WhisperProvider } from './providers/whisper.js'
// import { DeepgramProvider } from './providers/deepgram.js'
// import { GeminiProvider } from './providers/gemini.js'  // Multimodal!
// registerProvider(new WhisperProvider())
// registerProvider(new DeepgramProvider())
// registerProvider(new GeminiProvider())

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
