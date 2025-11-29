import {
  ref as storageRef,
  uploadBytesResumable,
  getDownloadURL,
  type UploadTask,
  type StorageReference
} from 'firebase/storage'

export interface UploadProgress {
  bytesTransferred: number
  totalBytes: number
  progress: number
  state: 'running' | 'paused' | 'success' | 'error' | 'canceled'
}

export interface UploadResult {
  downloadUrl: string
  gsUri: string
  path: string
  metadata: {
    name: string
    size: number
    contentType: string
    timeCreated: string
  }
}

export function useStorage() {
  const { $storage } = useNuxtApp()
  const { user } = useAuth()

  const uploadProgress = ref<UploadProgress | null>(null)
  const isUploading = ref(false)
  const uploadError = ref<string | null>(null)
  const currentUploadTask = ref<UploadTask | null>(null)

  /**
   * Upload a file to Firebase Storage
   * @param file - The file to upload
   * @param path - Storage path (e.g., 'cases/123/transcriptions')
   * @param filename - Optional custom filename (defaults to original)
   */
  async function uploadFile(
    file: File,
    path: string,
    filename?: string
  ): Promise<UploadResult> {
    if (!$storage) {
      throw new Error('Firebase Storage not initialized')
    }

    if (!user.value) {
      throw new Error('User must be authenticated to upload files')
    }

    const finalFilename = filename || `${Date.now()}-${file.name}`
    const fullPath = `${path}/${finalFilename}`
    const fileRef = storageRef($storage, fullPath)

    isUploading.value = true
    uploadError.value = null
    uploadProgress.value = {
      bytesTransferred: 0,
      totalBytes: file.size,
      progress: 0,
      state: 'running'
    }

    return new Promise((resolve, reject) => {
      const uploadTask = uploadBytesResumable(fileRef, file, {
        contentType: file.type,
        customMetadata: {
          uploadedBy: user.value!.uid,
          originalName: file.name
        }
      })

      currentUploadTask.value = uploadTask

      uploadTask.on(
        'state_changed',
        (snapshot) => {
          const progress = (snapshot.bytesTransferred / snapshot.totalBytes) * 100
          uploadProgress.value = {
            bytesTransferred: snapshot.bytesTransferred,
            totalBytes: snapshot.totalBytes,
            progress,
            state: snapshot.state as UploadProgress['state']
          }
        },
        (error) => {
          isUploading.value = false
          uploadError.value = error.message
          uploadProgress.value = {
            ...uploadProgress.value!,
            state: 'error'
          }
          currentUploadTask.value = null
          reject(error)
        },
        async () => {
          try {
            const downloadUrl = await getDownloadURL(fileRef)

            // Construct the GCS URI for use with Genkit/Gemini
            const bucket = fileRef.bucket
            const gsUri = `gs://${bucket}/${fullPath}`

            const result: UploadResult = {
              downloadUrl,
              gsUri,
              path: fullPath,
              metadata: {
                name: finalFilename,
                size: file.size,
                contentType: file.type,
                timeCreated: new Date().toISOString()
              }
            }

            uploadProgress.value = {
              ...uploadProgress.value!,
              state: 'success'
            }
            isUploading.value = false
            currentUploadTask.value = null
            resolve(result)
          } catch (error: any) {
            isUploading.value = false
            uploadError.value = error.message
            currentUploadTask.value = null
            reject(error)
          }
        }
      )
    })
  }

  /**
   * Upload a file specifically for transcription
   * @param file - Audio/video file
   * @param caseId - Optional case ID to associate with
   */
  async function uploadForTranscription(
    file: File,
    caseId?: string
  ): Promise<UploadResult> {
    const basePath = caseId
      ? `cases/${caseId}/transcriptions`
      : `users/${user.value?.uid}/transcriptions`

    return uploadFile(file, basePath)
  }

  /**
   * Cancel the current upload
   */
  function cancelUpload() {
    if (currentUploadTask.value) {
      currentUploadTask.value.cancel()
      uploadProgress.value = {
        ...uploadProgress.value!,
        state: 'canceled'
      }
      isUploading.value = false
      currentUploadTask.value = null
    }
  }

  /**
   * Pause the current upload
   */
  function pauseUpload() {
    if (currentUploadTask.value) {
      currentUploadTask.value.pause()
      uploadProgress.value = {
        ...uploadProgress.value!,
        state: 'paused'
      }
    }
  }

  /**
   * Resume a paused upload
   */
  function resumeUpload() {
    if (currentUploadTask.value) {
      currentUploadTask.value.resume()
      uploadProgress.value = {
        ...uploadProgress.value!,
        state: 'running'
      }
    }
  }

  /**
   * Reset upload state
   */
  function resetUpload() {
    uploadProgress.value = null
    isUploading.value = false
    uploadError.value = null
    currentUploadTask.value = null
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
