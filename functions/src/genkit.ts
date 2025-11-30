import { genkit } from 'genkit'
import type { GenkitPlugin, GenkitPluginV2 } from 'genkit/plugin'
import { googleAI } from '@genkit-ai/google-genai'
import { enableFirebaseTelemetry } from '@genkit-ai/firebase'
import { anthropic } from 'genkitx-anthropic'
import { openAI } from 'genkitx-openai'
import { getModel } from './ai/index.js'

// Enable Firebase telemetry for tracing/logging
enableFirebaseTelemetry()

// Build plugins conditionally based on available API keys
// Uses Genkit's official union type: (GenkitPlugin | GenkitPluginV2)[]
const plugins: (GenkitPlugin | GenkitPluginV2)[] = [
  googleAI(),
  // Community plugins only initialize if their API keys are present
  ...(process.env.ANTHROPIC_API_KEY ? [anthropic()] : []),
  ...(process.env.OPENAI_API_KEY ? [openAI()] : [])
]

// Initialize Genkit with available provider plugins
export const ai = genkit({
  plugins,
  // Default model uses the 'standard' capability configuration
  model: getModel('standard')
})
