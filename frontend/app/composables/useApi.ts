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
        toast.add({
          title: 'Error',
          description: response._data?.detail || response.statusText || 'An error occurred',
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
      list: () => api('/api/v1/transcriptions'),
      get: (id: string) => api(`/api/v1/transcriptions/${id}`),
      create: (formData: FormData) => api('/api/v1/transcriptions', { method: 'POST', body: formData }),
      bulkCreate: (formData: FormData) => api('/api/v1/transcriptions/bulk', { method: 'POST', body: formData }),
      delete: (id: string) => api(`/api/v1/transcriptions/${id}`, { method: 'DELETE' }),
      export: (id: string, format: 'docx' | 'srt' | 'vtt') =>
        api(`/api/v1/transcriptions/${id}/export/${format}`)
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
