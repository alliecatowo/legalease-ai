import { genkit } from 'genkit'
import { googleAI } from '@genkit-ai/google-genai'
import { enableFirebaseTelemetry } from '@genkit-ai/firebase'

// Enable Firebase telemetry for tracing/logging
enableFirebaseTelemetry()

// Initialize Genkit with Google AI plugin
export const ai = genkit({
  plugins: [googleAI()],
  model: googleAI.model('gemini-2.5-flash')
})
