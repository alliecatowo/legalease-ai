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
  type Timestamp,
  type QueryConstraint
} from 'firebase/firestore'

// Case types for Firestore
export interface CaseDoc {
  id?: string
  name: string
  caseNumber: string
  client: string
  matterType?: string
  description?: string
  status: 'active' | 'staging' | 'unloaded' | 'archived'
  // Ownership
  userId: string
  teamId?: string
  // Counts (denormalized for performance)
  documentCount?: number
  transcriptionCount?: number
  // Timestamps
  createdAt?: Timestamp
  updatedAt?: Timestamp
}

export interface CaseCreateInput {
  name: string
  caseNumber: string
  client: string
  matterType?: string
  description?: string
  teamId?: string
}

export interface CaseUpdateInput {
  name?: string
  caseNumber?: string
  client?: string
  matterType?: string
  description?: string
  status?: CaseDoc['status']
}

export function useCases() {
  const { $firestore } = useNuxtApp()
  const { user } = useAuth()
  const { currentTeam } = useTeam()

  // Reactive state
  const cases = ref<CaseDoc[]>([])
  const currentCase = ref<CaseDoc | null>(null)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)

  /**
   * Create a new case
   */
  async function createCase(data: CaseCreateInput): Promise<string> {
    if (import.meta.server) throw new Error('Cannot create case on server')
    if (!$firestore) throw new Error('Firestore not initialized')
    if (!user.value) throw new Error('User must be authenticated')

    const casesRef = collection($firestore, 'cases')
    const docRef = await addDoc(casesRef, {
      ...data,
      status: 'active',
      userId: user.value.uid,
      teamId: data.teamId || currentTeam.value?.id || null,
      documentCount: 0,
      transcriptionCount: 0,
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp()
    })

    return docRef.id
  }

  /**
   * Get a case by ID
   */
  async function getCase(id: string): Promise<CaseDoc | null> {
    if (import.meta.server) return null
    if (!$firestore) throw new Error('Firestore not initialized')

    const docRef = doc($firestore, 'cases', id)
    const docSnap = await getDoc(docRef)

    if (!docSnap.exists()) return null

    return {
      id: docSnap.id,
      ...docSnap.data()
    } as CaseDoc
  }

  /**
   * List cases for current user or team
   */
  async function listCases(options: {
    teamId?: string
    status?: CaseDoc['status']
    limitCount?: number
  } = {}): Promise<CaseDoc[]> {
    if (import.meta.server) return []
    if (!$firestore) throw new Error('Firestore not initialized')
    if (!user.value) throw new Error('User must be authenticated')

    isLoading.value = true
    error.value = null

    try {
      const constraints: QueryConstraint[] = []

      // Filter by team or user
      if (options.teamId || currentTeam.value?.id) {
        constraints.push(where('teamId', '==', options.teamId || currentTeam.value?.id))
      } else {
        // Personal cases only
        constraints.push(where('userId', '==', user.value.uid))
      }

      if (options.status) {
        constraints.push(where('status', '==', options.status))
      }

      constraints.push(orderBy('createdAt', 'desc'))

      if (options.limitCount) {
        constraints.push(limit(options.limitCount))
      }

      const casesRef = collection($firestore, 'cases')
      const q = query(casesRef, ...constraints)
      const querySnapshot = await getDocs(q)

      const result = querySnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      })) as CaseDoc[]

      cases.value = result
      return result
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to list cases')
      throw error.value
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update a case
   */
  async function updateCase(id: string, data: CaseUpdateInput): Promise<void> {
    if (import.meta.server) return
    if (!$firestore) throw new Error('Firestore not initialized')

    const docRef = doc($firestore, 'cases', id)
    await updateDoc(docRef, {
      ...data,
      updatedAt: serverTimestamp()
    })

    // Update local state if this is the current case
    if (currentCase.value?.id === id) {
      currentCase.value = { ...currentCase.value, ...data }
    }

    // Update in list
    const index = cases.value.findIndex(c => c.id === id)
    if (index !== -1) {
      cases.value[index] = { ...cases.value[index], ...data }
    }
  }

  /**
   * Delete a case
   */
  async function deleteCase(id: string): Promise<void> {
    if (import.meta.server) return
    if (!$firestore) throw new Error('Firestore not initialized')

    const docRef = doc($firestore, 'cases', id)
    await deleteDoc(docRef)

    // Remove from local state
    cases.value = cases.value.filter(c => c.id !== id)
    if (currentCase.value?.id === id) {
      currentCase.value = null
    }
  }

  /**
   * Subscribe to real-time updates for a case
   */
  function subscribeToCase(
    id: string,
    callback: (data: CaseDoc | null) => void
  ): () => void {
    if (!$firestore) {
      callback(null)
      return () => {}
    }

    const docRef = doc($firestore, 'cases', id)
    return onSnapshot(docRef, (docSnap) => {
      if (!docSnap.exists()) {
        callback(null)
        return
      }
      const data = {
        id: docSnap.id,
        ...docSnap.data()
      } as CaseDoc
      currentCase.value = data
      callback(data)
    })
  }

  /**
   * Subscribe to real-time updates for cases list
   */
  function subscribeToCases(
    options: { teamId?: string } = {},
    callback?: (data: CaseDoc[]) => void
  ): () => void {
    if (!$firestore || !user.value) {
      return () => {}
    }

    const constraints: QueryConstraint[] = []

    if (options.teamId || currentTeam.value?.id) {
      constraints.push(where('teamId', '==', options.teamId || currentTeam.value?.id))
    } else {
      constraints.push(where('userId', '==', user.value.uid))
    }

    constraints.push(orderBy('createdAt', 'desc'))

    const casesRef = collection($firestore, 'cases')
    const q = query(casesRef, ...constraints)

    return onSnapshot(q, (querySnapshot) => {
      const result = querySnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      })) as CaseDoc[]

      cases.value = result
      callback?.(result)
    })
  }

  /**
   * Increment document count for a case
   */
  async function incrementDocumentCount(caseId: string, delta: number = 1): Promise<void> {
    if (import.meta.server) return
    if (!$firestore) throw new Error('Firestore not initialized')

    const caseDoc = await getCase(caseId)
    if (!caseDoc) throw new Error('Case not found')

    // TODO: Use FieldValue.increment() for proper atomic increments
    await updateCase(caseId, {})

    // For now, we'll refetch to get the updated count
    // In production, use FieldValue.increment()
  }

  /**
   * Archive a case
   */
  async function archiveCase(id: string): Promise<void> {
    await updateCase(id, { status: 'archived' })
  }

  /**
   * Restore an archived case
   */
  async function restoreCase(id: string): Promise<void> {
    await updateCase(id, { status: 'active' })
  }

  return {
    // State
    cases,
    currentCase,
    isLoading,
    error,
    // Methods
    createCase,
    getCase,
    listCases,
    updateCase,
    deleteCase,
    subscribeToCase,
    subscribeToCases,
    archiveCase,
    restoreCase
  }
}
