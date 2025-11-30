// Shared transcription types - single source of truth

export interface TranscriptSegment {
  id: string     // Unique segment identifier
  start: number  // seconds
  end: number    // seconds
  text: string
  speaker?: string
  confidence?: number
}

export interface Speaker {
  id: string
  inferredName?: string
}

export interface TranscriptionInput {
  gcsUri?: string
  url?: string
  language?: string
  enableDiarization?: boolean
  enableSummary?: boolean
}

export interface TranscriptionOutput {
  fullText: string
  segments: TranscriptSegment[]
  speakers: Speaker[]
  duration?: number
  language?: string
  summary?: string
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
