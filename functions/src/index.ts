import { onCallGenkit } from 'firebase-functions/https'
import { defineSecret } from 'firebase-functions/params'

// Import flows
import { transcribeMediaFlow, TranscriptionInput } from './flows/transcription.js'
import { summarizeTranscriptFlow, SummarizationInput } from './flows/summarization.js'

// Define the API key secret
const googleAIApiKey = defineSecret('GOOGLE_GENAI_API_KEY')

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
    // TODO: Add auth policy once Firebase Auth is set up
    cors: true,
    memory: '512MiB',
    timeoutSeconds: 120
  },
  summarizeTranscriptFlow
)

// Re-export schemas for client-side use
export { TranscriptionInput, SummarizationInput }
