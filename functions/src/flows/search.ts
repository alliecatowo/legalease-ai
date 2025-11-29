import { z } from 'genkit'
import { googleAI } from '@genkit-ai/google-genai'
import { QdrantClient } from '@qdrant/js-client-rest'
import { defineSecret } from 'firebase-functions/params'
import { ai } from '../genkit.js'

// Secrets
const qdrantUrl = defineSecret('QDRANT_URL')
const qdrantApiKey = defineSecret('QDRANT_API_KEY')

// Collection name in Qdrant
const COLLECTION_NAME = 'legal_documents'
const EMBEDDING_MODEL = 'text-embedding-004'
const EMBEDDING_DIMENSION = 768

// Input schema
export const SearchInput = z.object({
  query: z.string().describe('Search query'),
  caseId: z.string().optional().describe('Filter by case ID'),
  documentType: z.string().optional().describe('Filter by document type'),
  limit: z.number().default(20).describe('Max results'),
  scoreThreshold: z.number().default(0.5).describe('Minimum similarity score')
})

export type SearchInputType = z.infer<typeof SearchInput>

// Search result schema
const SearchResult = z.object({
  id: z.string().describe('Document chunk ID'),
  documentId: z.string().describe('Parent document ID'),
  text: z.string().describe('Matched text content'),
  score: z.number().describe('Similarity score'),
  metadata: z.object({
    filename: z.string().optional(),
    pageNumber: z.number().optional(),
    caseId: z.string().optional(),
    documentType: z.string().optional()
  }).optional()
})

// Output schema
export const SearchOutput = z.object({
  results: z.array(SearchResult),
  totalFound: z.number(),
  queryEmbeddingTime: z.number().optional(),
  searchTime: z.number().optional()
})

export type SearchOutputType = z.infer<typeof SearchOutput>

// Generate embeddings using Gemini
async function generateEmbedding(text: string): Promise<number[]> {
  const response = await ai.embed({
    embedder: googleAI.embedder(EMBEDDING_MODEL),
    content: text
  })
  // ai.embed returns an array of { embedding: number[], metadata?: Record } objects
  // We need to extract the first embedding
  if (Array.isArray(response) && response.length > 0) {
    return response[0].embedding
  }
  throw new Error('Failed to generate embedding')
}

// Search flow
export const searchDocumentsFlow = ai.defineFlow(
  {
    name: 'searchDocuments',
    inputSchema: SearchInput,
    outputSchema: SearchOutput
  },
  async (input) => {
    const { query, caseId, documentType, limit, scoreThreshold } = input

    const startTime = Date.now()

    // Generate query embedding
    const queryEmbedding = await generateEmbedding(query)
    const embeddingTime = Date.now() - startTime

    // Initialize Qdrant client
    const client = new QdrantClient({
      url: qdrantUrl.value(),
      apiKey: qdrantApiKey.value()
    })

    // Build filter conditions
    const mustConditions: any[] = []

    if (caseId) {
      mustConditions.push({
        key: 'caseId',
        match: { value: caseId }
      })
    }

    if (documentType) {
      mustConditions.push({
        key: 'documentType',
        match: { value: documentType }
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
    const results = searchResult.map(hit => ({
      id: String(hit.id),
      documentId: hit.payload?.documentId as string || '',
      text: hit.payload?.text as string || '',
      score: hit.score,
      metadata: {
        filename: hit.payload?.filename as string,
        pageNumber: hit.payload?.pageNumber as number,
        caseId: hit.payload?.caseId as string,
        documentType: hit.payload?.documentType as string
      }
    }))

    return {
      results,
      totalFound: results.length,
      queryEmbeddingTime: embeddingTime,
      searchTime
    }
  }
)

// Index document flow (for adding documents to vector store)
export const IndexDocumentInput = z.object({
  documentId: z.string().describe('Firestore document ID'),
  text: z.string().describe('Document text to index'),
  caseId: z.string().optional(),
  filename: z.string().optional(),
  documentType: z.string().optional(),
  pageNumber: z.number().optional()
})

export const indexDocumentFlow = ai.defineFlow(
  {
    name: 'indexDocument',
    inputSchema: IndexDocumentInput,
    outputSchema: z.object({ success: z.boolean(), pointId: z.string() })
  },
  async (input) => {
    const { documentId, text, caseId, filename, documentType, pageNumber } = input

    // Generate embedding
    const embedding = await generateEmbedding(text)

    // Initialize Qdrant client
    const client = new QdrantClient({
      url: qdrantUrl.value(),
      apiKey: qdrantApiKey.value()
    })

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

    // Generate a unique point ID
    const pointId = `${documentId}_${pageNumber || 0}_${Date.now()}`

    // Upsert point
    await client.upsert(COLLECTION_NAME, {
      wait: true,
      points: [{
        id: pointId,
        vector: embedding,
        payload: {
          documentId,
          text,
          caseId,
          filename,
          documentType,
          pageNumber,
          indexedAt: new Date().toISOString()
        }
      }]
    })

    return { success: true, pointId }
  }
)
