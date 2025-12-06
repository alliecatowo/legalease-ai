/**
 * Search and Indexing Flows
 *
 * Provides semantic search over document chunks with bounding box support
 * for UI highlighting.
 */

import { z } from 'genkit'
import { QdrantClient } from '@qdrant/js-client-rest'
import { defineSecret } from 'firebase-functions/params'
import { ai } from '../genkit.js'
import { getEmbedder, getModelConfig } from '../ai/index.js'
import config from '../config.js'

// Secrets (used when not using local Qdrant)
const qdrantUrl = defineSecret('QDRANT_URL')
const qdrantApiKey = defineSecret('QDRANT_API_KEY')

/**
 * Get Qdrant client
 *
 * Configuration is controlled by environment variables:
 * - QDRANT_LOCAL=true: Use local Qdrant (http://localhost:6333, no auth)
 * - QDRANT_URL: Override URL (works with both local and cloud)
 * - QDRANT_API_KEY: API key for Qdrant Cloud
 *
 * For cloud Qdrant in production, secrets are loaded via defineSecret()
 */
function getQdrantClient(): QdrantClient {
  if (config.qdrant.isLocal) {
    // Local Qdrant - use config values (env vars or defaults)
    return new QdrantClient({
      url: config.qdrant.url,
      apiKey: config.qdrant.apiKey || undefined
    })
  }
  // Cloud Qdrant - use Secret Manager values
  return new QdrantClient({
    url: qdrantUrl.value(),
    apiKey: qdrantApiKey.value()
  })
}

// Collection name in Qdrant
const COLLECTION_NAME = config.qdrant.collectionName
// Embedding dimension depends on the configured model
// Google text-embedding-004 = 768, OpenAI text-embedding-3-small = 1536
const EMBEDDING_DIMENSION = getModelConfig('embedding').provider === 'google' ? 768 : 1536

// Bbox schema for search results
const BboxSchema = z.object({
  x: z.number(),
  y: z.number(),
  width: z.number(),
  height: z.number(),
  pageNumber: z.number()
})

// Search input schema
export const SearchInput = z.object({
  query: z.string().describe('Search query'),
  caseId: z.string().optional().describe('Filter by case ID'),
  documentId: z.string().optional().describe('Filter by specific document'),
  documentType: z.string().optional().describe('Filter by document type'),
  chunkTypes: z.array(z.enum(['summary', 'section', 'paragraph'])).optional().describe('Filter by chunk types'),
  limit: z.number().default(20).describe('Max results'),
  scoreThreshold: z.number().default(0.5).describe('Minimum similarity score'),
  includeBboxes: z.boolean().default(true).describe('Include bounding boxes in results')
})

export type SearchInputType = z.infer<typeof SearchInput>

// Search result schema with bbox support
const SearchResult = z.object({
  id: z.string().describe('Chunk ID'),
  documentId: z.string().describe('Parent document ID'),
  text: z.string().describe('Matched text content'),
  score: z.number().describe('Similarity score'),
  chunkType: z.enum(['summary', 'section', 'paragraph']).optional(),
  headings: z.array(z.string()).optional().describe('Heading hierarchy for context'),
  bboxes: z.array(BboxSchema).optional().describe('Bounding boxes for highlighting'),
  metadata: z.object({
    filename: z.string().optional(),
    pageNumbers: z.array(z.number()).optional(),
    caseId: z.string().optional(),
    documentType: z.string().optional(),
    elementTypes: z.array(z.string()).optional()
  }).optional()
})

// Search output schema
export const SearchOutput = z.object({
  results: z.array(SearchResult),
  totalFound: z.number(),
  queryEmbeddingTime: z.number().optional(),
  searchTime: z.number().optional()
})

export type SearchOutputType = z.infer<typeof SearchOutput>

// Generate embeddings using configured embedding model
async function generateEmbedding(text: string): Promise<number[]> {
  const response = await ai.embed({
    embedder: getEmbedder(),
    content: text
  })
  // ai.embed returns an array of { embedding: number[], metadata?: Record } objects
  if (Array.isArray(response) && response.length > 0) {
    return response[0].embedding
  }
  throw new Error('Failed to generate embedding')
}

// Search flow with bbox support
export const searchDocumentsFlow = ai.defineFlow(
  {
    name: 'searchDocuments',
    inputSchema: SearchInput,
    outputSchema: SearchOutput
  },
  async (input) => {
    const { query, caseId, documentId, documentType, chunkTypes, limit, scoreThreshold, includeBboxes } = input

    const startTime = Date.now()

    // Generate query embedding
    const queryEmbedding = await generateEmbedding(query)
    const embeddingTime = Date.now() - startTime

    // Initialize Qdrant client (local or cloud based on environment)
    const client = getQdrantClient()

    // Build filter conditions
    const mustConditions: any[] = []

    if (caseId) {
      mustConditions.push({
        key: 'caseId',
        match: { value: caseId }
      })
    }

    if (documentId) {
      mustConditions.push({
        key: 'documentId',
        match: { value: documentId }
      })
    }

    if (documentType) {
      mustConditions.push({
        key: 'documentType',
        match: { value: documentType }
      })
    }

    if (chunkTypes && chunkTypes.length > 0) {
      mustConditions.push({
        key: 'chunkType',
        match: { any: chunkTypes }
      })
    }

    // Search Qdrant
    const searchStart = Date.now()
    const searchResult = await client.search(COLLECTION_NAME, {
      vector: queryEmbedding,
      limit,
      score_threshold: scoreThreshold,
      filter: mustConditions.length > 0 ? { must: mustConditions } : undefined,
      with_payload: true
    })
    const searchTime = Date.now() - searchStart

    // Transform results
    const results = searchResult.map(hit => {
      const payload = hit.payload || {}

      // Parse bboxes from JSON string if present
      let bboxes: any[] | undefined
      if (includeBboxes && payload.bboxesJson) {
        try {
          bboxes = JSON.parse(payload.bboxesJson as string)
        } catch {
          bboxes = undefined
        }
      }

      return {
        id: String(hit.id),
        documentId: payload.documentId as string || '',
        text: payload.text as string || '',
        score: hit.score,
        chunkType: payload.chunkType as 'summary' | 'section' | 'paragraph' | undefined,
        headings: payload.headings as string[] | undefined,
        bboxes,
        metadata: {
          filename: payload.filename as string | undefined,
          pageNumbers: payload.pageNumbers as number[] | undefined,
          caseId: payload.caseId as string | undefined,
          documentType: payload.documentType as string | undefined,
          elementTypes: payload.elementTypes as string[] | undefined
        }
      }
    })

    return {
      results,
      totalFound: results.length,
      queryEmbeddingTime: embeddingTime,
      searchTime
    }
  }
)

