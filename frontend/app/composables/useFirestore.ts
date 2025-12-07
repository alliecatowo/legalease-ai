import type {
  Timestamp,
  collection,
  doc,
  addDoc,
  getDoc,
  getDocs,
  updateDoc,
  deleteDoc,
  query,
  where,
  orderBy,
  limit,
  onSnapshot,
  serverTimestamp,
  type QueryConstraint
} from 'firebase/firestore'
import type { TranscriptSegment, Speaker, SummarizationOutput } from '~/types/transcription'

// Transcription document type for Firestore
export interface TranscriptionDoc {
  id?: string
  caseId?: string
  userId: string
  filename: string
  storagePath: string
  gsUri: string
  downloadUrl: string
  mimeType: string
  fileSize: number
  status: 'uploading' | 'processing' | 'completed' | 'failed'
  error?: string
  // Transcription results
  fullText?: string
  segments?: TranscriptSegment[]
  speakers?: Speaker[]
  duration?: number
  language?: string
  // Detailed summarization (replaces legacy summary string)
  summarization?: SummarizationOutput
  // Timestamps
  createdAt?: Timestamp
  updatedAt?: Timestamp
  completedAt?: Timestamp
}

export function useFirestore() {
  const { $firestore } = useNuxtApp()
  const { user } = useAuth()

  /**
   * Create a new transcription document
   */
  async function createTranscription(data: Omit<TranscriptionDoc, 'id' | 'createdAt' | 'updatedAt'>): Promise<string> {
    if (import.meta.server) throw new Error('Cannot create on server')
    if (!$firestore) throw new Error('Firestore not initialized')
    if (!user.value) throw new Error('User must be authenticated')

    // Filter out undefined values - Firestore doesn't allow them
    const cleanData = Object.fromEntries(
      Object.entries(data).filter(([_, v]) => v !== undefined)
    )

    const transcriptionsRef = collection($firestore, 'transcriptions')
    const docRef = await addDoc(transcriptionsRef, {
      ...cleanData,
      userId: user.value.uid,
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp()
    })

    return docRef.id
  }

  /**
   * Get a transcription by ID
   */
  async function getTranscription(id: string): Promise<TranscriptionDoc | null> {
    if (import.meta.server) return null
    if (!$firestore) throw new Error('Firestore not initialized')

    const docRef = doc($firestore, 'transcriptions', id)
    const docSnap = await getDoc(docRef)

    if (!docSnap.exists()) return null

    return {
      id: docSnap.id,
      ...docSnap.data()
    } as TranscriptionDoc
  }

  /**
   * Update a transcription document
   */
  async function updateTranscription(id: string, data: Partial<TranscriptionDoc>): Promise<void> {
    if (import.meta.server) return
    if (!$firestore) throw new Error('Firestore not initialized')

    // Filter out undefined values - Firestore doesn't allow them
    const cleanData = Object.fromEntries(
      Object.entries(data).filter(([_, v]) => v !== undefined)
    )

    const docRef = doc($firestore, 'transcriptions', id)
    await updateDoc(docRef, {
      ...cleanData,
      updatedAt: serverTimestamp()
    })
  }

  /**
   * List transcriptions for a case or user
   */
  async function listTranscriptions(options: {
    caseId?: string
    userId?: string
    status?: TranscriptionDoc['status']
    limitCount?: number
  } = {}): Promise<TranscriptionDoc[]> {
    if (import.meta.server) return []
    if (!$firestore) throw new Error('Firestore not initialized')

    const constraints: QueryConstraint[] = []

    if (options.caseId) {
      constraints.push(where('caseId', '==', options.caseId))
    }

    if (options.userId) {
      constraints.push(where('userId', '==', options.userId))
    } else if (user.value) {
      // Default to current user's transcriptions
      constraints.push(where('userId', '==', user.value.uid))
    }

    if (options.status) {
      constraints.push(where('status', '==', options.status))
    }

    constraints.push(orderBy('createdAt', 'desc'))

    if (options.limitCount) {
      constraints.push(limit(options.limitCount))
    }

    const transcriptionsRef = collection($firestore, 'transcriptions')
    const q = query(transcriptionsRef, ...constraints)
    const querySnapshot = await getDocs(q)

    return querySnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    })) as TranscriptionDoc[]
  }

  /**
   * Subscribe to real-time updates for a transcription
   */
  function subscribeToTranscription(
    id: string,
    callback: (data: TranscriptionDoc | null) => void
  ): () => void {
    if (!$firestore) {
      callback(null)
      return () => {}
    }

    const docRef = doc($firestore, 'transcriptions', id)
    return onSnapshot(docRef, (docSnap) => {
      if (!docSnap.exists()) {
        callback(null)
        return
      }
      callback({
        id: docSnap.id,
        ...docSnap.data()
      } as TranscriptionDoc)
    })
  }

  /**
   * Delete a transcription
   */
  async function deleteTranscription(id: string): Promise<void> {
    if (import.meta.server) return
    if (!$firestore) throw new Error('Firestore not initialized')

    const docRef = doc($firestore, 'transcriptions', id)
    await deleteDoc(docRef)
  }

  /**
   * Mark transcription as completed with results
   */
  async function completeTranscription(
    id: string,
    results: {
      fullText: string
      segments: TranscriptSegment[]
      speakers: Speaker[]
      duration?: number
      language?: string
      summarization?: SummarizationOutput
    }
  ): Promise<void> {
    await updateTranscription(id, {
      status: 'completed',
      ...results,
      completedAt: serverTimestamp() as unknown as Timestamp
    })
  }

  /**
   * Mark transcription as failed
   */
  async function failTranscription(id: string, error: string): Promise<void> {
    await updateTranscription(id, {
      status: 'failed',
      error
    })
  }

  return {
    createTranscription,
    getTranscription,
    updateTranscription,
    listTranscriptions,
    subscribeToTranscription,
    deleteTranscription,
    completeTranscription,
    failTranscription
  }
}
