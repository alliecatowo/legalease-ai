import { genkit } from 'genkit'
import { googleAI } from '@genkit-ai/google-genai'
import express from 'express'

// Import flows
import { transcribeMedia, TranscriptionInput } from './flows/transcription.js'
import { summarizeTranscript, SummarizationInput } from './flows/summarization.js'

// Initialize Genkit with Google AI plugin
export const ai = genkit({
  plugins: [googleAI()]
})

// Create Express app to expose flows as HTTP endpoints
const app = express()
app.use(express.json())

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'legalease-ai' })
})

// Transcription endpoint
app.post('/transcribe', async (req, res) => {
  try {
    const input = TranscriptionInput.parse(req.body)
    const result = await transcribeMedia(input)
    res.json(result)
  } catch (error) {
    console.error('Transcription error:', error)
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// Summarization endpoint
app.post('/summarize', async (req, res) => {
  try {
    const input = SummarizationInput.parse(req.body)
    const result = await summarizeTranscript(input)
    res.json(result)
  } catch (error) {
    console.error('Summarization error:', error)
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// Start server
const PORT = process.env.PORT || 8080
app.listen(PORT, () => {
  console.log(`LegalEase AI service listening on port ${PORT}`)
})

export { transcribeMedia, summarizeTranscript }
