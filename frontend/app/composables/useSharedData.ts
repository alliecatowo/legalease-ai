/**
 * Shared Data Cache Composable
 *
 * This composable implements a singleton pattern using Nuxt's useState to ensure
 * data is shared across all pages and components. This solves the performance issue
 * where each page was fetching the same data independently with different cache keys.
 *
 * Benefits:
 * - Single source of truth for cases, documents, transcriptions, and forensic exports
 * - Reduces redundant API calls
 * - Faster navigation between pages
 * - Consistent data across the application
 * - Efficient cache invalidation
 *
 * Usage:
 * ```ts
 * const { cases, documents, transcriptions, forensicExports } = useSharedData()
 *
 * // Access data
 * console.log(cases.data.value)
 *
 * // Refresh data
 * await cases.refresh()
 *
 * // Check loading state
 * if (cases.loading.value) { ... }
 *
 * // Invalidate cache
 * cases.invalidate()
 *
 * // Clear all caches
 * const { clearAll } = useSharedData()
 * clearAll()
 * ```
 */

import type { Ref } from 'vue'

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * API Response for cases list
 */
export interface CaseListResponse {
  cases: CaseItem[]
  total: number
  page: number
  page_size: number
}

/**
 * Individual case item from API
 */
export interface CaseItem {
  id: string | number
  name: string
  case_number: string
  description?: string
  status?: string
  matter_type?: string
  created_at?: string
  updated_at?: string
  is_loaded?: boolean
  [key: string]: any
}

/**
 * API Response for documents list
 */
export interface DocumentListResponse {
  documents: DocumentItem[]
  total: number
}

/**
 * Individual document item from API
 */
export interface DocumentItem {
  id: string | number
  filename: string
  document_type?: string
  uploaded_at?: string
  file_size?: number
  status?: string
  case_id?: string | number
  case_name?: string
  case_number?: string
  [key: string]: any
}

/**
 * API Response for transcriptions list
 */
export interface TranscriptionListResponse {
  transcriptions: TranscriptionItem[]
  total: number
  page?: number
  page_size?: number
}

/**
 * Individual transcription item from API
 */
export interface TranscriptionItem {
  id: number
  filename: string
  title?: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  duration?: number
  uploaded_at?: string
  completed_at?: string
  case_id?: number
  case_name?: string
  has_summary?: boolean
  [key: string]: any
}

/**
 * API Response for forensic exports list
 */
export interface ForensicExportListResponse {
  exports: ForensicExportItem[]
  total: number
}

/**
 * Individual forensic export item from API
 */
export interface ForensicExportItem {
  gid: string
  folder_name: string
  export_uuid?: string
  case_gid: string
  case_name?: string
  total_records?: number
  num_attachments?: number
  size_bytes?: number
  export_status?: string
  discovered_at?: string
  [key: string]: any
}

/**
 * Generic cache state for a data type
 */
export interface CacheState<T> {
  /** The cached data */
  data: Ref<T | null>
  /** Loading state */
  loading: Ref<boolean>
  /** Error state */
  error: Ref<Error | null>
  /** Last updated timestamp */
  lastUpdated: Ref<number | null>
  /** Refresh function to fetch fresh data */
  refresh: () => Promise<void>
  /** Invalidate cache without fetching */
  invalidate: () => void
  /** Check if cache is stale (older than maxAge milliseconds) */
  isStale: (maxAge?: number) => boolean
}

// ============================================================================
// Main Composable
// ============================================================================

/**
 * Shared data cache composable
 * Provides centralized access to cases, documents, transcriptions, and forensic exports
 *
 * NOTE: useState calls are inside the function for SSR safety.
 * useState automatically creates singletons based on the key,
 * so the state is still shared across all components and pages.
 */
