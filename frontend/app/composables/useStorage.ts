/**
 * Storage composable - provides reactive file upload functionality
 *
 * Uses the storage provider abstraction for flexibility.
 * Currently backs to Firebase Storage, but can be swapped to S3, etc.
 */

import { createStorageProvider, type StorageResult, type UploadProgress, type StorageProvider } from '~/services/storage'

export type { StorageResult, UploadProgress }

export function useStorage() {
  const { $storage } = useNuxtApp()
  const { user } = useAuth()

  const uploadProgress = ref<UploadProgress | null>(null)
  const isUploading = ref(false)
  const uploadError = ref<string | null>(null)

  // Keep reference to current provider for pause/resume/cancel
  let currentProvider: StorageProvider | null = null

  // Create provider when needed (lazy initialization)
  function getProvider(): StorageProvider {
    if (!$storage) {
      throw new Error('Firebase Storage not initialized')
    }
    if (!user.value) {
      throw new Error('User must be authenticated to upload files')
    }

    // Create new provider if none exists or user changed
    if (!currentProvider) {
      currentProvider = createStorageProvider($storage, user.value.uid)
    }

    return currentProvider
  }

  /**
   * Upload a file to cloud storage
   * @param file - The file to upload
   * @param path - Storage path (e.g., 'cases/123/transcriptions')
   * @param filename - Optional custom filename (defaults to original)
   */
  async function uploadFile(
    file: File,
    path: string,
    filename?: string
  ): Promise<StorageResult> {
    const provider = getProvider()

    isUploading.value = true
    uploadError.value = null
    uploadProgress.value = {
      bytesTransferred: 0,
      totalBytes: file.size,
      progress: 0,
      state: 'running'
    }

    // Set up progress tracking
    provider.onProgress((progress) => {
      uploadProgress.value = progress
    })

    try {
      const result = await provider.upload(file, path, { filename })

      // Map storageUri to gsUri for backward compatibility
      return {
        downloadUrl: result.downloadUrl,
        gsUri: result.storageUri, // Alias for backward compatibility
        storageUri: result.storageUri,
        path: result.path,
        metadata: result.metadata
      } as StorageResult & { gsUri: string }
    } catch (error: any) {
      uploadError.value = error.message
      throw error
    } finally {
      isUploading.value = false
    }
  }

  /**
   * Upload a file specifically for transcription
   * @param file - Audio/video file
   * @param caseId - Optional case ID to associate with
   */
  async function uploadForTranscription(
    file: File,
    caseId?: string
  ): Promise<StorageResult & { gsUri: string }> {
    const basePath = caseId
      ? `cases/${caseId}/transcriptions`
      : `users/${user.value?.uid}/transcriptions`

    return uploadFile(file, basePath) as Promise<StorageResult & { gsUri: string }>
  }

  /**
   * Cancel the current upload
   */
  function cancelUpload() {
    try {
      const provider = getProvider()
      provider.cancel()
    } catch {
      // Provider may not be initialized
    }
  }

  /**
   * Pause the current upload
   */
  function pauseUpload() {
    try {
      const provider = getProvider()
      provider.pause()
    } catch {
      // Provider may not be initialized
    }
  }

  /**
   * Resume a paused upload
   */
  function resumeUpload() {
    try {
      const provider = getProvider()
      provider.resume()
    } catch {
      // Provider may not be initialized
    }
  }

  /**
   * Reset upload state
   */
  function resetUpload() {
    uploadProgress.value = null
    isUploading.value = false
    uploadError.value = null
  }

  return {
    uploadFile,
    uploadForTranscription,
    cancelUpload,
    pauseUpload,
    resumeUpload,
    resetUpload,
    uploadProgress,
    isUploading,
    uploadError
  }
}
