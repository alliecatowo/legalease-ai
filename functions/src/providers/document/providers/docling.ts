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
import { isEmulator } from '../../../config.js'
import { download as downloadFromStorage } from '../../../storage/index.js'
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

// Pages can be an array or object keyed by page number
type DoclingPages = DoclingPage[] | Record<string, { size: { width: number; height: number } }>

interface DoclingDocument {
  pages: DoclingPages
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
   * Returns either a source object (for /v1/convert/source) or a Buffer (for /v1/convert/file)
   */
  private async prepareSource(input: ExtractionInput): Promise<
    | { type: 'source'; data: { kind: string; url?: string } }
    | { type: 'file'; data: Buffer; filename: string }
  > {
    switch (input.source.type) {
      case 'gcs': {
        // In emulator mode, download directly and use file upload
        // (signed URLs don't work without service account credentials)
        if (isEmulator()) {
          console.log('[Docling] Emulator mode: downloading file for direct upload')
          const buffer = await downloadFromStorage(input.source.uri!)
          return { type: 'file', data: buffer, filename: input.filename }
        }
        // Production: generate a signed URL that Docling can fetch
        const signedUrl = await this.generateSignedUrl(input.source.uri!)
        return { type: 'source', data: { kind: 'http', url: signedUrl } }
      }
      case 'url': {
        return { type: 'source', data: { kind: 'http', url: input.source.uri! } }
      }
      case 'base64': {
        // Convert base64 to buffer for file upload
        const buffer = Buffer.from(input.source.data!, 'base64')
        return { type: 'file', data: buffer, filename: input.filename }
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
   * Uses service account authentication via ID token (production only)
   */
  private async callDocling(
    source: { type: 'source'; data: { kind: string; url?: string } } | { type: 'file'; data: Buffer; filename: string },
    options?: ExtractionInput['options']
  ): Promise<DoclingConvertResponse> {
    // In emulator mode, call local Docling without authentication
    // In production, get ID token for Cloud Run authentication
    let authHeaders: Record<string, string> = {}
    if (!isEmulator()) {
      const client = await this.auth.getIdTokenClient(this.config.serviceUrl)
      authHeaders = await client.getRequestHeaders()
    }

    const controller = new AbortController()
    const timeout = options?.timeout || this.config.timeout
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
      let response: Response

      if (source.type === 'file') {
        // Use multipart file upload endpoint
        const formData = new FormData()
        const blob = new Blob([source.data])
        formData.append('files', blob, source.filename)
        formData.append('to_formats', 'json')
        formData.append('to_formats', 'md')
        formData.append('do_ocr', String(!options?.skipOcr && !this.config.skipOcr))
        formData.append('do_table_structure', String(!options?.skipTableStructure && !this.config.skipTableStructure))

        response = await fetch(`${this.config.serviceUrl}/v1/convert/file`, {
          method: 'POST',
          headers: authHeaders,
          body: formData,
          signal: controller.signal
        })
      } else {
        // Use source URL endpoint
        const requestBody = {
          sources: [source.data],
          options: {
            do_ocr: !options?.skipOcr && !this.config.skipOcr,
            do_table_structure: !options?.skipTableStructure && !this.config.skipTableStructure,
            return_as_file: false,
            include_md: true
          }
        }

        response = await fetch(`${this.config.serviceUrl}/v1/convert/source`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...authHeaders
          },
          body: JSON.stringify(requestBody),
          signal: controller.signal
        })
      }

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Docling API error (${response.status}): ${errorText}`)
      }

      const rawResult = await response.json()

      // Normalize response format - file endpoint has different structure
      let result: DoclingConvertResponse
      if (source.type === 'file') {
        // File endpoint: { document: { json_content, md_content }, status, ... }
        const fileResult = rawResult as {
          document: { json_content?: DoclingDocument; md_content?: string }
          status: string
          errors?: Array<{ message: string }>
        }
        if (fileResult.errors?.length) {
          throw new Error(`Docling extraction failed: ${fileResult.errors[0].message}`)
        }
        if (!fileResult.document.json_content) {
          throw new Error('Docling returned no document content')
        }
        result = {
          document: fileResult.document.json_content,
          md: fileResult.document.md_content
        }
      } else {
        // Source endpoint: { document, md, status, error }
        result = rawResult as DoclingConvertResponse
        if (result.error) {
          throw new Error(`Docling extraction failed: ${result.error}`)
        }
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
    // Build page dimensions map - handle both array and object formats
    const pageDimensions = new Map<number, { width: number; height: number }>()
    if (Array.isArray(doc.pages)) {
      for (const page of doc.pages) {
        pageDimensions.set(page.page_no, { width: page.size.width, height: page.size.height })
      }
    } else {
      // Object format: { "1": { size: {...} }, "2": { size: {...} } }
      for (const [pageNo, page] of Object.entries(doc.pages)) {
        pageDimensions.set(parseInt(pageNo, 10), { width: page.size.width, height: page.size.height })
      }
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
      pageCount: Array.isArray(doc.pages) ? doc.pages.length : Object.keys(doc.pages).length,
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
