import type { TranscriptionProvider } from './provider.js'
import config from '../config.js'

const providers = new Map<string, TranscriptionProvider>()

/**
 * Register a transcription provider
 */
export function registerProvider(provider: TranscriptionProvider): void {
  providers.set(provider.name, provider)
}

/**
 * Get a provider by name, or the configured default
 *
 * Default provider is determined by TRANSCRIPTION_PROVIDER env var.
 * Throws an error if the configured provider is not available.
 */
export function getProvider(name?: string): TranscriptionProvider {
  const providerName = name || config.transcription.defaultProvider

  const provider = providers.get(providerName)
  if (!provider) {
    const available = Array.from(providers.keys()).join(', ')
    throw new Error(
      `Transcription provider '${providerName}' not found. ` +
      `Available providers: ${available || 'none registered'}`
    )
  }

  return provider
}

/**
 * List all registered provider names
 */
export function listProviders(): string[] {
  return Array.from(providers.keys())
}

/**
 * Get the default provider name (from environment config)
 */
export function getDefaultProviderName(): string {
  return config.transcription.defaultProvider
}
