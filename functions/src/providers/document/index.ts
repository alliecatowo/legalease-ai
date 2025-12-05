/**
 * Document Extraction Provider Public API
 *
 * Usage:
 * ```typescript
 * import { extractDocument, getProvider } from './providers/document'
 *
 * const result = await extractDocument({
 *   documentId: 'doc123',
 *   filename: 'contract.pdf',
 *   source: { type: 'gcs', uri: 'gs://bucket/path/contract.pdf' }
 * })
 * ```
 */

// Re-export types
export type {
  NormalizedBbox,
  ElementType,
  TableData,
  PageElement,
  PageContent,
  ChunkType,
  ExtractedChunk,
  ExtractionMetadata,
  ExtractionResult,
  ExtractionSource,
  ExtractionOptions,
  ExtractionInput,
  ExtractionStatus,
  DoclingConfig,
  SuryaConfig,
  GeminiConfig,
  ChunkingConfig,
  ExtractionConfig
} from './types.js'

// Re-export provider interface
export type { DocumentExtractionProvider, ProviderCapabilities } from './provider.js'

// Re-export bbox utilities
export {
  fromDoclingBbox,
  fromPyMuPdfBbox,
  mergeBboxes,
  sortByReadingOrder,
  bboxesOverlap,
  calculateOverlap,
  expandBbox,
  type DoclingBbox,
  type PyMuPdfBbox
} from './bbox-utils.js'

// Re-export chunking
export { chunkDocument } from './chunking.js'

// Re-export registry functions
export {
  registerProvider,
  getProvider,
  getProviderForMimeType,
  listProviders,
  getDefaultProviderName,
  hasProvider,
  clearProviders
} from './registry.js'

// Re-export Docling provider
export { DoclingProvider, createDoclingProvider } from './providers/docling.js'

// Import for initialization
import { registerProvider } from './registry.js'
import { createDoclingProvider } from './providers/docling.js'
import type { ExtractionInput, ExtractionResult, ExtractionConfig, DoclingConfig } from './types.js'
import appConfig from '../../config.js'

/**
 * Get configuration from environment variables
 * Uses centralized config from ../../config.ts
 */
export function getConfigFromEnv(): ExtractionConfig {
  const provider = (process.env.EXTRACTION_PROVIDER || 'docling') as 'docling' | 'surya' | 'gemini'

  const extractionConfig: ExtractionConfig = {
    provider,
    chunking: {
      maxTokensPerChunk: parseInt(process.env.CHUNKING_MAX_TOKENS || '400', 10),
      overlapTokens: parseInt(process.env.CHUNKING_OVERLAP_TOKENS || '50', 10),
      respectHeadings: process.env.CHUNKING_RESPECT_HEADINGS !== 'false',
      preserveTables: process.env.CHUNKING_PRESERVE_TABLES !== 'false'
    }
  }

  if (provider === 'docling') {
    extractionConfig.docling = {
      serviceUrl: appConfig.docling.serviceUrl,
      timeout: appConfig.docling.timeout,
      skipOcr: appConfig.docling.skipOcr,
      skipTableStructure: appConfig.docling.skipTableStructure
    }
  }

  return extractionConfig
}

/**
 * Initialize providers based on configuration
 */
let initialized = false

export function initializeProviders(config?: ExtractionConfig): void {
  if (initialized) return

  const cfg = config || getConfigFromEnv()

  if (cfg.docling) {
    registerProvider(createDoclingProvider(cfg.docling))
  }

  // Future: Add Surya, Gemini providers here

  initialized = true
}

/**
 * High-level extraction function
 * Automatically initializes providers if not already done
 */
export async function extractDocument(input: ExtractionInput): Promise<ExtractionResult> {
  initializeProviders()

  const { getProvider } = await import('./registry.js')
  const provider = getProvider()

  const result = await provider.extract(input)

  // Handle async status (future use)
  if ('status' in result && result.status !== 'completed') {
    throw new Error(`Async extraction not yet supported. Status: ${result.status}`)
  }

  return result as ExtractionResult
}

/**
 * Check if a MIME type is supported for extraction
 */
export function canExtract(mimeType: string): boolean {
  initializeProviders()

  const { getProviderForMimeType } = require('./registry.js')
  return getProviderForMimeType(mimeType) !== null
}
