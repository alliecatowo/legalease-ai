// Shared transcription types - single source of truth

export interface TranscriptSegment {
  id: string // Unique segment identifier
  start: number // seconds (legacy name, maps to startTime)
  end: number // seconds (legacy name, maps to endTime)
  text: string
  speaker?: string // Speaker identifier (maps to speakerId)
  confidence?: number
}

export interface Speaker {
  id: string
  inferredName?: string // Provider-inferred name
  name?: string // User-customized name (frontend only)
  role?: string // User-assigned role (frontend only)
  color?: string // UI color (frontend only)
}

/**
 * Provider capabilities - describes what a transcription provider supports
 */
export interface ProviderCapabilities {
  diarization: boolean // Speaker identification
  streaming: boolean // Real-time transcription
  languageDetection: boolean
  languageCount: number
  directUrlInput: boolean // Can transcribe from URLs directly
  maxDurationSeconds?: number
  multimodal: boolean // Video/visual context support
}

/**
 * Available transcription provider info
 */
export interface ProviderInfo {
  name: string // e.g., 'chirp'
  displayName: string // e.g., 'Google Chirp 3'
  capabilities: ProviderCapabilities
}

export interface TranscriptionInput {
  gcsUri?: string
  url?: string
  language?: string
  enableDiarization?: boolean
  enableSummary?: boolean
  maxSpeakers?: number
  provider?: string // Which provider to use (default: chirp)
}

export interface TranscriptionOutput {
  fullText: string
  segments: TranscriptSegment[]
  speakers: Speaker[]
  duration?: number
  language?: string
  // Detailed summarization output (replaces legacy summary string)
  summarization?: SummarizationOutput
  provider?: string // Which provider was used
}

// Summarization types
export interface SummarizationInput {
  transcript: string
  caseContext?: string
  outputType?: 'brief' | 'detailed' | 'legal'
}

export interface KeyMoment {
  timestamp?: string
  description: string
  importance: 'high' | 'medium' | 'low'
  speakers?: string[]
}

export interface SummarizationOutput {
  summary: string
  keyMoments: KeyMoment[]
  actionItems: string[]
  topics: string[]
  entities?: {
    people?: string[]
    organizations?: string[]
    locations?: string[]
    dates?: string[]
  }
}

// Search types
export interface SearchInput {
  query: string
  caseId?: string
  documentType?: string
  limit?: number
  scoreThreshold?: number
}

export interface SearchResult {
  id: string
  documentId: string
  text: string
  score: number
  metadata?: {
    filename?: string
    pageNumber?: number
    caseId?: string
    documentType?: string
  }
}

export interface SearchOutput {
  results: SearchResult[]
  totalFound: number
  queryEmbeddingTime?: number
  searchTime?: number
}

export interface IndexDocumentInput {
  documentId: string
  text: string
  caseId?: string
  filename?: string
  documentType?: string
  pageNumber?: number
}

// Waveform types
export interface WaveformInput {
  gcsUri: string
  samplesPerPeak?: number
  targetPeaks?: number
}

export interface WaveformOutput {
  peaks: number[]
  duration?: number
  sampleRate?: number
}
