/**
 * Google Cloud Storage provider
 *
 * Handles gs:// URIs for Google Cloud Storage operations.
 */

import type { StorageProvider, StorageCapabilities } from '../provider.js'
import type { StorageMetadata } from '../types.js'
import { parseUri } from '../types.js'

export class GCSProvider implements StorageProvider {
  readonly name = 'gcs'
  readonly displayName = 'Google Cloud Storage'
  readonly scheme = 'gs' as const

  readonly capabilities: StorageCapabilities = {
    resumableUpload: true,
    signedUrls: true,
    streaming: true,
    maxFileSize: undefined // No practical limit
  }

  private storageClient: any = null

  /**
   * Lazily initialize the Storage client
   */
  private async getClient() {
    if (!this.storageClient) {
      const { Storage } = await import('@google-cloud/storage')
      this.storageClient = new Storage()
    }
    return this.storageClient
  }

  canHandle(uri: string): boolean {
    return uri.startsWith('gs://')
  }

  async download(uri: string): Promise<Buffer> {
    const { bucket, path } = parseUri(uri)
    const storage = await this.getClient()

    const [fileBuffer] = await storage.bucket(bucket).file(path).download()
    return fileBuffer
  }

  async getSignedUrl(uri: string, expiresInSeconds: number = 3600): Promise<string> {
    const { bucket, path } = parseUri(uri)
    const storage = await this.getClient()

    const [signedUrl] = await storage.bucket(bucket).file(path).getSignedUrl({
      action: 'read',
      expires: Date.now() + expiresInSeconds * 1000
    })

    return signedUrl
  }

  async getMetadata(uri: string): Promise<StorageMetadata> {
    const { bucket, path } = parseUri(uri)
    const storage = await this.getClient()

    const [metadata] = await storage.bucket(bucket).file(path).getMetadata()

    return {
      name: metadata.name || path.split('/').pop() || '',
      size: parseInt(metadata.size, 10) || 0,
      contentType: metadata.contentType || 'application/octet-stream',
      timeCreated: metadata.timeCreated,
      updated: metadata.updated
    }
  }

  async exists(uri: string): Promise<boolean> {
    const { bucket, path } = parseUri(uri)
    const storage = await this.getClient()

    const [exists] = await storage.bucket(bucket).file(path).exists()
    return exists
  }

  async delete(uri: string): Promise<void> {
    const { bucket, path } = parseUri(uri)
    const storage = await this.getClient()

    await storage.bucket(bucket).file(path).delete()
  }
}
