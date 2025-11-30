/**
 * Storage types - shared type definitions for storage abstraction
 *
 * These types are designed to be consistent with frontend storage types
 * to enable seamless interoperability between frontend uploads and backend downloads.
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
 * Result from uploading a file (frontend) or downloading metadata (backend)
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
 * Upload progress tracking (primarily for frontend, but consistent interface)
 */
export interface UploadProgress {
  bytesTransferred: number
  totalBytes: number
  progress: number
  state: 'running' | 'paused' | 'success' | 'error' | 'canceled'
}

/**
 * Parse a storage URI into its components
 *
 * Supports:
 * - gs://bucket/path/to/file (Google Cloud Storage)
 * - s3://bucket/path/to/file (AWS S3)
 * - https://storage.googleapis.com/bucket/path (GCS HTTPS)
 * - https://bucket.s3.amazonaws.com/path (S3 HTTPS)
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

  // GCS HTTPS: https://storage.googleapis.com/bucket/path
  const gcsHttpsMatch = uri.match(/^https:\/\/storage\.googleapis\.com\/([^/]+)\/(.+)$/)
  if (gcsHttpsMatch) {
    return {
      scheme: 'https',
      bucket: gcsHttpsMatch[1],
      path: gcsHttpsMatch[2],
      raw: uri
    }
  }

  // S3 HTTPS: https://bucket.s3.amazonaws.com/path or https://bucket.s3.region.amazonaws.com/path
  const s3HttpsMatch = uri.match(/^https:\/\/([^.]+)\.s3(?:\.[^.]+)?\.amazonaws\.com\/(.+)$/)
  if (s3HttpsMatch) {
    return {
      scheme: 'https',
      bucket: s3HttpsMatch[1],
      path: s3HttpsMatch[2],
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
    case 'https':
      // Default to GCS HTTPS format
      return `https://storage.googleapis.com/${bucket}/${path}`
    default:
      throw new Error(`Unsupported scheme: ${scheme}`)
  }
}
