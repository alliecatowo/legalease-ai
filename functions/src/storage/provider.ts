/**
 * Storage provider interface
 *
 * All storage providers (GCS, S3, etc.) must implement this interface.
 * Designed for backend file operations (download, signed URLs, metadata).
 */

import type { StorageScheme, StorageMetadata } from './types.js'

/**
 * Provider capabilities - describes what a storage provider supports
 */
export interface StorageCapabilities {
  /** Supports resumable uploads */
  resumableUpload: boolean
  /** Supports signed URLs for temporary access */
  signedUrls: boolean
  /** Supports streaming downloads */
  streaming: boolean
  /** Maximum file size in bytes (undefined = unlimited) */
  maxFileSize?: number
}

/**
 * Interface that all storage providers must implement
 */
export interface StorageProvider {
  /** Unique name for this provider (e.g., 'gcs', 's3') */
  readonly name: string

  /** Human-readable display name */
  readonly displayName: string

  /** URI scheme this provider handles (e.g., 'gs', 's3') */
  readonly scheme: StorageScheme

  /** Provider capabilities */
  readonly capabilities: StorageCapabilities

  /**
   * Check if this provider can handle the given URI
   */
  canHandle(uri: string): boolean

  /**
   * Download a file to memory
   */
  download(uri: string): Promise<Buffer>

  /**
   * Generate a signed URL for temporary public access
   * @param uri - Storage URI
   * @param expiresInSeconds - How long the URL should be valid (default: 3600)
   */
  getSignedUrl(uri: string, expiresInSeconds?: number): Promise<string>

  /**
   * Get file metadata without downloading
   */
  getMetadata(uri: string): Promise<StorageMetadata>

  /**
   * Check if a file exists
   */
  exists(uri: string): Promise<boolean>

  /**
   * Delete a file
   */
  delete(uri: string): Promise<void>
}
