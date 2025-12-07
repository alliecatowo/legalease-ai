/**
 * Centralized Configuration
 *
 * All project-level configuration should be defined here.
 * This ensures consistency across the codebase and makes it easy
 * to update values in one place.
 */

/**
 * Check if running in Firebase emulator mode
 */
export function isEmulator(): boolean {
  return (
    process.env.FUNCTIONS_EMULATOR === 'true' ||
    process.env.FIREBASE_EMULATOR_HUB !== undefined ||
    process.env.USE_EMULATORS === 'true'
  )
}

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
    /** Cloud Run service URL (local Docker uses port 5050) */
    get serviceUrl() {
      if (isEmulator()) {
        return process.env.DOCLING_SERVICE_URL || 'http://localhost:5050'
      }
      return process.env.DOCLING_SERVICE_URL || 'http://localhost:5050'
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

  /** Qdrant vector database configuration */
  qdrant: {
    /**
     * Whether to use local Qdrant (set via QDRANT_LOCAL=true)
     * This is independent of Firebase emulator mode - you can mix and match:
     * - Emulators + Local Qdrant
     * - Emulators + Cloud Qdrant
     * - Production + Cloud Qdrant
     */
    get useLocal() {
      return process.env.QDRANT_LOCAL === 'true'
    },

    /** Qdrant server URL */
    get url() {
      // Check env var first (works for both local and cloud)
      if (process.env.QDRANT_URL) {
        return process.env.QDRANT_URL
      }
      // Default based on useLocal flag
      return this.useLocal ? 'http://localhost:6333' : ''
    },

    /** Qdrant API key (empty for local, required for cloud) */
    get apiKey() {
      return process.env.QDRANT_API_KEY || ''
    },

    /** Collection name for document chunks */
    collectionName: 'legal_documents',

    /** Check if using local Qdrant (no auth needed) */
    get isLocal() {
      return this.useLocal || this.url.includes('localhost')
    }
  },

  /** Speech-to-Text configuration (legacy - used by Chirp provider) */
  speech: {
    /** Default location for Speech API */
    location: 'us',

    /** Default model */
    model: 'chirp_3'
  },

  /** Transcription provider configuration */
  transcription: {
    /** Default transcription provider (gemini, chirp) */
    get defaultProvider() {
      return process.env.TRANSCRIPTION_PROVIDER || 'gemini'
    },

    /** Gemini model for transcription */
    get geminiModel() {
      return process.env.TRANSCRIPTION_GEMINI_MODEL || 'gemini-2.5-flash'
    },

    /** File size threshold for Gemini Files API (20MB) */
    fileSizeThresholdBytes: 20 * 1024 * 1024
  }
} as const

export default config
