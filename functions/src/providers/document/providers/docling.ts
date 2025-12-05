/**
 * Docling Document Extraction Provider
 *
 * Connects to docling-serve running on Cloud Run for document extraction
 * with bounding box support.
 *
 * Cloud Run authentication uses service account with IAM invoker role.
 */

import { Storage } from '@google-cloud/storage'
import { GoogleAuth } from 'google-auth-library'
import type { DocumentExtractionProvider, ProviderCapabilities } from '../provider.js'
import type {
  ExtractionInput,
  ExtractionResult,
  DoclingConfig,
  PageContent,
  PageElement,
  ElementType,
  ExtractionMetadata
} from '../types.js'
import { fromDoclingBbox, type DoclingBbox } from '../bbox-utils.js'
import { chunkDocument } from '../chunking.js'

/**
 * Docling API Response Types
 * Based on docling-serve /v1/convert/source response
 */

interface DoclingProvenance {
  page_no: number
  bbox: DoclingBbox
  charspan?: [number, number]
}

interface DoclingTextItem {
  self_ref: string
  parent?: { $ref: string }
  children?: Array<{ $ref: string }>
  label: 'text' | 'section_header' | 'title' | 'caption' | 'list_item' | 'code' | 'formula' | 'paragraph'
  prov: DoclingProvenance[]
  text: string
  level?: number
}

interface DoclingTableCell {
  text: string
  row_span: number
  col_span: number
  start_row_offset_idx: number
  start_col_offset_idx: number
}

interface DoclingTableItem {
  self_ref: string
  prov: DoclingProvenance[]
  data: {
    num_rows: number
    num_cols: number
    table_cells: DoclingTableCell[]
  }
}

interface DoclingPictureItem {
  self_ref: string
  prov: DoclingProvenance[]
  caption?: string
}

interface DoclingPage {
  page_no: number
  size: {
    width: number
    height: number
  }
}

interface DoclingDocument {
  pages: DoclingPage[]
  texts: DoclingTextItem[]
  tables: DoclingTableItem[]
  pictures: DoclingPictureItem[]
  origin?: {
    mimetype: string
    filename: string
  }
  version?: string
}

interface DoclingConvertResponse {
  document: DoclingDocument
  md?: string
  status?: string
  error?: string
}

/**
 * Map Docling label to our ElementType
 */
function mapLabelToType(label: string): ElementType {
  switch (label) {
    case 'section_header':
    case 'title':
      return 'heading'
    case 'list_item':
      return 'list'
    case 'code':
      return 'code'
    case 'formula':
      return 'formula'
    case 'caption':
    case 'text':
    case 'paragraph':
    default:
      return 'text'
  }
}

/**
 * Convert table cells to markdown format
 */
function tableToMarkdown(table: DoclingTableItem): string {
  const { num_rows, num_cols, table_cells } = table.data

  // Build grid
  const grid: string[][] = Array.from({ length: num_rows }, () =>
    Array.from({ length: num_cols }, () => '')
  )

  for (const cell of table_cells) {
    const row = cell.start_row_offset_idx
    const col = cell.start_col_offset_idx
    if (row < num_rows && col < num_cols) {
      grid[row][col] = cell.text.replace(/\|/g, '\\|').replace(/\n/g, ' ')
    }
  }

  // Build markdown
  const lines: string[] = []
  for (let i = 0; i < num_rows; i++) {
    lines.push('| ' + grid[i].join(' | ') + ' |')
    if (i === 0) {
      // Add header separator
      lines.push('| ' + grid[i].map(() => '---').join(' | ') + ' |')
    }
  }

  return lines.join('\n')
}

/**
 * Docling Provider Implementation
 */
export class DoclingProvider implements DocumentExtractionProvider {
  readonly name = 'docling'
  readonly displayName = 'Docling'

  readonly capabilities: ProviderCapabilities = {
    boundingBoxes: true,
    asyncProcessing: false, // Using sync API for now
    tableDetection: true,
    ocr: true,
    multiLanguage: true,
    maxFileSizeBytes: 100 * 1024 * 1024, // 100MB
    maxPages: 500
  }

