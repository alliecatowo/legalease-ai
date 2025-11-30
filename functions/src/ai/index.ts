/**
 * AI module - capability-based model abstraction
 *
 * Provides a Dify-inspired model selection interface that chooses models
 * by capability (reasoning, standard, fast, embedding) rather than provider.
 *
 * Usage:
 *   import { getModel, getEmbedder } from '../ai/index.js'
 *
 *   // Get a model by capability
 *   const response = await ai.generate({
 *     model: getModel('standard'),  // Uses configured standard model
 *     prompt: '...'
 *   })
 *
 *   // Get an embedder
 *   const embedding = await ai.embed({
 *     embedder: getEmbedder(),  // Uses configured embedding model
 *     content: '...'
 *   })
 *
 * Configuration via environment variables:
 *   MODEL_REASONING=google:gemini-2.5-pro
 *   MODEL_STANDARD=anthropic:claude-3-5-sonnet
 *   MODEL_FAST=google:gemini-2.0-flash
 *   MODEL_EMBEDDING=google:text-embedding-004
 */

// Types
export type { ModelCapability, ModelProvider, ModelConfig } from './types.js'
export { PROVIDER_CAPABILITIES } from './types.js'

// Configuration
export { getModelConfig, listModelConfigs } from './config.js'

// Model selection (plugins are conditionally loaded in genkit.ts)
export { getModel, getEmbedder, getModelSummary } from './models.js'
