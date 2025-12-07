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
  increment,
  type QueryConstraint
} from 'firebase/firestore'
import { ref as storageRef, uploadBytesResumable, getDownloadURL, deleteObject } from 'firebase/storage'

// Document types for Firestore
export interface DocumentDoc {
  id?: string
  caseId: string
  filename: string
  title?: string
  storagePath: string
  downloadUrl: string
  mimeType: string
  fileSize: number
  documentType?: 'contract' | 'agreement' | 'transcript' | 'court_filing' | 'general'
  status: 'uploading' | 'processing' | 'indexed' | 'completed' | 'failed'
  // Metadata
  summary?: string
  pageCount?: number
  extractedText?: string
  // Ownership
  userId: string
  teamId?: string
  // Timestamps
  createdAt?: Timestamp
  updatedAt?: Timestamp
}

export interface DocumentCreateInput {
  caseId: string
  filename: string
  title?: string
  mimeType: string
  fileSize: number
  documentType?: DocumentDoc['documentType']
}

export interface DocumentUploadProgress {
  bytesTransferred: number
  totalBytes: number
  progress: number
  state: 'running' | 'paused' | 'success' | 'canceled' | 'error'
}

export function useDocuments() {
  const { $firestore, $storage } = useNuxtApp()
  const { user } = useAuth()
  const { currentTeam } = useTeam()

  // Reactive state
  const documents = ref<DocumentDoc[]>([])
  const currentDocument = ref<DocumentDoc | null>(null)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  const uploadProgress = ref<DocumentUploadProgress | null>(null)

  /**
   * Upload a document to Firebase Storage and create Firestore record
   */
  async function uploadDocument(
    caseId: string,
    file: File,
    options: {
      documentType?: DocumentDoc['documentType']
      title?: string
      onProgress?: (progress: DocumentUploadProgress) => void
    } = {}
  ): Promise<string> {
    if (import.meta.server) throw new Error('Cannot upload on server')
    if (!$firestore || !$storage) throw new Error('Firebase not initialized')
    if (!user.value) throw new Error('User must be authenticated')

    const userId = user.value.uid
    const timestamp = Date.now()
    const safeName = file.name.replace(/[^a-zA-Z0-9.-]/g, '_')
    const path = `documents/${userId}/${caseId}/${timestamp}_${safeName}`

    // Upload to Storage
    const fileRef = storageRef($storage, path)
    const uploadTask = uploadBytesResumable(fileRef, file)

    return new Promise((resolve, reject) => {
      uploadTask.on(
        'state_changed',
        (snapshot) => {
          const progress: DocumentUploadProgress = {
            bytesTransferred: snapshot.bytesTransferred,
            totalBytes: snapshot.totalBytes,
            progress: (snapshot.bytesTransferred / snapshot.totalBytes) * 100,
            state: snapshot.state as DocumentUploadProgress['state']
          }
          uploadProgress.value = progress
          options.onProgress?.(progress)
        },
        (err) => {
          uploadProgress.value = null
          reject(err)
        },
        async () => {
          try {
            // Get download URL
            const downloadUrl = await getDownloadURL(fileRef)

            // Create Firestore document
            const documentsRef = collection($firestore!, 'documents')
            const docRef = await addDoc(documentsRef, {
              caseId,
              filename: file.name,
              title: options.title || file.name,
              storagePath: path,
              downloadUrl,
              mimeType: file.type || 'application/octet-stream',
              fileSize: file.size,
              documentType: options.documentType || 'general',
              status: 'processing',
              userId,
              teamId: currentTeam.value?.id || null,
              createdAt: serverTimestamp(),
              updatedAt: serverTimestamp()
            })

            // Update case document count
            const caseRef = doc($firestore!, 'cases', caseId)
            await updateDoc(caseRef, {
              documentCount: increment(1),
              updatedAt: serverTimestamp()
            })

            uploadProgress.value = null
            resolve(docRef.id)
          } catch (err) {
            uploadProgress.value = null
            reject(err)
          }
        }
      )
    })
  }

  /**
   * Create a document record in Firestore (without uploading file)
   * Used when file is already uploaded via useStorage
   */
  async function createDocument(data: {
    filename: string
    storagePath: string
    downloadUrl: string
    mimeType: string
    fileSize: number
    status: DocumentDoc['status']
    caseId?: string
    title?: string
    documentType?: DocumentDoc['documentType']
  }): Promise<string> {
    if (import.meta.server) throw new Error('Cannot create document on server')
    if (!$firestore) throw new Error('Firestore not initialized')
    if (!user.value) throw new Error('User must be authenticated')

    const documentsRef = collection($firestore, 'documents')
    const docRef = await addDoc(documentsRef, {
      ...data,
      caseId: data.caseId || null,
      title: data.title || data.filename,
      documentType: data.documentType || 'general',
      userId: user.value.uid,
      teamId: currentTeam.value?.id || null,
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp()
    })

    // Update case document count if caseId provided
    if (data.caseId) {
      const caseRef = doc($firestore, 'cases', data.caseId)
      await updateDoc(caseRef, {
        documentCount: increment(1),
        updatedAt: serverTimestamp()
      })
    }

    return docRef.id
  }

  /**
   * Get a document by ID
   */
  async function getDocument(id: string): Promise<DocumentDoc | null> {
    if (import.meta.server) return null
    if (!$firestore) throw new Error('Firestore not initialized')

    const docRef = doc($firestore, 'documents', id)
    const docSnap = await getDoc(docRef)

    if (!docSnap.exists()) return null

    return {
      id: docSnap.id,
      ...docSnap.data()
    } as DocumentDoc
  }

  /**
   * List documents with optional filters
   */
  async function listDocuments(options: {
    caseId?: string
    status?: DocumentDoc['status']
    documentType?: DocumentDoc['documentType']
    limitCount?: number
  } = {}): Promise<DocumentDoc[]> {
    if (import.meta.server) return []
    if (!$firestore) throw new Error('Firestore not initialized')
    if (!user.value) throw new Error('User must be authenticated')

    isLoading.value = true
    error.value = null

    try {
      const constraints: QueryConstraint[] = []

      if (options.caseId) {
        constraints.push(where('caseId', '==', options.caseId))
      }

      // Filter by team or user
      if (currentTeam.value?.id) {
        constraints.push(where('teamId', '==', currentTeam.value.id))
      } else {
        constraints.push(where('userId', '==', user.value.uid))
      }

      if (options.status) {
        constraints.push(where('status', '==', options.status))
      }

      if (options.documentType) {
        constraints.push(where('documentType', '==', options.documentType))
      }

      constraints.push(orderBy('createdAt', 'desc'))

      if (options.limitCount) {
        constraints.push(limit(options.limitCount))
      }

      const documentsRef = collection($firestore, 'documents')
      const q = query(documentsRef, ...constraints)
      const querySnapshot = await getDocs(q)

      const result = querySnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      })) as DocumentDoc[]

      documents.value = result
      return result
    } catch (err) {
      error.value = err instanceof Error ? err : new Error('Failed to list documents')
      throw error.value
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update a document
   */
  async function updateDocument(id: string, data: Partial<DocumentDoc>): Promise<void> {
    if (import.meta.server) return
    if (!$firestore) throw new Error('Firestore not initialized')

    const docRef = doc($firestore, 'documents', id)
    await updateDoc(docRef, {
      ...data,
      updatedAt: serverTimestamp()
    })

    // Update local state
    if (currentDocument.value?.id === id) {
      currentDocument.value = { ...currentDocument.value, ...data }
    }

    const index = documents.value.findIndex(d => d.id === id)
    if (index !== -1) {
      documents.value[index] = { ...documents.value[index], ...data }
    }
  }

  /**
   * Delete a document
   */
  async function deleteDocument(id: string): Promise<void> {
    if (import.meta.server) return
    if (!$firestore || !$storage) throw new Error('Firebase not initialized')

    // Get the document to find storage path and case ID
    const docData = await getDocument(id)
    if (!docData) throw new Error('Document not found')

    // Delete from Storage
    if (docData.storagePath) {
      try {
        const fileRef = storageRef($storage, docData.storagePath)
        await deleteObject(fileRef)
      } catch (err) {
        console.warn('Failed to delete file from storage:', err)
      }
    }

    // Delete from Firestore
    const docRef = doc($firestore, 'documents', id)
    await deleteDoc(docRef)

    // Update case document count
    if (docData.caseId) {
      const caseRef = doc($firestore, 'cases', docData.caseId)
      await updateDoc(caseRef, {
        documentCount: increment(-1),
        updatedAt: serverTimestamp()
      })
    }

    // Remove from local state
    documents.value = documents.value.filter(d => d.id !== id)
    if (currentDocument.value?.id === id) {
      currentDocument.value = null
    }
  }

  /**
   * Subscribe to real-time updates for documents
   */
  function subscribeToDocuments(
    options: { caseId?: string } = {},
    callback?: (data: DocumentDoc[]) => void
  ): () => void {
    if (!$firestore || !user.value) {
      return () => {}
    }

    const constraints: QueryConstraint[] = []

    if (options.caseId) {
      constraints.push(where('caseId', '==', options.caseId))
    }

    if (currentTeam.value?.id) {
      constraints.push(where('teamId', '==', currentTeam.value.id))
    } else {
      constraints.push(where('userId', '==', user.value.uid))
    }

    constraints.push(orderBy('createdAt', 'desc'))

    const documentsRef = collection($firestore, 'documents')
    const q = query(documentsRef, ...constraints)

    return onSnapshot(q, (querySnapshot) => {
      const result = querySnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      })) as DocumentDoc[]

      documents.value = result
      callback?.(result)
    })
  }

  /**
   * Subscribe to a single document
   */
  function subscribeToDocument(
    id: string,
    callback: (data: DocumentDoc | null) => void
  ): () => void {
    if (!$firestore) {
      callback(null)
      return () => {}
    }

    const docRef = doc($firestore, 'documents', id)
    return onSnapshot(docRef, (docSnap) => {
      if (!docSnap.exists()) {
        callback(null)
        return
      }
      const data = {
        id: docSnap.id,
        ...docSnap.data()
      } as DocumentDoc
      currentDocument.value = data
      callback(data)
    })
  }

  /**
   * Download a document
   */
  function getDownloadUrl(doc: DocumentDoc): string {
    return doc.downloadUrl
  }

  return {
    // State
    documents,
    currentDocument,
    isLoading,
    error,
    uploadProgress,
    // Methods
    createDocument,
    uploadDocument,
    getDocument,
    listDocuments,
    updateDocument,
    deleteDocument,
    subscribeToDocuments,
    subscribeToDocument,
    getDownloadUrl
  }
}
