import { getFunctions, httpsCallable } from 'firebase/functions'
import type {
  TranscriptionInput,
  TranscriptionOutput,
  SummarizationInput,
  SummarizationOutput,
  SearchInput,
  SearchOutput,
  IndexDocumentInput
} from '~/types/transcription'

// Re-export types for convenience
export type {
  TranscriptionInput,
  TranscriptionOutput,
  SummarizationInput,
  SummarizationOutput,
  SearchInput,
  SearchOutput,
  IndexDocumentInput
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

  const searchDocuments = async (input: SearchInput): Promise<SearchOutput> => {
    if (!$firebase) {
      throw new Error('Firebase not initialized')
    }

    const functions = getFunctions($firebase, 'us-central1')
    const search = httpsCallable<SearchInput, SearchOutput>(
      functions,
      'searchDocuments'
    )

    const result = await search(input)
    return result.data
  }

  const indexDocument = async (input: IndexDocumentInput): Promise<{ success: boolean; pointId: string }> => {
    if (!$firebase) {
      throw new Error('Firebase not initialized')
    }

    const functions = getFunctions($firebase, 'us-central1')
    const index = httpsCallable<IndexDocumentInput, { success: boolean; pointId: string }>(
      functions,
      'indexDocument'
    )

    const result = await index(input)
    return result.data
  }

  return {
    transcribeMedia,
    summarizeTranscript,
    searchDocuments,
    indexDocument
  }
}