export function useSharedData() {
  const api = useApi()

  // ==========================================================================
  // Singleton State Management (SSR-Safe)
  // ==========================================================================
  // These useState calls create singleton state shared across all components.
  // They must be inside the function to work with SSR.

  /**
   * Global shared state for cases
   */
  const casesData = useState<CaseListResponse | null>('shared-cases-data', () => null)
  const casesLoading = useState<boolean>('shared-cases-loading', () => false)
  const casesError = useState<Error | null>('shared-cases-error', () => null)
  const casesLastUpdated = useState<number | null>('shared-cases-last-updated', () => null)

  /**
   * Global shared state for documents
   */
  const documentsData = useState<DocumentListResponse | null>('shared-documents-data', () => null)
  const documentsLoading = useState<boolean>('shared-documents-loading', () => false)
  const documentsError = useState<Error | null>('shared-documents-error', () => null)
  const documentsLastUpdated = useState<number | null>('shared-documents-last-updated', () => null)

  /**
   * Global shared state for transcriptions
   */
  const transcriptionsData = useState<TranscriptionListResponse | null>('shared-transcriptions-data', () => null)
  const transcriptionsLoading = useState<boolean>('shared-transcriptions-loading', () => false)
  const transcriptionsError = useState<Error | null>('shared-transcriptions-error', () => null)
  const transcriptionsLastUpdated = useState<number | null>('shared-transcriptions-last-updated', () => null)

  /**
   * Global shared state for forensic exports
   */
  const forensicExportsData = useState<ForensicExportItem[] | null>('shared-forensic-exports-data', () => null)
  const forensicExportsLoading = useState<boolean>('shared-forensic-exports-loading', () => false)
  const forensicExportsError = useState<Error | null>('shared-forensic-exports-error', () => null)
  const forensicExportsLastUpdated = useState<number | null>('shared-forensic-exports-last-updated', () => null)

  // Default cache duration: 5 minutes
  const DEFAULT_CACHE_DURATION = 5 * 60 * 1000

  // ==========================================================================
  // Cases
  // ==========================================================================

  /**
   * Fetch cases from API and update cache
   */
  const fetchCases = async (): Promise<void> => {
    // Skip if already loading
    if (casesLoading.value) return

    casesLoading.value = true
    casesError.value = null

    try {
      const response = await api.cases.list()
      casesData.value = response
      casesLastUpdated.value = Date.now()
    } catch (err) {
      casesError.value = err instanceof Error ? err : new Error('Failed to fetch cases')
      console.error('Error fetching cases:', err)
    } finally {
      casesLoading.value = false
    }
  }

  /**
   * Invalidate cases cache without fetching
   */
  const invalidateCases = (): void => {
    casesData.value = null
    casesLastUpdated.value = null
    casesError.value = null
  }

  /**
   * Check if cases cache is stale
   */
  const isCasesStale = (maxAge: number = DEFAULT_CACHE_DURATION): boolean => {
    if (!casesLastUpdated.value) return true
    return Date.now() - casesLastUpdated.value > maxAge
  }

  /**
   * Refresh cases data - always fetches fresh data
   */
  const refreshCases = async (): Promise<void> => {
    await fetchCases()
  }

  /**
   * Get cases with automatic caching
   * Fetches only if cache is empty or stale
   */
  const getCases = async (forceRefresh: boolean = false): Promise<void> => {
    if (forceRefresh || !casesData.value || isCasesStale()) {
      await fetchCases()
    }
  }

  // ==========================================================================
  // Documents
  // ==========================================================================

  /**
   * Fetch documents from API and update cache
   */
  const fetchDocuments = async (): Promise<void> => {
    // Skip if already loading
    if (documentsLoading.value) return

    documentsLoading.value = true
    documentsError.value = null

    try {
      const response = await api.documents.listAll()
      documentsData.value = response
      documentsLastUpdated.value = Date.now()
    } catch (err) {
      documentsError.value = err instanceof Error ? err : new Error('Failed to fetch documents')
      console.error('Error fetching documents:', err)
    } finally {
      documentsLoading.value = false
    }
  }

  /**
   * Invalidate documents cache without fetching
   */
  const invalidateDocuments = (): void => {
    documentsData.value = null
    documentsLastUpdated.value = null
    documentsError.value = null
  }

  /**
   * Check if documents cache is stale
   */
  const isDocumentsStale = (maxAge: number = DEFAULT_CACHE_DURATION): boolean => {
    if (!documentsLastUpdated.value) return true
    return Date.now() - documentsLastUpdated.value > maxAge
  }

  /**
   * Refresh documents data - always fetches fresh data
   */
  const refreshDocuments = async (): Promise<void> => {
    await fetchDocuments()
  }

  /**
   * Get documents with automatic caching
   * Fetches only if cache is empty or stale
   */
  const getDocuments = async (forceRefresh: boolean = false): Promise<void> => {
    if (forceRefresh || !documentsData.value || isDocumentsStale()) {
      await fetchDocuments()
    }
  }

  // ==========================================================================
  // Transcriptions
  // ==========================================================================

  /**
   * Fetch transcriptions from API and update cache
   */
  const fetchTranscriptions = async (): Promise<void> => {
    // Skip if already loading
    if (transcriptionsLoading.value) return

    transcriptionsLoading.value = true
    transcriptionsError.value = null

    try {
      // Fetch with a large page size to get all transcriptions
      const response = await api.transcriptions.listAll({ page: 1, page_size: 100 })
      transcriptionsData.value = response
      transcriptionsLastUpdated.value = Date.now()
    } catch (err) {
      transcriptionsError.value = err instanceof Error ? err : new Error('Failed to fetch transcriptions')
      console.error('Error fetching transcriptions:', err)
    } finally {
      transcriptionsLoading.value = false
    }
  }

  /**
   * Invalidate transcriptions cache without fetching
   */
  const invalidateTranscriptions = (): void => {
    transcriptionsData.value = null
    transcriptionsLastUpdated.value = null
    transcriptionsError.value = null
  }

  /**
   * Check if transcriptions cache is stale
   */
  const isTranscriptionsStale = (maxAge: number = DEFAULT_CACHE_DURATION): boolean => {
    if (!transcriptionsLastUpdated.value) return true
    return Date.now() - transcriptionsLastUpdated.value > maxAge
  }

  /**
   * Refresh transcriptions data - always fetches fresh data
   */
  const refreshTranscriptions = async (): Promise<void> => {
    await fetchTranscriptions()
  }

  /**
   * Get transcriptions with automatic caching
   * Fetches only if cache is empty or stale
   */
  const getTranscriptions = async (forceRefresh: boolean = false): Promise<void> => {
    if (forceRefresh || !transcriptionsData.value || isTranscriptionsStale()) {
      await fetchTranscriptions()
    }
  }

  // ==========================================================================
  // Forensic Exports
  // ==========================================================================

  /**
   * Fetch forensic exports from API and update cache
   */
  const fetchForensicExports = async (): Promise<void> => {
    // Skip if already loading
    if (forensicExportsLoading.value) return

    forensicExportsLoading.value = true
    forensicExportsError.value = null

    try {
      const response = await api.forensicExports.listAll()

      // Enrich exports with case names from the cases cache
      const enriched = (response.exports || []).map((exp: any) => {
        const caseItem = casesData.value?.cases?.find((c: any) => c.gid === exp.case_gid)
        return {
          ...exp,
          case_name: exp.case_name || caseItem?.name || `Case ${exp.case_gid}`
        }
      })

      forensicExportsData.value = enriched
      forensicExportsLastUpdated.value = Date.now()
    } catch (err) {
      forensicExportsError.value = err instanceof Error ? err : new Error('Failed to fetch forensic exports')
      console.error('Error fetching forensic exports:', err)
    } finally {
      forensicExportsLoading.value = false
    }
  }

  /**
   * Invalidate forensic exports cache without fetching
   */
  const invalidateForensicExports = (): void => {
    forensicExportsData.value = null
    forensicExportsLastUpdated.value = null
    forensicExportsError.value = null
  }

  /**
   * Check if forensic exports cache is stale
   */
  const isForensicExportsStale = (maxAge: number = DEFAULT_CACHE_DURATION): boolean => {
    if (!forensicExportsLastUpdated.value) return true
    return Date.now() - forensicExportsLastUpdated.value > maxAge
  }

  /**
   * Refresh forensic exports data - always fetches fresh data
   */
  const refreshForensicExports = async (): Promise<void> => {
    await fetchForensicExports()
  }

  /**
   * Get forensic exports with automatic caching
   * Fetches only if cache is empty or stale
   */
  const getForensicExports = async (forceRefresh: boolean = false): Promise<void> => {
    if (forceRefresh || !forensicExportsData.value || isForensicExportsStale()) {
      await fetchForensicExports()
    }
  }

  // ==========================================================================
  // Utility Functions
  // ==========================================================================

  /**
   * Clear all caches at once
   */
  const clearAll = (): void => {
    invalidateCases()
    invalidateDocuments()
    invalidateTranscriptions()
    invalidateForensicExports()
  }

  /**
   * Refresh all data at once
   */
  const refreshAll = async (): Promise<void> => {
    await Promise.all([
      fetchCases(),
      fetchDocuments(),
      fetchTranscriptions(),
      fetchForensicExports()
    ])
  }

  /**
   * Initialize all data if not already loaded
   * Useful for pre-loading data on app start
   */
  const initialize = async (): Promise<void> => {
    const promises: Promise<void>[] = []

    if (!casesData.value) {
      promises.push(getCases())
    }
    if (!documentsData.value) {
      promises.push(getDocuments())
    }
    if (!transcriptionsData.value) {
      promises.push(getTranscriptions())
    }
    if (!forensicExportsData.value) {
      promises.push(getForensicExports())
    }

    if (promises.length > 0) {
      await Promise.all(promises)
    }
  }

  /**
   * Get overall loading state
   */
  const isAnyLoading = computed(() => {
    return casesLoading.value || documentsLoading.value || transcriptionsLoading.value || forensicExportsLoading.value
  })

  /**
   * Get overall error state
   */
  const hasAnyError = computed(() => {
    return !!(casesError.value || documentsError.value || transcriptionsError.value || forensicExportsError.value)
  })

  /**
   * Get all errors
   */
  const allErrors = computed(() => {
    return {
      cases: casesError.value,
      documents: documentsError.value,
      transcriptions: transcriptionsError.value,
      forensicExports: forensicExportsError.value
    }
  })

  // ==========================================================================
  // Return API
  // ==========================================================================

  return {
    /**
     * Cases cache state and operations
     */
    cases: {
      data: casesData,
      loading: casesLoading,
      error: casesError,
      lastUpdated: casesLastUpdated,
      refresh: refreshCases,
      invalidate: invalidateCases,
      isStale: isCasesStale,
      get: getCases
    } as CacheState<CaseListResponse> & { get: (forceRefresh?: boolean) => Promise<void> },

    /**
     * Documents cache state and operations
     */
    documents: {
      data: documentsData,
      loading: documentsLoading,
      error: documentsError,
      lastUpdated: documentsLastUpdated,
      refresh: refreshDocuments,
      invalidate: invalidateDocuments,
      isStale: isDocumentsStale,
      get: getDocuments
    } as CacheState<DocumentListResponse> & { get: (forceRefresh?: boolean) => Promise<void> },

    /**
     * Transcriptions cache state and operations
     */
    transcriptions: {
      data: transcriptionsData,
      loading: transcriptionsLoading,
      error: transcriptionsError,
      lastUpdated: transcriptionsLastUpdated,
      refresh: refreshTranscriptions,
      invalidate: invalidateTranscriptions,
      isStale: isTranscriptionsStale,
      get: getTranscriptions
    } as CacheState<TranscriptionListResponse> & { get: (forceRefresh?: boolean) => Promise<void> },

    /**
     * Forensic Exports cache state and operations
     */
    forensicExports: {
      data: forensicExportsData,
      loading: forensicExportsLoading,
      error: forensicExportsError,
      lastUpdated: forensicExportsLastUpdated,
      refresh: refreshForensicExports,
      invalidate: invalidateForensicExports,
      isStale: isForensicExportsStale,
      get: getForensicExports
    } as CacheState<ForensicExportItem[]> & { get: (forceRefresh?: boolean) => Promise<void> },

    /**
     * Utility functions
     */
    clearAll,
    refreshAll,
    initialize,
    isAnyLoading,
    hasAnyError,
    allErrors
  }
}

