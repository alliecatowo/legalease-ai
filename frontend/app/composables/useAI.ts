import { httpsCallable } from 'firebase/functions'
import type {
  TranscriptionInput,
  TranscriptionOutput,
  SummarizationInput,
  SummarizationOutput,
  SearchInput,
  SearchOutput,
  IndexDocumentInput,
  WaveformInput,
  WaveformOutput
} from '~/types/transcription'

// Re-export types for convenience
export type {
  TranscriptionInput,
  TranscriptionOutput,
  SummarizationInput,
  SummarizationOutput,
  SearchInput,
  SearchOutput,
  IndexDocumentInput,
  WaveformInput,
  WaveformOutput
}

export function useAI() {
  const { $functions } = useNuxtApp()

  // Helper to check functions availability (moved from top-level to allow SSR)
  function ensureFunctions() {
    if (import.meta.server) throw new Error('AI functions cannot be called on server')
    if (!$functions) throw new Error('Firebase Functions not initialized')
    return $functions
  }

  // All functions use the same $functions instance (emulator-connected in dev)
  const transcribeMedia = async (input: TranscriptionInput): Promise<TranscriptionOutput> => {
    const fn = httpsCallable<TranscriptionInput, TranscriptionOutput>(ensureFunctions(), 'transcribeMedia')
    return (await fn(input)).data
  }

  const summarizeTranscript = async (input: SummarizationInput): Promise<SummarizationOutput> => {
    const fn = httpsCallable<SummarizationInput, SummarizationOutput>(ensureFunctions(), 'summarizeTranscript')
    return (await fn(input)).data
  }

  const searchDocuments = async (input: SearchInput): Promise<SearchOutput> => {
    const fn = httpsCallable<SearchInput, SearchOutput>(ensureFunctions(), 'searchDocuments')
    return (await fn(input)).data
  }

  const indexDocument = async (input: IndexDocumentInput): Promise<{ success: boolean; pointId: string }> => {
    const fn = httpsCallable<IndexDocumentInput, { success: boolean; pointId: string }>(ensureFunctions(), 'indexDocument')
    return (await fn(input)).data
  }

  const generateWaveform = async (input: WaveformInput): Promise<WaveformOutput> => {
    const fn = httpsCallable<WaveformInput, WaveformOutput>(ensureFunctions(), 'generateWaveform')
    return (await fn(input)).data
  }

  return {
    transcribeMedia,
    summarizeTranscript,
    searchDocuments,
    indexDocument,
    generateWaveform
  }
}
