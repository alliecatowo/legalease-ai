import { onCallGenkit } from 'firebase-functions/https'
import { defineSecret } from 'firebase-functions/params'

// Import flows
import { transcribeMediaFlow, TranscriptionInput } from './flows/transcription.js'
import { summarizeTranscriptFlow, SummarizationInput } from './flows/summarization.js'
import { searchDocumentsFlow, indexDocumentFlow, SearchInput, IndexDocumentInput } from './flows/search.js'

// Define secrets
const googleAIApiKey = defineSecret('GOOGLE_GENAI_API_KEY')
const qdrantUrl = defineSecret('QDRANT_URL')
const qdrantApiKey = defineSecret('QDRANT_API_KEY')

// Export flows as Firebase callable functions
export const transcribeMedia = onCallGenkit(
  {
    secrets: [googleAIApiKey],
    // TODO: Add auth policy once Firebase Auth is set up
    // authPolicy: hasClaim('email_verified'),
    cors: true,
    memory: '1GiB',
    timeoutSeconds: 540 // 9 minutes for long transcriptions
  },
  transcribeMediaFlow
)

export const summarizeTranscript = onCallGenkit(
  {
    secrets: [googleAIApiKey],
    cors: true,
    memory: '512MiB',
    timeoutSeconds: 120
  },
  summarizeTranscriptFlow
)

export const searchDocuments = onCallGenkit(
  {
    secrets: [googleAIApiKey, qdrantUrl, qdrantApiKey],
    cors: true,
    memory: '512MiB',
    timeoutSeconds: 60
  },
  searchDocumentsFlow
)

export const indexDocument = onCallGenkit(
  {
    secrets: [googleAIApiKey, qdrantUrl, qdrantApiKey],
    cors: true,
    memory: '512MiB',
    timeoutSeconds: 120
  },
  indexDocumentFlow
)

// Re-export schemas for client-side use
export { TranscriptionInput, SummarizationInput, SearchInput, IndexDocumentInput }
