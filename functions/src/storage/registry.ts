/**
 * Storage provider registry
 *
 * Manages registered storage providers and routes URIs to the correct provider.
 */

import type { StorageProvider } from './provider.js'

const providers: Map<string, StorageProvider> = new Map()
let defaultProviderName: string | null = null

/**
 * Register a storage provider
 * @param provider - The provider to register
 * @param isDefault - Whether this should be the default provider
 */
export function registerProvider(provider: StorageProvider, isDefault: boolean = false): void {
  providers.set(provider.name, provider)

  if (isDefault || providers.size === 1) {
    defaultProviderName = provider.name
  }

  console.log(`[Storage] Registered provider: ${provider.displayName} (${provider.scheme}://)`)
}

/**
 * Get a provider by name
 * @param name - Provider name (e.g., 'gcs', 's3')
 * @throws Error if provider not found
 */
export function getProvider(name?: string): StorageProvider {
  if (name) {
    const provider = providers.get(name)
    if (!provider) {
      throw new Error(`Storage provider '${name}' not found. Available: ${listProviders().join(', ')}`)
    }
    return provider
  }

  // Return default provider
  if (!defaultProviderName) {
    throw new Error('No storage providers registered')
  }

  return providers.get(defaultProviderName)!
}

/**
 * Get a provider that can handle the given URI
 * @param uri - Storage URI (e.g., 'gs://bucket/path', 's3://bucket/path')
 * @throws Error if no provider can handle the URI
 */
export function getProviderForUri(uri: string): StorageProvider {
  for (const provider of providers.values()) {
    if (provider.canHandle(uri)) {
      return provider
    }
  }

  throw new Error(`No storage provider can handle URI: ${uri}`)
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
  return defaultProviderName
}
