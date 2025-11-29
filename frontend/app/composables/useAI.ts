import { getFunctions, httpsCallable } from 'firebase/functions'

// Types for transcription
export interface TranscriptionInput {
  gcsUri?: string
  url?: string
  language?: string
  enableDiarization?: boolean
  enableSummary?: boolean
}

export interface TranscriptSegment {
  start: number
  end: number
  text: string
  speaker?: string
  confidence?: number
}

export interface Speaker {
  id: string
  inferredName?: string
}

export interface TranscriptionOutput {
  fullText: string
  segments: TranscriptSegment[]
  speakers: Speaker[]
  duration?: number
  language?: string
  summary?: string
}

// Types for summarization
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

export function useAI() {
  const { $firebase } = useNuxtApp()

  const transcribeMedia = async (input: TranscriptionInput): Promise<TranscriptionOutput> => {
    if (!$firebase) {
      throw new Error('Firebase not initialized')
    }

    const functions = getFunctions($firebase, 'us-central1')
    const transcribe = httpsCallable<TranscriptionInput, TranscriptionOutput>(
      functions,
      'transcribeMedia'
    )

    const result = await transcribe(input)
    return result.data
  }

  const summarizeTranscript = async (input: SummarizationInput): Promise<SummarizationOutput> => {
    if (!$firebase) {
      throw new Error('Firebase not initialized')
    }

    const functions = getFunctions($firebase, 'us-central1')
    const summarize = httpsCallable<SummarizationInput, SummarizationOutput>(
      functions,
      'summarizeTranscript'
    )

    const result = await summarize(input)
    return result.data
  }

  return {
    transcribeMedia,
    summarizeTranscript
  }
}
