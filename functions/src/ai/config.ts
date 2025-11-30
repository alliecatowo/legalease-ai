/**
 * AI model configuration
 *
 * Default models for each capability, with environment variable overrides.
 * Format for env override: "provider:modelId"
 *
 * Example:
 *   MODEL_STANDARD=anthropic:claude-sonnet-4-20250514
 *   MODEL_REASONING=openai:o1-preview
 */

import type { ModelCapability, ModelConfig, ModelProvider } from './types.js'

/**
 * Default model assignments per capability
 * These are used when no environment override is set
 */
const DEFAULT_MODELS: Record<ModelCapability, ModelConfig> = {
  reasoning: { provider: 'google', modelId: 'gemini-2.5-pro' },
  standard: { provider: 'google', modelId: 'gemini-2.5-flash' },
  fast: { provider: 'google', modelId: 'gemini-2.0-flash' },
  embedding: { provider: 'google', modelId: 'text-embedding-004' }
}

/**
 * Parse a model configuration string
 * Format: "provider:modelId"
 */
function parseModelString(value: string): ModelConfig | null {
  const colonIndex = value.indexOf(':')
  if (colonIndex === -1) {
    console.warn(`Invalid model config format: "${value}". Expected "provider:modelId"`)
    return null
  }

  const provider = value.substring(0, colonIndex) as ModelProvider
  const modelId = value.substring(colonIndex + 1)

  if (!['google', 'anthropic', 'openai'].includes(provider)) {
    console.warn(`Unknown provider: "${provider}". Using default.`)
    return null
  }

  return { provider, modelId }
}

/**
 * Get the model configuration for a capability
 *
 * Checks for environment variable override first:
 *   MODEL_REASONING, MODEL_STANDARD, MODEL_FAST, MODEL_EMBEDDING
 *
 * Falls back to DEFAULT_MODELS if not set
 */
export function getModelConfig(capability: ModelCapability): ModelConfig {
  const envKey = `MODEL_${capability.toUpperCase()}`
  const envValue = process.env[envKey]

  if (envValue) {
    const parsed = parseModelString(envValue)
    if (parsed) {
      return parsed
    }
  }

  return DEFAULT_MODELS[capability]
}

/**
 * List all configured models (for debugging/logging)
 */
export function listModelConfigs(): Record<ModelCapability, ModelConfig> {
  return {
    reasoning: getModelConfig('reasoning'),
    standard: getModelConfig('standard'),
    fast: getModelConfig('fast'),
    embedding: getModelConfig('embedding')
  }
}
