/**
 * AI model types - capability-based model abstraction
 *
 * Inspired by Dify's model categorization approach.
 * Models are selected by capability rather than provider.
 */

/**
 * Model capability categories
 *
 * - reasoning: Complex multi-step thinking (o1, Claude Opus, Gemini Pro)
 * - standard: General-purpose tasks (GPT-4o, Claude Sonnet, Gemini Flash)
 * - fast: Quick, cheap operations (GPT-4o-mini, Claude Haiku, Gemini Flash 8B)
 * - embedding: Vector representations for search
 */
export type ModelCapability = 'reasoning' | 'standard' | 'fast' | 'embedding'

/**
 * Supported AI model providers
 */
export type ModelProvider = 'google' | 'anthropic' | 'openai'

/**
 * Model configuration for a specific capability
 */
export interface ModelConfig {
  provider: ModelProvider
  modelId: string
  maxTokens?: number
  temperature?: number
}

/**
 * Provider capabilities - what each provider supports
 */
export interface ProviderCapabilities {
  text: boolean
  embedding: boolean
  vision: boolean
}

/**
 * Known provider capabilities
 */
export const PROVIDER_CAPABILITIES: Record<ModelProvider, ProviderCapabilities> = {
  google: { text: true, embedding: true, vision: true },
  anthropic: { text: true, embedding: false, vision: true },
  openai: { text: true, embedding: true, vision: true }
}
