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
import { HttpsError } from 'firebase-functions/https'
import { ai } from '../genkit.js'
import config from '../config.js'
import {
  authorizeDocument,
  assertStoragePathOwned,
  resolveActor,
  type AuthorizedDocument
} from '../security/access.js'
import { extractDocument } from '../providers/document/index.js'
import type { ExtractionResult, ExtractedChunk } from '../providers/document/types.js'

// Input schema
export const ExtractDocumentInput = z.object({
  documentId: z.string().describe('Firestore document ID'),
  gcsUri: z.string().optional().describe('Ignored for authorization; the source is always derived from the document record'),
  filename: z.string().optional().describe('Original filename (taken from the document record)'),
  caseId: z.string().nullable().optional().describe('Must match the document record if provided'),
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
  doc: AuthorizedDocument,
  filename: string,
  chunks: ExtractedChunk[]
): Promise<void> {
  // Import the refactored index flow
  const { indexChunksForOwner } = await import('./search.js')

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
  // Owner/team/case come from the verified document record
  await indexChunksForOwner(
    { userId: doc.userId, teamId: doc.teamId },
    { documentId: doc.documentId, caseId: doc.caseId, filename, chunks: indexChunks }
  )
}

/**
 * Run extraction for a document whose record has already been authorized
 * (either by the callable wrapper below or by the Firestore trigger).
 * The source file is always derived from the record's own storagePath, which
 * must live under the owner's documents/{uid}/ prefix.
 */
export async function runExtraction(
  doc: AuthorizedDocument,
  options: ExtractDocumentInputType['options']
): Promise<ExtractDocumentOutputType> {
  const input = {
    documentId: doc.documentId,
    caseId: doc.caseId ?? '',
    filename: doc.filename ?? doc.documentId,
    gcsUri: `gs://${config.storageBucket}/${assertStoragePathOwned(doc.storagePath, doc)}`,
    options
  }
  return runExtractionUnchecked(input)
}

async function runExtractionUnchecked(input: {
  documentId: string
  caseId: string
  filename: string
  gcsUri: string
  options?: ExtractDocumentInputType['options']
}): Promise<ExtractDocumentOutputType> {
  const startTime = Date.now()
  const db = getFirestore()
  const docRef = db.doc(`documents/${input.documentId}`)

  try {
    await docRef.update({
      extractionStatus: 'extracting',
      extractionStartedAt: FieldValue.serverTimestamp()
    })

    const doc = await authorizeOwnerRecord(input.documentId)

    const extraction = await extractDocument({
      documentId: input.documentId,
      filename: input.filename,
      source: { type: 'gcs', uri: input.gcsUri },
      options: input.options
    })

    await storeExtractionResult(input.documentId, input.caseId, extraction)

    if (!input.options?.skipIndexing) {
      await indexChunksInQdrant(doc, input.filename, extraction.chunks)
    }

    const processingTimeMs = Date.now() - startTime
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

/** Re-read the record as its owner (used for the indexing owner fields). */
async function authorizeOwnerRecord(documentId: string): Promise<AuthorizedDocument> {
  const snap = await getFirestore().doc(`documents/${documentId}`).get()
  const data = snap.data()
  if (!snap.exists || !data || typeof data.userId !== 'string') {
    throw new Error('Document record missing owner')
  }
  return {
    documentId,
    collection: 'documents',
    userId: data.userId,
    teamId: typeof data.teamId === 'string' ? data.teamId : null,
    caseId: typeof data.caseId === 'string' ? data.caseId : null,
    filename: typeof data.filename === 'string' ? data.filename : null,
    storagePath: typeof data.storagePath === 'string' ? data.storagePath : null
  }
}

/**
 * Document Extraction Flow (client-callable)
 *
 * The caller must be able to access the document; caseId/gcsUri/filename from
 * the client are never trusted and must agree with the Firestore record.
 */
export const extractDocumentFlow = ai.defineFlow(
  {
    name: 'extractDocument',
    inputSchema: ExtractDocumentInput,
    outputSchema: ExtractDocumentOutput
  },
  async (input, { context }) => {
    const db = getFirestore()
    const actor = await resolveActor(db, context)
    const doc = await authorizeDocument(db, actor, input.documentId)
    if (doc.collection !== 'documents') {
      throw new HttpsError('invalid-argument', 'Only documents can be extracted')
    }
    if (input.caseId != null && input.caseId !== doc.caseId) {
      throw new HttpsError('permission-denied', 'caseId does not match the document')
    }
    const gcsUri = `gs://${config.storageBucket}/${assertStoragePathOwned(doc.storagePath, doc)}`
    if (input.gcsUri != null && input.gcsUri !== gcsUri) {
      throw new HttpsError('permission-denied', 'gcsUri does not match the document')
    }
    return runExtraction(doc, input.options)
  }
)
