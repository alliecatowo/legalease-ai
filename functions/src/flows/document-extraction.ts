/**
 * Document Extraction Flow
 *
 * Orchestrates document extraction, storage, and indexing:
 * 1. Extract document using configured provider (Docling)
 * 2. Store pages and chunks in Firestore subcollections
 * 3. Index chunks in Qdrant vector store
 */

import { z } from 'genkit'
import { getFirestore, FieldValue } from 'firebase-admin/firestore'
import { ai } from '../genkit.js'
import { extractDocument } from '../providers/document/index.js'
import type { ExtractionResult, ExtractedChunk } from '../providers/document/types.js'

// Input schema
export const ExtractDocumentInput = z.object({
  documentId: z.string().describe('Firestore document ID'),
  gcsUri: z.string().describe('GCS URI of the document (gs://...)'),
  filename: z.string().describe('Original filename'),
  caseId: z.string().describe('Associated case ID'),
  options: z.object({
    skipOcr: z.boolean().optional().describe('Skip OCR for digital-native PDFs'),
    skipTableStructure: z.boolean().optional().describe('Skip table structure detection'),
    skipIndexing: z.boolean().optional().describe('Skip Qdrant indexing')
  }).optional()
})

export type ExtractDocumentInputType = z.infer<typeof ExtractDocumentInput>

// Output schema
export const ExtractDocumentOutput = z.object({
  success: z.boolean(),
  documentId: z.string(),
  pageCount: z.number(),
  chunkCount: z.number(),
  processingTimeMs: z.number(),
  error: z.string().optional()
})

export type ExtractDocumentOutputType = z.infer<typeof ExtractDocumentOutput>

/**
 * Store extraction result in Firestore
 */
async function storeExtractionResult(
  documentId: string,
  caseId: string,
  extraction: ExtractionResult
): Promise<void> {
  const db = getFirestore()

  // Update main document with extraction status
  await db.doc(`documents/${documentId}`).update({
    status: 'indexed',
    extractionStatus: 'completed',
    pageCount: extraction.pageCount,
    chunkCount: extraction.chunks.length,
    extractedAt: FieldValue.serverTimestamp(),
    extraction: {
      provider: extraction.metadata.provider,
      processingTimeMs: extraction.metadata.processingTimeMs,
      usedOcr: extraction.metadata.usedOcr || false,
      language: extraction.metadata.language || null
    },
    // Store markdown summary for quick access
    markdownPreview: extraction.content.markdown.substring(0, 5000)
  })

  // Store pages subcollection (for PDF viewer highlighting)
  // Batch writes in groups of 500 (Firestore limit)
  const BATCH_SIZE = 500
  let batch = db.batch()
  let batchCount = 0

  for (const page of extraction.pages) {
    const pageRef = db.doc(`documents/${documentId}/pages/page-${page.pageNumber}`)
    batch.set(pageRef, {
      pageNumber: page.pageNumber,
      width: page.width,
      height: page.height,
      elementCount: page.elements.length,
      // Store elements with truncated content for large documents
      elements: page.elements.map(el => ({
        type: el.type,
        content: el.content.substring(0, 500),
        bbox: el.bbox,
        order: el.order,
        level: el.level || null
      }))
    })

    batchCount++
    if (batchCount >= BATCH_SIZE) {
      await batch.commit()
      batch = db.batch()
      batchCount = 0
    }
  }

  // Store chunks subcollection
  for (const chunk of extraction.chunks) {
    const chunkRef = db.doc(`documents/${documentId}/chunks/${chunk.id}`)
    batch.set(chunkRef, {
      id: chunk.id,
      type: chunk.type,
      text: chunk.text.substring(0, 10000), // Firestore field limit
      bboxes: chunk.bboxes,
      headings: chunk.headings,
      pageNumbers: chunk.metadata.pageNumbers,
      elementTypes: chunk.metadata.elementTypes,
      createdAt: FieldValue.serverTimestamp()
    })

    batchCount++
    if (batchCount >= BATCH_SIZE) {
      await batch.commit()
      batch = db.batch()
      batchCount = 0
    }
  }

  // Commit remaining writes
  if (batchCount > 0) {
    await batch.commit()
  }
}

/**
 * Index chunks in Qdrant vector store
 */
async function indexChunksInQdrant(
  documentId: string,
  caseId: string,
  filename: string,
  chunks: ExtractedChunk[]
): Promise<void> {
  // Import the refactored index flow
  const { indexDocumentChunksFlow } = await import('./search.js')

  // Prepare chunks for indexing
  const indexChunks = chunks.map(chunk => ({
    id: chunk.id,
    text: chunk.text,
    type: chunk.type,
    headings: chunk.headings,
    pageNumbers: chunk.metadata.pageNumbers,
    elementTypes: chunk.metadata.elementTypes,
    bboxesJson: JSON.stringify(chunk.bboxes)
  }))

  // Call the index flow
  await indexDocumentChunksFlow({
    documentId,
    caseId,
    filename,
    chunks: indexChunks
  })
}

/**
 * Document Extraction Flow
 */
export const extractDocumentFlow = ai.defineFlow(
  {
    name: 'extractDocument',
    inputSchema: ExtractDocumentInput,
    outputSchema: ExtractDocumentOutput
  },
  async (input) => {
    const startTime = Date.now()
    const db = getFirestore()
    const docRef = db.doc(`documents/${input.documentId}`)

    try {
      // Update status to extracting
      await docRef.update({
        extractionStatus: 'extracting',
        extractionStartedAt: FieldValue.serverTimestamp()
      })

      console.log(`[extractDocument] Starting extraction for ${input.documentId}`)

      // 1. Extract document
      const extraction = await extractDocument({
        documentId: input.documentId,
        filename: input.filename,
        source: { type: 'gcs', uri: input.gcsUri },
        options: input.options
      })

      console.log(`[extractDocument] Extracted ${extraction.pageCount} pages, ${extraction.chunks.length} chunks`)

      // 2. Store in Firestore
      await storeExtractionResult(input.documentId, input.caseId, extraction)
      console.log(`[extractDocument] Stored extraction result in Firestore`)

      // 3. Index chunks in Qdrant (unless skipped)
      if (!input.options?.skipIndexing) {
        await indexChunksInQdrant(
          input.documentId,
          input.caseId,
          input.filename,
          extraction.chunks
        )
        console.log(`[extractDocument] Indexed ${extraction.chunks.length} chunks in Qdrant`)
      }

      const processingTimeMs = Date.now() - startTime
      console.log(`[extractDocument] Completed in ${processingTimeMs}ms`)

      return {
        success: true,
        documentId: input.documentId,
        pageCount: extraction.pageCount,
        chunkCount: extraction.chunks.length,
        processingTimeMs
      }

    } catch (error: any) {
      const processingTimeMs = Date.now() - startTime
      console.error(`[extractDocument] Failed for ${input.documentId}:`, error)

      // Update document with failure status
      await docRef.update({
        status: 'failed',
        extractionStatus: 'failed',
        extractionError: error.message || 'Unknown extraction error',
        extractionFailedAt: FieldValue.serverTimestamp()
      })

      return {
        success: false,
        documentId: input.documentId,
        pageCount: 0,
        chunkCount: 0,
        processingTimeMs,
        error: error.message || 'Unknown extraction error'
      }
    }
  }
)