// ============================================================================
// Computed Helpers
// ============================================================================

/**
 * Get computed case by ID
 * Useful for finding a specific case from the cache
 */
export function useSharedCase(caseId: Ref<string | number> | string | number) {
  const { cases } = useSharedData()
  const id = computed(() => typeof caseId === 'object' ? caseId.value : caseId)

  const caseItem = computed(() => {
    if (!cases.data.value?.cases) return null
    return cases.data.value.cases.find(c => String(c.id) === String(id.value)) || null
  })

  return {
    case: caseItem,
    loading: cases.loading,
    error: cases.error,
    refresh: cases.refresh
  }
}

/**
 * Get computed document by ID
 * Useful for finding a specific document from the cache
 */
export function useSharedDocument(documentId: Ref<string | number> | string | number) {
  const { documents } = useSharedData()
  const id = computed(() => typeof documentId === 'object' ? documentId.value : documentId)

  const documentItem = computed(() => {
    if (!documents.data.value?.documents) return null
    return documents.data.value.documents.find(d => String(d.id) === String(id.value)) || null
  })

  return {
    document: documentItem,
    loading: documents.loading,
    error: documents.error,
    refresh: documents.refresh
  }
}

/**
 * Get computed transcription by ID
 * Useful for finding a specific transcription from the cache
 */
