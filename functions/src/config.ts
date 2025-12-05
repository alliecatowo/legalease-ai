/**
 * Centralized Configuration
 *
 * All project-level configuration should be defined here.
 * This ensures consistency across the codebase and makes it easy
 * to update values in one place.
 */

/**
 * Get the GCP project ID from environment or use default
 */
export function getProjectId(): string {
  return (
    process.env.GCLOUD_PROJECT ||
    process.env.GOOGLE_CLOUD_PROJECT ||
    process.env.FIREBASE_PROJECT_ID ||
    'legalease-420'
  )
}

/**
 * Get the Firebase Storage bucket name
 */
export function getStorageBucket(): string {
  return process.env.FIREBASE_STORAGE_BUCKET || `${getProjectId()}.firebasestorage.app`
}

/**
 * Get the default GCP region
 */
export function getRegion(): string {
  return process.env.FUNCTION_REGION || 'us-central1'
}

/**
 * Project configuration object
 */
export const config = {
  /** GCP/Firebase Project ID */
  get projectId() {
    return getProjectId()
  },

  /** Firebase Storage bucket */
  get storageBucket() {
    return getStorageBucket()
  },

  /** Default GCP region */
  get region() {
    return getRegion()
  },

  /** Firebase Functions service account */
  get serviceAccount() {
    return `${getProjectId()}@appspot.gserviceaccount.com`
  },

  /** Storage configuration */
  storage: {
    /** Transcription results path prefix */
    transcriptionResultsPath: 'transcription-results',

    /** Documents storage path prefix */
    documentsPath: 'documents'
  },

  /** Docling configuration */
  docling: {
    /** Cloud Run service URL */
    get serviceUrl() {
      return process.env.DOCLING_SERVICE_URL || 'http://localhost:5001'
    },

    /** Request timeout in milliseconds */
    get timeout() {
      return parseInt(process.env.DOCLING_TIMEOUT || '600000', 10)
    },

    /** Skip OCR by default */
    get skipOcr() {
      return process.env.DOCLING_SKIP_OCR === 'true'
    },

    /** Skip table structure detection */
    get skipTableStructure() {
      return process.env.DOCLING_SKIP_TABLE_STRUCTURE === 'true'
    }
  },

  /** Speech-to-Text configuration */
  speech: {
    /** Default location for Speech API */
    location: 'us',

    /** Default model */
    model: 'chirp_3'
  }
} as const

export default config
