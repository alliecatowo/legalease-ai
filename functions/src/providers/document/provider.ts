/**
 * Document Extraction Provider Interface
 *
 * Defines the contract that all document extraction providers must implement.
 * Follows the same pattern as transcription/provider.ts
 */

import type { ExtractionInput, ExtractionResult, ExtractionStatus } from './types.js'

/**
 * Describes what features a provider supports
 */
export interface ProviderCapabilities {
  /** Outputs bounding boxes for elements */
  boundingBoxes: boolean

  /** Supports async processing with status polling */
  asyncProcessing: boolean

  /** Supports table structure detection */
  tableDetection: boolean

  /** Supports OCR for scanned documents */
  ocr: boolean

  /** Supports multiple languages */
  multiLanguage: boolean

  /** Maximum file size in bytes (undefined = unlimited) */
  maxFileSizeBytes?: number

  /** Maximum page count (undefined = unlimited) */
  maxPages?: number
}

/**
 * Interface that all document extraction providers must implement
 */
export interface DocumentExtractionProvider {
  /** Unique name for this provider (e.g., 'docling', 'surya', 'gemini') */
  readonly name: string

  /** Human-readable display name */
  readonly displayName: string

  /** Provider capabilities for feature detection */
  readonly capabilities: ProviderCapabilities

  /** MIME types this provider can process */
  readonly supportedMimeTypes: string[]

  /**
   * Check if this provider can process the given MIME type
   */
  canProcess(mimeType: string): boolean

  /**
   * Extract document content with bounding boxes
   *
   * Returns either:
   * - ExtractionResult for synchronous processing
   * - ExtractionStatus for async processing (check status.status)
   */
  extract(input: ExtractionInput): Promise<ExtractionResult | ExtractionStatus>

  /**
   * Get status of an async extraction task
   * Only available if capabilities.asyncProcessing is true
   */
  getStatus?(taskId: string): Promise<ExtractionStatus>

  /**
   * Cancel an async extraction task
   * Only available if capabilities.asyncProcessing is true
   */
  cancel?(taskId: string): Promise<void>
}
