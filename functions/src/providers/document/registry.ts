/**
 * Document Extraction Provider Registry
 *
 * Manages registration and retrieval of document extraction providers.
 * Follows the same pattern as transcription/registry.ts
 */

import type { DocumentExtractionProvider } from './provider.js'

const providers = new Map<string, DocumentExtractionProvider>()
let defaultProvider: DocumentExtractionProvider | null = null

/**
 * Register a document extraction provider
 * The first registered provider becomes the default
 */
export function registerProvider(provider: DocumentExtractionProvider): void {
  providers.set(provider.name, provider)
  if (!defaultProvider) {
    defaultProvider = provider
  }
}

/**
 * Get a provider by name, or the default if no name specified
 */
export function getProvider(name?: string): DocumentExtractionProvider {
  if (name) {
    const provider = providers.get(name)
    if (!provider) {
      throw new Error(`Document extraction provider '${name}' not found. Available: ${Array.from(providers.keys()).join(', ')}`)
    }
    return provider
  }

  if (!defaultProvider) {
    throw new Error('No document extraction providers registered')
  }

  return defaultProvider
}

/**
 * Get a provider that can handle the given MIME type
 */
export function getProviderForMimeType(mimeType: string): DocumentExtractionProvider | null {
  // First try the default provider
  if (defaultProvider?.canProcess(mimeType)) {
    return defaultProvider
  }

  // Fall back to any provider that supports this MIME type
  for (const provider of providers.values()) {
    if (provider.canProcess(mimeType)) {
      return provider
    }
  }

  return null
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

/**
 * Check if a provider is registered
 */
export function hasProvider(name: string): boolean {
  return providers.has(name)
}

/**
 * Clear all registered providers (useful for testing)
 */
export function clearProviders(): void {
  providers.clear()
  defaultProvider = null
}
