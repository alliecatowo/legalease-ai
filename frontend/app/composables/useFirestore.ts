import {
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
  Timestamp,
  type DocumentData,
  type QueryConstraint
} from 'firebase/firestore'

// Transcription types for Firestore
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
  segments?: TranscriptionSegment[]
  speakers?: Speaker[]
  duration?: number
  language?: string
  summary?: string
  // Timestamps
  createdAt?: Timestamp
  updatedAt?: Timestamp
  completedAt?: Timestamp
}

export interface TranscriptionSegment {
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

export function useFirestore() {
  const { $firestore } = useNuxtApp()
  const { user } = useAuth()

  /**
   * Create a new transcription document
   */
  async function createTranscription(data: Omit<TranscriptionDoc, 'id' | 'createdAt' | 'updatedAt'>): Promise<string> {
    if (!$firestore) throw new Error('Firestore not initialized')
    if (!user.value) throw new Error('User must be authenticated')

    const transcriptionsRef = collection($firestore, 'transcriptions')
    const docRef = await addDoc(transcriptionsRef, {
      ...data,
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
    if (!$firestore) throw new Error('Firestore not initialized')

    const docRef = doc($firestore, 'transcriptions', id)
    await updateDoc(docRef, {
      ...data,
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
      segments: TranscriptionSegment[]
      speakers: Speaker[]
      duration?: number
      language?: string
      summary?: string
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
