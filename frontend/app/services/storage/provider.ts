/**
 * Frontend storage provider interface
 *
 * All storage providers (Firebase, S3, etc.) must implement this interface.
 * Designed for frontend file operations (upload, progress, pause/resume).
 */

import type { StorageScheme, StorageResult, UploadProgress, UploadOptions } from './types'

/**
 * Provider capabilities - describes what a storage provider supports
 */
export interface StorageCapabilities {
  /** Supports resumable uploads */
  resumableUpload: boolean
  /** Supports pause/resume */
  pauseResume: boolean
  /** Supports upload cancellation */
  cancellation: boolean
  /** Maximum file size in bytes (undefined = unlimited) */
  maxFileSize?: number
}

/**
 * Progress callback type
 */
export type ProgressCallback = (progress: UploadProgress) => void

/**
 * Interface that all frontend storage providers must implement
 */
export interface StorageProvider {
  /** Unique name for this provider (e.g., 'firebase', 's3') */
  readonly name: string

  /** Human-readable display name */
  readonly displayName: string

  /** URI scheme this provider produces (e.g., 'gs', 's3') */
  readonly scheme: StorageScheme

  /** Provider capabilities */
  readonly capabilities: StorageCapabilities

  /**
   * Upload a file
   * @param file - File to upload
   * @param path - Destination path (e.g., 'cases/123/files')
   * @param options - Upload options
   */
  upload(file: File, path: string, options?: UploadOptions): Promise<StorageResult>

  /**
   * Set progress callback for current upload
   */
  onProgress(callback: ProgressCallback): void

  /**
   * Cancel the current upload
   */
  cancel(): void

  /**
   * Pause the current upload
   */
  pause(): void

  /**
   * Resume a paused upload
   */
  resume(): void

  /**
   * Get the current upload state
   */
  getState(): UploadProgress | null
}
