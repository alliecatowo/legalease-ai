/**
 * Firebase Storage provider
 *
 * Handles file uploads to Firebase Storage (which backs to GCS).
 * Returns gs:// URIs for backend consumption.
 */

import {
  ref as storageRef,
  uploadBytesResumable,
  getDownloadURL,
  type UploadTask,
  type FirebaseStorage
} from 'firebase/storage'

import type { StorageProvider, StorageCapabilities, ProgressCallback } from '../provider'
import type { StorageResult, UploadProgress, UploadOptions } from '../types'

export class FirebaseStorageProvider implements StorageProvider {
  readonly name = 'firebase'
  readonly displayName = 'Firebase Storage'
  readonly scheme = 'gs' as const

  readonly capabilities: StorageCapabilities = {
    resumableUpload: true,
    pauseResume: true,
    cancellation: true,
    maxFileSize: undefined // No practical limit
  }

  private storage: FirebaseStorage
  private userId: string
  private currentUploadTask: UploadTask | null = null
  private currentProgress: UploadProgress | null = null
  private progressCallback: ProgressCallback | null = null

  constructor(storage: FirebaseStorage, userId: string) {
    this.storage = storage
    this.userId = userId
  }

  async upload(file: File, path: string, options?: UploadOptions): Promise<StorageResult> {
    const finalFilename = options?.filename || `${Date.now()}-${file.name}`
    const fullPath = `${path}/${finalFilename}`
    const fileRef = storageRef(this.storage, fullPath)

    this.currentProgress = {
      bytesTransferred: 0,
      totalBytes: file.size,
      progress: 0,
      state: 'running'
    }

    return new Promise((resolve, reject) => {
      const uploadTask = uploadBytesResumable(fileRef, file, {
        contentType: options?.contentType || file.type,
        customMetadata: {
          uploadedBy: this.userId,
          originalName: file.name,
          ...options?.customMetadata
        }
      })

      this.currentUploadTask = uploadTask

      uploadTask.on(
        'state_changed',
        (snapshot) => {
          const progress = (snapshot.bytesTransferred / snapshot.totalBytes) * 100
          this.currentProgress = {
            bytesTransferred: snapshot.bytesTransferred,
            totalBytes: snapshot.totalBytes,
            progress,
            state: snapshot.state as UploadProgress['state']
          }

          if (this.progressCallback) {
            this.progressCallback(this.currentProgress)
          }
        },
        (error) => {
          this.currentProgress = {
            ...this.currentProgress!,
            state: 'error'
          }
          this.currentUploadTask = null

          if (this.progressCallback) {
            this.progressCallback(this.currentProgress)
          }

          reject(error)
        },
        async () => {
          try {
            const downloadUrl = await getDownloadURL(fileRef)

            // Construct the GCS URI for backend use
            const bucket = fileRef.bucket
            const storageUri = `gs://${bucket}/${fullPath}`

            const result: StorageResult = {
              downloadUrl,
              storageUri,
              path: fullPath,
              metadata: {
                name: finalFilename,
                size: file.size,
                contentType: options?.contentType || file.type,
                timeCreated: new Date().toISOString()
              }
            }

            this.currentProgress = {
              ...this.currentProgress!,
              state: 'success'
            }
            this.currentUploadTask = null

            if (this.progressCallback) {
              this.progressCallback(this.currentProgress)
            }

            resolve(result)
          } catch (error: any) {
            this.currentProgress = {
              ...this.currentProgress!,
              state: 'error'
            }
            this.currentUploadTask = null
            reject(error)
          }
        }
      )
    })
  }

  onProgress(callback: ProgressCallback): void {
    this.progressCallback = callback
  }

  cancel(): void {
    if (this.currentUploadTask) {
      this.currentUploadTask.cancel()
      this.currentProgress = {
        ...this.currentProgress!,
        state: 'canceled'
      }
      this.currentUploadTask = null

      if (this.progressCallback) {
        this.progressCallback(this.currentProgress)
      }
    }
  }

  pause(): void {
    if (this.currentUploadTask) {
      this.currentUploadTask.pause()
      this.currentProgress = {
        ...this.currentProgress!,
        state: 'paused'
      }

      if (this.progressCallback) {
        this.progressCallback(this.currentProgress)
      }
    }
  }

  resume(): void {
    if (this.currentUploadTask) {
      this.currentUploadTask.resume()
      this.currentProgress = {
        ...this.currentProgress!,
        state: 'running'
      }

      if (this.progressCallback) {
        this.progressCallback(this.currentProgress)
      }
    }
  }

  getState(): UploadProgress | null {
    return this.currentProgress
  }
}
