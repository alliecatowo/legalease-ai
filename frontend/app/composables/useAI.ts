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

  if (!$functions) {
    throw new Error('Firebase Functions not initialized')
  }

  // All functions use the same $functions instance (emulator-connected in dev)
  const transcribeMedia = async (input: TranscriptionInput): Promise<TranscriptionOutput> => {
    const fn = httpsCallable<TranscriptionInput, TranscriptionOutput>($functions, 'transcribeMedia')
    return (await fn(input)).data
  }

  const summarizeTranscript = async (input: SummarizationInput): Promise<SummarizationOutput> => {
    const fn = httpsCallable<SummarizationInput, SummarizationOutput>($functions, 'summarizeTranscript')
    return (await fn(input)).data
  }

  const searchDocuments = async (input: SearchInput): Promise<SearchOutput> => {
    const fn = httpsCallable<SearchInput, SearchOutput>($functions, 'searchDocuments')
    return (await fn(input)).data
  }

  const indexDocument = async (input: IndexDocumentInput): Promise<{ success: boolean; pointId: string }> => {
    const fn = httpsCallable<IndexDocumentInput, { success: boolean; pointId: string }>($functions, 'indexDocument')
    return (await fn(input)).data
  }

  const generateWaveform = async (input: WaveformInput): Promise<WaveformOutput> => {
    const fn = httpsCallable<WaveformInput, WaveformOutput>($functions, 'generateWaveform')
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
