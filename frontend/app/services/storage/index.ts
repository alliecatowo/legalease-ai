/**
 * Frontend storage module - provider-agnostic cloud storage operations
 *
 * Usage:
 *   import { createStorageProvider } from '~/services/storage'
 *
 *   const provider = createStorageProvider(storage, userId)
 *   const result = await provider.upload(file, 'cases/123/files')
 */

// Re-export types
export type {
  StorageScheme,
  StorageUri,
  StorageResult,
  StorageMetadata,
  UploadProgress,
  UploadOptions
} from './types'

export { parseUri, buildUri } from './types'

export type {
  StorageProvider,
  StorageCapabilities,
  ProgressCallback
} from './provider'

// Provider implementations
export { FirebaseStorageProvider } from './providers/firebase'

// Factory function to create the appropriate provider
import type { FirebaseStorage } from 'firebase/storage'
import type { StorageProvider } from './provider'
import { FirebaseStorageProvider } from './providers/firebase'

/**
 * Create a storage provider instance
 *
 * Currently defaults to Firebase, but can be extended to support other providers
 * based on configuration or environment.
 *
 * @param storage - Firebase Storage instance
 * @param userId - Current user's ID for metadata
 * @param providerName - Optional provider name override (future use)
 */
export function createStorageProvider(
  storage: FirebaseStorage,
  userId: string,
  _providerName?: string
): StorageProvider {
  // For now, always use Firebase
  // In the future, this could check config/env to use S3, etc.
  return new FirebaseStorageProvider(storage, userId)
}
