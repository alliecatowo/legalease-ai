/**
 * AI model selection - capability-based model abstraction
 *
 * Provides getModel() and getEmbedder() functions that return
 * Genkit model/embedder references based on configured capability.
 *
 * NOTE: Uses community Genkit plugins (genkitx-anthropic, genkitx-openai)
 * as there are no official @genkit-ai packages for these providers.
 * Community packages may lag behind latest API releases.
 *
 * For Google models, uses official @genkit-ai/google-genai which supports
 * any model via googleAI.model('model-id').
 *
 * TODO: Update when genkitx packages add GPT-5, Opus 4.5, Haiku 4.5
 */

import { googleAI } from '@genkit-ai/google-genai'
import {
  claude45Sonnet,
  claude4Opus,
  claude4Sonnet
} from 'genkitx-anthropic'
import {
  gpt4o,
  gpt4oMini,
  gpt41,
  gpt41Mini,
  gpt41Nano,
  o3,
  o3Mini,
  o4Mini,
  textEmbedding3Large,
  textEmbedding3Small
} from 'genkitx-openai'

import type { ModelCapability, ModelProvider } from './types.js'
import { getModelConfig } from './config.js'
import { PROVIDER_CAPABILITIES } from './types.js'

/**
 * Anthropic model mappings
 * Available via genkitx-anthropic@0.26.0
 *
 * Missing from package: claude-4.5-opus, claude-4.5-haiku (newest Nov 2025)
 */
const ANTHROPIC_MODELS: Record<string, any> = {
  // Claude 4.5 Sonnet (available)
  'claude-4-5-sonnet': claude45Sonnet,
  'claude-sonnet-4-5-20241022': claude45Sonnet,

  // Claude 4 series
  'claude-4-sonnet': claude4Sonnet,
  'claude-sonnet-4-20250514': claude4Sonnet,
  'claude-4-opus': claude4Opus,
  'claude-opus-4-20250514': claude4Opus
}

/**
 * OpenAI model mappings
 * Available via genkitx-openai@0.26.0
 *
 * Missing from package: gpt-5, gpt-5-pro (newest Aug 2025)
 */
const OPENAI_MODELS: Record<string, any> = {
  // GPT-4.1 series
  'gpt-4.1': gpt41,
  'gpt-4.1-mini': gpt41Mini,
  'gpt-4.1-nano': gpt41Nano,

  // GPT-4o series
  'gpt-4o': gpt4o,
  'gpt-4o-mini': gpt4oMini,

  // Reasoning models (o-series)
  'o3': o3,
  'o3-mini': o3Mini,
  'o4-mini': o4Mini
}

/**
 * OpenAI embedder mappings
 */
const OPENAI_EMBEDDERS: Record<string, any> = {
  'text-embedding-3-large': textEmbedding3Large,
  'text-embedding-3-small': textEmbedding3Small
}

/**
 * Get a text generation model by capability
 *
 * Usage:
 *   const model = getModel('standard')  // Uses configured standard model
 *   const model = getModel('reasoning') // Uses configured reasoning model
 *   const model = getModel('fast')      // Uses configured fast model
 *
 * Configuration via environment:
 *   MODEL_STANDARD=anthropic:claude-4-sonnet
 *   MODEL_REASONING=openai:o3
 *   MODEL_FAST=google:gemini-2.0-flash
 */
export function getModel(capability: Exclude<ModelCapability, 'embedding'> = 'standard') {
  const config = getModelConfig(capability)
  const { provider, modelId } = config

  switch (provider) {
    case 'google':
      // Google AI supports dynamic model creation
      return googleAI.model(modelId)

    case 'anthropic':
      // Anthropic uses predefined model references
      const anthropicModel = ANTHROPIC_MODELS[modelId]
      if (!anthropicModel) {
        console.warn(`Unknown Anthropic model: ${modelId}, falling back to claude-4-sonnet`)
        return claude4Sonnet
      }
      return anthropicModel

    case 'openai':
      // OpenAI uses predefined model references
      const openaiModel = OPENAI_MODELS[modelId]
      if (!openaiModel) {
        console.warn(`Unknown OpenAI model: ${modelId}, falling back to gpt-4.1`)
        return gpt41
      }
      return openaiModel

    default:
      throw new Error(`Unknown provider: ${provider}`)
  }
}

/**
 * Get an embedding model
 *
 * Note: Embeddings should stay consistent - changing requires re-indexing
 * your entire vector store.
 *
 * Configuration via environment:
 *   MODEL_EMBEDDING=google:text-embedding-004
 *   MODEL_EMBEDDING=openai:text-embedding-3-small
 */
export function getEmbedder() {
  const config = getModelConfig('embedding')
  const { provider, modelId } = config

  // Check provider supports embeddings
  if (!PROVIDER_CAPABILITIES[provider].embedding) {
    throw new Error(`Provider ${provider} does not support embeddings`)
  }

  switch (provider) {
    case 'google':
      // Google AI supports dynamic embedder creation
      return googleAI.embedder(modelId)

    case 'openai':
      // OpenAI uses predefined embedder references
      const openaiEmbedder = OPENAI_EMBEDDERS[modelId]
      if (!openaiEmbedder) {
        console.warn(`Unknown OpenAI embedder: ${modelId}, falling back to text-embedding-3-small`)
        return textEmbedding3Small
      }
      return openaiEmbedder

    case 'anthropic':
      // Anthropic doesn't have embeddings
      throw new Error('Anthropic does not provide embedding models')

    default:
      throw new Error(`Unknown provider: ${provider}`)
  }
}

/**
 * Get the current model configuration summary (for logging/debugging)
 */
export function getModelSummary(): Record<string, string> {
  return {
    reasoning: formatConfig(getModelConfig('reasoning')),
    standard: formatConfig(getModelConfig('standard')),
    fast: formatConfig(getModelConfig('fast')),
    embedding: formatConfig(getModelConfig('embedding'))
  }
}

function formatConfig(config: { provider: string; modelId: string }): string {
  return `${config.provider}:${config.modelId}`
}
