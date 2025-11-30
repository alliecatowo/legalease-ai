import type { TranscriptionProvider } from './provider.js'

const providers = new Map<string, TranscriptionProvider>()
let defaultProvider: TranscriptionProvider | null = null

/**
 * Register a transcription provider
 * The first registered provider becomes the default
 */
export function registerProvider(provider: TranscriptionProvider): void {
  providers.set(provider.name, provider)
  if (!defaultProvider) {
    defaultProvider = provider
  }
}

/**
 * Get a provider by name, or the default if no name specified
 */
export function getProvider(name?: string): TranscriptionProvider {
  if (name) {
    const provider = providers.get(name)
    if (!provider) {
      throw new Error(`Transcription provider '${name}' not found. Available: ${Array.from(providers.keys()).join(', ')}`)
    }
    return provider
  }

  if (!defaultProvider) {
    throw new Error('No transcription providers registered')
  }

  return defaultProvider
}

/**
 * List all registered provider names
 */
export function listProviders(): string[] {
  return Array.from(providers.keys())
}

/**
 * Get the default provider name
 */
export function getDefaultProviderName(): string | null {
  return defaultProvider?.name ?? null
}
