/**
 * Document Extraction Provider Types
 *
 * These types define the contract for document extraction providers
 * that output bounding boxes for UI highlighting.
 */

/**
 * Normalized bounding box - frontend expects top-left origin, 0-1 coords
 * Matches frontend PDFViewerWithHighlights component expectations
 */
export interface NormalizedBbox {
  /** X coordinate (0 = left, 1 = right) */
  x: number
  /** Y coordinate (0 = top, 1 = bottom) */
  y: number
  /** Width as fraction of page width */
  width: number
  /** Height as fraction of page height */
  height: number
  /** Page number (1-indexed) */
  pageNumber: number
}

/** Element types that can be extracted from documents */
export type ElementType = 'text' | 'heading' | 'table' | 'image' | 'list' | 'code' | 'formula'

/** Structured table data */
export interface TableData {
  /** Table rows as 2D array of cell text */
  rows: string[][]
  /** Markdown representation of the table */
  markdown: string
  /** Number of header rows (default: 1) */
  headerRows?: number
}

/** A single element extracted from a page */
export interface PageElement {
  /** Element type */
  type: ElementType
  /** Text content (or markdown for tables) */
  content: string
  /** Bounding box in normalized coordinates */
  bbox: NormalizedBbox
  /** Reading order index within the page */
  order: number
  /** Heading level (1-6) for heading elements */
  level?: number
  /** Structured table data for table elements */
  tableData?: TableData
}

/** Content extracted from a single page */
export interface PageContent {
  /** Page number (1-indexed) */
  pageNumber: number
  /** Page width in points */
  width: number
  /** Page height in points */
  height: number
  /** Elements on this page in reading order */
  elements: PageElement[]
}

/** Chunk types for hierarchical chunking */
export type ChunkType = 'summary' | 'section' | 'paragraph'

/** A chunk of document content with associated bboxes */
export interface ExtractedChunk {
  /** Unique chunk identifier */
  id: string
  /** Chunk text content */
  text: string
  /** Chunk type (determines embedding strategy) */
  type: ChunkType
  /** All bboxes for elements in this chunk (for highlighting) */
  bboxes: NormalizedBbox[]
  /** Heading hierarchy for context */
  headings: string[]
  /** Metadata about the chunk */
  metadata: {
    /** Page numbers this chunk spans */
    pageNumbers: number[]
    /** Types of elements in this chunk */
    elementTypes: ElementType[]
    /** Character start position in full document text */
    charStart?: number
    /** Character end position in full document text */
    charEnd?: number
  }
}

/** Metadata about the extraction process */
export interface ExtractionMetadata {
  /** Provider name that performed extraction */
  provider: string
  /** Total processing time in milliseconds */
  processingTimeMs: number
  /** Model version used (if applicable) */
  modelVersion?: string
  /** Whether OCR was used */
  usedOcr?: boolean
  /** Detected language */
  language?: string
}

/** Complete extraction result */
export interface ExtractionResult {
  /** Document ID (from Firestore) */
  documentId: string
  /** Original filename */
  filename: string
  /** Document MIME type */
  mimeType: string
  /** Total page count */
  pageCount: number
  /** Full document content */
  content: {
    /** Markdown representation of full document */
    markdown: string
    /** Plain text representation */
    text: string
  }
  /** Per-page content with elements and bboxes */
  pages: PageContent[]
  /** Hierarchical chunks for indexing */
  chunks: ExtractedChunk[]
  /** Extraction metadata */
  metadata: ExtractionMetadata
}

/** Source types for document input */
export interface ExtractionSource {
  /** Source type */
  type: 'gcs' | 'base64' | 'url'
  /** URI for gcs or url types */
  uri?: string
  /** Base64 encoded data for base64 type */
  data?: string
  /** MIME type (required for base64) */
  mimeType?: string
}

/** Options for extraction */
export interface ExtractionOptions {
  /** Specific pages to extract (1-indexed), omit for all pages */
  pages?: number[]
  /** Skip OCR for digital-native PDFs (faster) */
  skipOcr?: boolean
  /** Skip table structure detection */
  skipTableStructure?: boolean
  /** Hint language code (BCP-47) */
  language?: string
  /** Timeout in milliseconds */
  timeout?: number
}

/** Input for extraction */
export interface ExtractionInput {
  /** Document source */
  source: ExtractionSource
  /** Firestore document ID */
  documentId: string
  /** Original filename */
  filename: string
  /** Extraction options */
  options?: ExtractionOptions
}

/** Status for async extraction operations */
export type ExtractionStatus =
  | { status: 'pending'; taskId: string; progress?: number }
  | { status: 'processing'; taskId: string; progress?: number }
  | { status: 'completed'; result: ExtractionResult }
  | { status: 'failed'; error: string; code?: string }

/** Configuration for Docling provider */
export interface DoclingConfig {
  /** Cloud Run service URL */
  serviceUrl: string
  /** Request timeout in milliseconds */
  timeout: number
  /** Skip OCR by default */
  skipOcr: boolean
  /** Skip table structure detection by default */
  skipTableStructure: boolean
}

/** Configuration for Surya provider (future) */
export interface SuryaConfig {
  /** Service URL */
  serviceUrl: string
  /** Request timeout in milliseconds */
  timeout: number
}

/** Configuration for Gemini provider (future) */
export interface GeminiConfig {
  /** Model ID */
  model: string
  /** Request bounding boxes in output */
  requestBboxes: boolean
}

/** Chunking configuration */
export interface ChunkingConfig {
  /** Maximum tokens per chunk */
  maxTokensPerChunk: number
  /** Overlap tokens between chunks */
  overlapTokens: number
  /** Respect heading boundaries */
  respectHeadings: boolean
  /** Keep tables in single chunks */
  preserveTables: boolean
}

/** Full extraction configuration */
export interface ExtractionConfig {
  /** Active provider name */
  provider: 'docling' | 'surya' | 'gemini'
  /** Docling-specific config */
  docling?: DoclingConfig
  /** Surya-specific config (future) */
  surya?: SuryaConfig
  /** Gemini-specific config (future) */
  gemini?: GeminiConfig
  /** Chunking configuration */
  chunking: ChunkingConfig
}
