/**
 * Storage module - provider-agnostic cloud storage operations
 *
 * Usage:
 *   import { download, getSignedUrl, getMetadata } from './storage'
 *
 *   // Download a file (automatically routes to correct provider)
 *   const buffer = await download('gs://bucket/path/to/file.mp3')
 *
 *   // Get a signed URL for temporary access
 *   const url = await getSignedUrl('gs://bucket/path/to/file.mp3', 3600)
 *
 *   // Get file metadata
 *   const meta = await getMetadata('gs://bucket/path/to/file.mp3')
 */

// Re-export types
export type {
  StorageScheme,
  StorageUri,
  StorageResult,
  StorageMetadata,
  UploadProgress
} from './types.js'

export { parseUri, buildUri } from './types.js'

export type {
  StorageProvider,
  StorageCapabilities
} from './provider.js'

// Re-export registry functions
export {
  registerProvider,
  getProvider,
  getProviderForUri,
  listProviders,
  getDefaultProviderName
} from './registry.js'

// Import and register providers
import { registerProvider } from './registry.js'
import { GCSProvider } from './providers/gcs.js'

// Register default providers
registerProvider(new GCSProvider(), true)

// Future providers:
// import { S3Provider } from './providers/s3.js'
// registerProvider(new S3Provider())

// Convenience functions that auto-route to correct provider
import { getProviderForUri } from './registry.js'

/**
 * Download a file from cloud storage
 * Automatically routes to the correct provider based on URI scheme.
 */
export async function download(uri: string): Promise<Buffer> {
  const provider = getProviderForUri(uri)
  return provider.download(uri)
}

/**
 * Generate a signed URL for temporary public access
 * @param uri - Storage URI
 * @param expiresInSeconds - How long the URL should be valid (default: 3600)
 */
export async function getSignedUrl(uri: string, expiresInSeconds?: number): Promise<string> {
  const provider = getProviderForUri(uri)
  return provider.getSignedUrl(uri, expiresInSeconds)
}

/**
 * Get file metadata without downloading
 */
export async function getMetadata(uri: string): Promise<import('./types.js').StorageMetadata> {
  const provider = getProviderForUri(uri)
  return provider.getMetadata(uri)
}

/**
 * Check if a file exists
 */
export async function exists(uri: string): Promise<boolean> {
  const provider = getProviderForUri(uri)
  return provider.exists(uri)
}

/**
 * Delete a file
 */
export async function deleteFile(uri: string): Promise<void> {
  const provider = getProviderForUri(uri)
  return provider.delete(uri)
}