export function useSharedTranscription(transcriptionGid: Ref<string | number> | string | number) {
  const { transcriptions } = useSharedData()
  const gid = computed(() => typeof transcriptionGid === 'object' ? String(transcriptionGid.value) : String(transcriptionGid))

  const transcriptionItem = computed(() => {
    if (!transcriptions.data.value?.transcriptions) return null
    return transcriptions.data.value.transcriptions.find(t => String(t.gid) === gid.value) || null
  })

  return {
    transcription: transcriptionItem,
    loading: transcriptions.loading,
    error: transcriptions.error,
    refresh: transcriptions.refresh
  }
}

/**
 * Get cases filtered by status
 */
export function useSharedCasesByStatus(status: Ref<string> | string) {
  const { cases } = useSharedData()
  const statusValue = computed(() => typeof status === 'object' ? status.value : status)

  const filteredCases = computed(() => {
    if (!cases.data.value?.cases) return []
    return cases.data.value.cases.filter(c => c.status === statusValue.value)
  })

  return {
    cases: filteredCases,
    loading: cases.loading,
    error: cases.error,
    refresh: cases.refresh
  }
}

/**
 * Get documents for a specific case
 */
export function useSharedDocumentsByCase(caseId: Ref<string | number> | string | number) {
  const { documents } = useSharedData()
  const id = computed(() => typeof caseId === 'object' ? caseId.value : caseId)

  const caseDocuments = computed(() => {
    if (!documents.data.value?.documents) return []
    return documents.data.value.documents.filter(d => String(d.case_id) === String(id.value))
  })

  return {
    documents: caseDocuments,
    loading: documents.loading,
    error: documents.error,
    refresh: documents.refresh
  }
}

/**
 * Get transcriptions for a specific case
 */
export function useSharedTranscriptionsByCase(caseId: Ref<number> | number) {
  const { transcriptions } = useSharedData()
  const id = computed(() => typeof caseId === 'object' ? caseId.value : caseId)

  const caseTranscriptions = computed(() => {
    if (!transcriptions.data.value?.transcriptions) return []
    return transcriptions.data.value.transcriptions.filter(t => t.case_id === id.value)
  })

  return {
    transcriptions: caseTranscriptions,
    loading: transcriptions.loading,
    error: transcriptions.error,
    refresh: transcriptions.refresh
  }
}