// Chunk schema for indexing
const ChunkSchema = z.object({
  id: z.string().describe('Unique chunk ID'),
  text: z.string().describe('Chunk text content'),
  type: z.enum(['summary', 'section', 'paragraph']).describe('Chunk type'),
  headings: z.array(z.string()).describe('Heading hierarchy'),
  pageNumbers: z.array(z.number()).describe('Page numbers this chunk spans'),
  elementTypes: z.array(z.string()).describe('Element types in this chunk'),
  bboxesJson: z.string().describe('JSON stringified bounding boxes')
})

// Index document chunks input
export const IndexDocumentChunksInput = z.object({
  documentId: z.string().describe('Firestore document ID'),
  caseId: z.string().nullable().describe('Associated case ID (null for transcriptions)'),
  filename: z.string().optional().describe('Original filename'),
  documentType: z.string().optional().describe('Document type'),
  chunks: z.array(ChunkSchema).describe('Chunks to index')
})

export type IndexDocumentChunksInputType = z.infer<typeof IndexDocumentChunksInput>

// Index document chunks output
export const IndexDocumentChunksOutput = z.object({
  success: z.boolean(),
  indexedCount: z.number(),
  failedCount: z.number(),
  processingTimeMs: z.number()
})

// Index document chunks flow (replaces old indexDocumentFlow)
export const indexDocumentChunksFlow = ai.defineFlow(
  {
    name: 'indexDocumentChunks',
    inputSchema: IndexDocumentChunksInput,
    outputSchema: IndexDocumentChunksOutput
  },
  async (input) => {
    const { documentId, caseId, filename, documentType, chunks } = input
    const startTime = Date.now()

    if (chunks.length === 0) {
      return {
        success: true,
        indexedCount: 0,
        failedCount: 0,
        processingTimeMs: Date.now() - startTime
      }
    }

    // Initialize Qdrant client (local or cloud based on environment)
    const client = getQdrantClient()

    // Ensure collection exists
    try {
      await client.getCollection(COLLECTION_NAME)
    } catch {
      await client.createCollection(COLLECTION_NAME, {
        vectors: {
          size: EMBEDDING_DIMENSION,
          distance: 'Cosine'
        }
      })
    }

    // Process chunks in batches for better performance
    const BATCH_SIZE = 10
    let indexedCount = 0
    let failedCount = 0

    for (let i = 0; i < chunks.length; i += BATCH_SIZE) {
      const batch = chunks.slice(i, i + BATCH_SIZE)

      try {
        // Generate embeddings for all chunks in batch
        const embeddings = await Promise.all(
          batch.map(chunk => generateEmbedding(chunk.text))
        )

        // Prepare points for upsert
        const points = batch.map((chunk, idx) => ({
          id: chunk.id,
          vector: embeddings[idx],
          payload: {
            documentId,
            caseId,
            filename,
            documentType,
            chunkId: chunk.id,
            chunkType: chunk.type,
            text: chunk.text,
            headings: chunk.headings,
            pageNumbers: chunk.pageNumbers,
            elementTypes: chunk.elementTypes,
            bboxesJson: chunk.bboxesJson,
            indexedAt: new Date().toISOString()
          }
        }))

        // Upsert batch
        await client.upsert(COLLECTION_NAME, {
          wait: true,
          points
        })

        indexedCount += batch.length
      } catch (error) {
        console.error(`[indexDocumentChunks] Batch ${i / BATCH_SIZE} failed:`, error)
        failedCount += batch.length
      }
    }

    return {
      success: failedCount === 0,
      indexedCount,
      failedCount,
      processingTimeMs: Date.now() - startTime
    }
  }
)

// Delete document chunks flow (for re-indexing)
export const DeleteDocumentChunksInput = z.object({
  documentId: z.string().describe('Document ID to delete chunks for')
})

export const deleteDocumentChunksFlow = ai.defineFlow(
  {
    name: 'deleteDocumentChunks',
    inputSchema: DeleteDocumentChunksInput,
    outputSchema: z.object({ success: z.boolean(), deletedCount: z.number() })
  },
  async (input) => {
    const { documentId } = input

    // Initialize Qdrant client (local or cloud based on environment)
    const client = getQdrantClient()

    try {
      // Delete all points with matching documentId
      const result = await client.delete(COLLECTION_NAME, {
        filter: {
          must: [{
            key: 'documentId',
            match: { value: documentId }
          }]
        },
        wait: true
      })

      return {
        success: true,
        deletedCount: result.status === 'completed' ? 1 : 0 // Qdrant doesn't return count
      }
    } catch (error) {
      console.error(`[deleteDocumentChunks] Failed for ${documentId}:`, error)
      return { success: false, deletedCount: 0 }
    }
  }
)
