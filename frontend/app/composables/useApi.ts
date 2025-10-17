// API Response Types
interface CaseListResponse {
  cases: any[]
  total: number
  page: number
  page_size: number
}

export const useApi = () => {
  const config = useRuntimeConfig()
  const baseURL = config.public.apiBase

  const api = $fetch.create({
    baseURL,
    onRequest({ options }) {
      // Add any auth headers here in the future
      options.headers = {
        ...options.headers
      }
    },
    onResponseError({ response }) {
      // Show toast on client-side only to avoid SSR issues
      if (import.meta.client) {
        const toast = useToast()
        let description = 'An error occurred'

        // Extract error message from different response formats
        if (response._data?.detail) {
          if (Array.isArray(response._data.detail)) {
            // Validation errors: extract first error message
            description = response._data.detail[0]?.msg || description
          } else if (typeof response._data.detail === 'string') {
            // Simple string error
            description = response._data.detail
          }
        } else if (response.statusText) {
          description = response.statusText
        }

        toast.add({
          title: 'Error',
          description,
          color: 'error'
        })
      }
    }
  })

  return {
    // Cases
    cases: {
      list: () => api<CaseListResponse>('/api/v1/cases'),
      get: (id: string) => api(`/api/v1/cases/${id}`),
      create: (data: any) => api('/api/v1/cases', { method: 'POST', body: data }),
      update: (id: string, data: any) => api(`/api/v1/cases/${id}`, { method: 'PUT', body: data }),
      delete: (id: string) => api(`/api/v1/cases/${id}`, { method: 'DELETE' }),
      load: (id: string) => api(`/api/v1/cases/${id}/load`, { method: 'POST' }),
      unload: (id: string) => api(`/api/v1/cases/${id}/unload`, { method: 'POST' }),
      archive: (id: string) => api(`/api/v1/cases/${id}/archive`, { method: 'POST' })
    },

    // Documents
    documents: {
      listByCase: (caseId: string | number) => api(`/api/v1/cases/${caseId}/documents`),
      listAll: (params?: any) => {
        // List all documents across all cases by fetching each case's documents
        return api<any>('/api/v1/cases')
          .then(async (casesResponse: any) => {
            const cases = casesResponse.cases || []
            const allDocuments: any[] = []

            // Fetch documents for each case
            for (const caseItem of cases) {
              try {
                const docsResponse = await api<any>(`/api/v1/cases/${caseItem.id}/documents`)
                const docs = docsResponse.documents || []
                // Add case info to each document
                docs.forEach((doc: any) => {
                  allDocuments.push({
                    ...doc,
                    case_name: caseItem.name,
                    case_number: caseItem.case_number
                  })
                })
              } catch (err) {
                console.error(`Failed to fetch documents for case ${caseItem.id}:`, err)
              }
            }

            // Sort by upload date (newest first)
            allDocuments.sort((a, b) => {
              const dateA = new Date(a.uploaded_at || 0).getTime()
              const dateB = new Date(b.uploaded_at || 0).getTime()
              return dateB - dateA
            })

            return { documents: allDocuments, total: allDocuments.length }
          })
      },
      get: (id: string) => api(`/api/v1/documents/${id}`),
      upload: (caseId: string | number, formData: FormData) => api(`/api/v1/cases/${caseId}/documents`, { method: 'POST', body: formData }),
      delete: (id: string) => api(`/api/v1/documents/${id}`, { method: 'DELETE' }),
      download: (id: string) => api(`/api/v1/documents/${id}/download`),
      content: (id: string) => api(`/api/v1/documents/${id}/content`)
    },

    // Search
    search: {
      query: (params: any) => api('/api/v1/search', { params }),
      hybrid: (data: any) => api('/api/v1/search/hybrid', { method: 'POST', body: data }),
      semantic: (data: any) => api('/api/v1/search/semantic', { method: 'POST', body: data }),
      suggest: (q: string) => api('/api/v1/search/suggestions', { params: { q } })
    },

    // Transcriptions
    transcriptions: {
      listForCase: (caseId: number) => api(`/api/v1/cases/${caseId}/transcriptions`),
      listAll: (params?: any) => {
        // List all transcriptions across all cases
        return api<any>('/api/v1/cases')
          .then(async (casesResponse: any) => {
            const cases = casesResponse.cases || []
            const allTranscriptions: any[] = []

            // Fetch transcriptions for each case
            for (const caseItem of cases) {
              try {
                const transResponse = await api<any>(`/api/v1/cases/${caseItem.id}/transcriptions`)
                const transcriptions = transResponse.transcriptions || []
                // Add case info to each transcription
                transcriptions.forEach((trans: any) => {
                  allTranscriptions.push({
                    ...trans,
                    case_name: caseItem.name,
                    case_number: caseItem.case_number
                  })
                })
              } catch (err) {
                console.error(`Failed to fetch transcriptions for case ${caseItem.id}:`, err)
              }
            }

            // Sort by created date (newest first)
            allTranscriptions.sort((a, b) => {
              const dateA = new Date(a.created_at || 0).getTime()
              const dateB = new Date(b.created_at || 0).getTime()
              return dateB - dateA
            })

            return { transcriptions: allTranscriptions, total: allTranscriptions.length }
          })
      },
      get: (id: number) => api(`/api/v1/transcriptions/${id}`),
      upload: (caseId: number, formData: FormData) =>
        api(`/api/v1/cases/${caseId}/transcriptions`, { method: 'POST', body: formData }),
      delete: (id: number) => api(`/api/v1/transcriptions/${id}`, { method: 'DELETE' }),
      download: (id: number, format: 'docx' | 'srt' | 'vtt' | 'txt' | 'json') =>
        api(`/api/v1/transcriptions/${id}/download/${format}`),

      // Summarization
      getSummary: (id: number) => api(`/api/v1/transcriptions/${id}/summary`),
      generateSummary: (id: number, options?: any) =>
        api(`/api/v1/transcriptions/${id}/summarize`, { method: 'POST', body: options || {} }),
      regenerateSummary: (id: number, components?: string[]) =>
        api(`/api/v1/transcriptions/${id}/summary/regenerate`, { method: 'POST', body: components }),
      quickSummary: (id: number) =>
        api(`/api/v1/transcriptions/${id}/summary/quick`, { method: 'POST' }),
      summaryStatus: (transcriptionId: number, taskId: string) =>
        api(`/api/v1/transcriptions/${transcriptionId}/summary/status/${taskId}`),

      // Key Moments
      toggleKeyMoment: (transcriptionId: number, segmentId: string, isKeyMoment: boolean) =>
        api(`/api/v1/transcriptions/${transcriptionId}/segments/${segmentId}/key-moment`, {
          method: 'PATCH',
          body: { is_key_moment: isKeyMoment }
        }),
      getKeyMoments: (transcriptionId: number) =>
        api(`/api/v1/transcriptions/${transcriptionId}/key-moments`),

      // Speakers
      updateSpeaker: (transcriptionId: number, speakerId: string, updates: { name: string, role?: string }) =>
        api(`/api/v1/transcriptions/${transcriptionId}/speakers/${speakerId}`, {
          method: 'PATCH',
          body: updates
        }),

      // Audio
      getAudio: (id: number) => api(`/api/v1/transcriptions/${id}/audio`)
    },

    // Stats & Analytics
    stats: {
      dashboard: () => api('/api/v1/stats/dashboard'),
      cases: () => api('/api/v1/stats/cases'),
      search: (days: number = 30) => api('/api/v1/stats/search', { params: { days } })
    },

    // Activity
    activity: {
      recent: (limit: number = 10) => api('/api/v1/activity/recent', { params: { limit } })
    },

    // Entities
    entities: {
      list: (params?: any) => api('/api/v1/entities', { params }),
      get: (id: string) => api(`/api/v1/entities/${id}`),
      byType: (type: string) => api(`/api/v1/entities/type/${type}`)
    },

    // Knowledge Graph
    graph: {
      get: (caseId?: string) => api('/api/v1/graph', { params: { case_id: caseId } }),
      node: (id: string) => api(`/api/v1/graph/nodes/${id}`),
      neighbors: (id: string) => api(`/api/v1/graph/nodes/${id}/neighbors`)
    }
  }
}