  readonly supportedMimeTypes = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/html',
    'text/markdown',
    'image/png',
    'image/jpeg',
    'image/tiff'
  ]

  private storage: Storage
  private auth: GoogleAuth

  constructor(private config: DoclingConfig) {
    this.storage = new Storage()
    this.auth = new GoogleAuth()
  }

  canProcess(mimeType: string): boolean {
    return this.supportedMimeTypes.includes(mimeType)
  }

  async extract(input: ExtractionInput): Promise<ExtractionResult> {
    const startTime = Date.now()

    // 1. Prepare source (generate signed URL for GCS)
    const source = await this.prepareSource(input)

    // 2. Call docling-serve
    const response = await this.callDocling(source, input.options)

    // 3. Transform to our format
    return this.transformResult(
      response.document,
      response.md,
      input,
      Date.now() - startTime
    )
  }

  /**
   * Prepare the source for Docling API
   */
  private async prepareSource(input: ExtractionInput): Promise<{ kind: string; url?: string; base64?: string; mime_type?: string }> {
    switch (input.source.type) {
      case 'gcs': {
        // Generate a signed URL that Docling can fetch
        const signedUrl = await this.generateSignedUrl(input.source.uri!)
        return { kind: 'http', url: signedUrl }
      }
      case 'url': {
        return { kind: 'http', url: input.source.uri! }
      }
      case 'base64': {
        return {
          kind: 'base64',
          base64: input.source.data!,
          mime_type: input.source.mimeType
        }
      }
      default:
        throw new Error(`Unsupported source type: ${input.source.type}`)
    }
  }

  /**
   * Generate a signed URL for GCS object
   * Short expiry since Docling fetches immediately
   */
  private async generateSignedUrl(gcsUri: string): Promise<string> {
    // Parse gs:// URI
    const match = gcsUri.match(/^gs:\/\/([^/]+)\/(.+)$/)
    if (!match) {
      throw new Error(`Invalid GCS URI: ${gcsUri}`)
    }

    const [, bucketName, objectPath] = match
    const bucket = this.storage.bucket(bucketName)
    const file = bucket.file(objectPath)

    const [signedUrl] = await file.getSignedUrl({
      version: 'v4',
      action: 'read',
      expires: Date.now() + 5 * 60 * 1000 // 5 minutes
    })

    return signedUrl
  }

  /**
   * Call Docling Cloud Run service
   * Uses service account authentication via ID token
   */
  private async callDocling(
    source: { kind: string; url?: string; base64?: string; mime_type?: string },
    options?: ExtractionInput['options']
  ): Promise<DoclingConvertResponse> {
    // Get ID token for Cloud Run authentication
    const client = await this.auth.getIdTokenClient(this.config.serviceUrl)
    const headers = await client.getRequestHeaders()

    const requestBody = {
      sources: [source],
      options: {
        do_ocr: !options?.skipOcr && !this.config.skipOcr,
        do_table_structure: !options?.skipTableStructure && !this.config.skipTableStructure,
        // Request both document JSON and markdown
        return_as_file: false,
        include_md: true
      }
    }

    const controller = new AbortController()
    const timeout = options?.timeout || this.config.timeout
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
      const response = await fetch(`${this.config.serviceUrl}/v1/convert/source`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...headers
        },
        body: JSON.stringify(requestBody),
        signal: controller.signal
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Docling API error (${response.status}): ${errorText}`)
      }

      const result = await response.json() as DoclingConvertResponse

      if (result.error) {
        throw new Error(`Docling extraction failed: ${result.error}`)
      }

      return result
    } finally {
      clearTimeout(timeoutId)
    }
  }

  /**
   * Transform Docling response to our ExtractionResult format
   */
  private transformResult(
    doc: DoclingDocument,
    markdown: string | undefined,
    input: ExtractionInput,
    processingTimeMs: number
  ): ExtractionResult {
    // Build page dimensions map
    const pageDimensions = new Map<number, { width: number; height: number }>()
    for (const page of doc.pages) {
      pageDimensions.set(page.page_no, { width: page.size.width, height: page.size.height })
    }

    // Transform elements and group by page
    const pageElements = new Map<number, PageElement[]>()
    let elementOrder = 0

    // Process text items
    for (const textItem of doc.texts) {
      for (const prov of textItem.prov) {
        const dims = pageDimensions.get(prov.page_no)
        if (!dims) continue

        const element: PageElement = {
          type: mapLabelToType(textItem.label),
          content: textItem.text,
          bbox: fromDoclingBbox(prov.bbox, dims.width, dims.height, prov.page_no),
          order: elementOrder++,
          level: textItem.level
        }

        const pageElems = pageElements.get(prov.page_no) || []
        pageElems.push(element)
        pageElements.set(prov.page_no, pageElems)
      }
    }

    // Process tables
    for (const table of doc.tables) {
      for (const prov of table.prov) {
        const dims = pageDimensions.get(prov.page_no)
        if (!dims) continue

        const tableMarkdown = tableToMarkdown(table)
        const element: PageElement = {
          type: 'table',
          content: tableMarkdown,
          bbox: fromDoclingBbox(prov.bbox, dims.width, dims.height, prov.page_no),
          order: elementOrder++,
          tableData: {
            rows: this.extractTableRows(table),
            markdown: tableMarkdown,
            headerRows: 1
          }
        }

        const pageElems = pageElements.get(prov.page_no) || []
        pageElems.push(element)
        pageElements.set(prov.page_no, pageElems)
      }
    }

    // Process pictures/images
    for (const picture of doc.pictures) {
      for (const prov of picture.prov) {
        const dims = pageDimensions.get(prov.page_no)
        if (!dims) continue

        const element: PageElement = {
          type: 'image',
          content: picture.caption || '[Image]',
          bbox: fromDoclingBbox(prov.bbox, dims.width, dims.height, prov.page_no),
          order: elementOrder++
        }

        const pageElems = pageElements.get(prov.page_no) || []
        pageElems.push(element)
        pageElements.set(prov.page_no, pageElems)
      }
    }

    // Build PageContent array
    const pages: PageContent[] = []
    for (const [pageNumber, elements] of pageElements.entries()) {
      const dims = pageDimensions.get(pageNumber)!
      // Sort elements by reading order (top-to-bottom, left-to-right)
      elements.sort((a, b) => {
        const yDiff = a.bbox.y - b.bbox.y
        if (Math.abs(yDiff) > 0.02) return yDiff
        return a.bbox.x - b.bbox.x
      })

      pages.push({
        pageNumber,
        width: dims.width,
        height: dims.height,
        elements
      })
    }

    // Sort pages by page number
    pages.sort((a, b) => a.pageNumber - b.pageNumber)

    // Generate chunks with bboxes
    const chunks = chunkDocument(pages, {
      maxTokensPerChunk: 400,
      overlapTokens: 50,
      respectHeadings: true,
      preserveTables: true
    })

    // Build full text from elements
    const fullText = pages
      .flatMap(p => p.elements)
      .map(e => e.content)
      .join('\n\n')

    // Determine if OCR was used (would be in response metadata if available)
    const usedOcr = !this.config.skipOcr

    const metadata: ExtractionMetadata = {
      provider: this.name,
      processingTimeMs,
      modelVersion: doc.version,
      usedOcr
    }

    return {
      documentId: input.documentId,
      filename: input.filename,
      mimeType: doc.origin?.mimetype || 'application/pdf',
      pageCount: doc.pages.length,
      content: {
        markdown: markdown || fullText,
        text: fullText
      },
      pages,
      chunks,
      metadata
    }
  }

  /**
   * Extract table rows as 2D string array
   */
  private extractTableRows(table: DoclingTableItem): string[][] {
    const { num_rows, num_cols, table_cells } = table.data
    const rows: string[][] = Array.from({ length: num_rows }, () =>
      Array.from({ length: num_cols }, () => '')
    )

    for (const cell of table_cells) {
      const row = cell.start_row_offset_idx
      const col = cell.start_col_offset_idx
      if (row < num_rows && col < num_cols) {
        rows[row][col] = cell.text
      }
    }

    return rows
  }
}

/**
 * Create a Docling provider instance
 */
export function createDoclingProvider(config: DoclingConfig): DoclingProvider {
  return new DoclingProvider(config)
}
