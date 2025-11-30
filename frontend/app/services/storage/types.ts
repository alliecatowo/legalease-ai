/**
 * Storage types - shared type definitions for storage abstraction
 *
 * These types mirror the backend storage types for consistency.
 * Both frontend and backend use the same interfaces for interoperability.
 */

/**
 * Supported storage schemes
 */
export type StorageScheme = 'gs' | 's3' | 'https'

/**
 * Parsed storage URI
 */
export interface StorageUri {
  scheme: StorageScheme
  bucket: string
  path: string
  raw: string
}

/**
 * Result from uploading a file
 * Shared structure between frontend and backend for consistency
 */
export interface StorageResult {
  /** Public download URL (https://) */
  downloadUrl: string
  /** Cloud storage URI (gs:// or s3://) */
  storageUri: string
  /** Path within the bucket */
  path: string
  /** File metadata */
  metadata: StorageMetadata
}

/**
 * File metadata
 */
export interface StorageMetadata {
  name: string
  size: number
  contentType: string
  timeCreated?: string
  updated?: string
}

/**
 * Upload progress tracking
 */
export interface UploadProgress {
  bytesTransferred: number
  totalBytes: number
  progress: number
  state: 'running' | 'paused' | 'success' | 'error' | 'canceled'
}

/**
 * Upload options
 */
export interface UploadOptions {
  /** Custom filename (defaults to original) */
  filename?: string
  /** Custom metadata to attach */
  customMetadata?: Record<string, string>
  /** Content type override */
  contentType?: string
}

/**
 * Parse a storage URI into its components
 */
export function parseUri(uri: string): StorageUri {
  // GCS URI: gs://bucket/path
  const gcsMatch = uri.match(/^gs:\/\/([^/]+)\/(.+)$/)
  if (gcsMatch) {
    return {
      scheme: 'gs',
      bucket: gcsMatch[1],
      path: gcsMatch[2],
      raw: uri
    }
  }

  // S3 URI: s3://bucket/path
  const s3Match = uri.match(/^s3:\/\/([^/]+)\/(.+)$/)
  if (s3Match) {
    return {
      scheme: 's3',
      bucket: s3Match[1],
      path: s3Match[2],
      raw: uri
    }
  }

  throw new Error(`Unsupported storage URI format: ${uri}`)
}

/**
 * Build a storage URI from components
 */
export function buildUri(scheme: StorageScheme, bucket: string, path: string): string {
  switch (scheme) {
    case 'gs':
      return `gs://${bucket}/${path}`
    case 's3':
      return `s3://${bucket}/${path}`
    default:
      throw new Error(`Unsupported scheme: ${scheme}`)
  }
}
