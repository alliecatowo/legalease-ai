// API Response Types
interface CaseListResponse {
  cases: any[]
  total: number
  page: number
  page_size: number
}

export const useApi = () => {
  const config = useRuntimeConfig()
  // Use the frontend proxy instead of calling the backend directly
  const baseURL = '/api/proxy'

  const session = useUserSession()

  const api = $fetch.create({
    baseURL,
    onRequest({ options }) {
      options.credentials = 'include'
      // Token is handled by the proxy on the server side
    },
    onResponseError({ response }) {
      if (response.status === 401 && import.meta.client) {
        const session = useUserSession()
        session.clear()
        navigateTo('/login')
        return
      }

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
    // User Profile
    user: {
      getProfile: () => api('/v1/auth/profile'),
      updateProfile: (data: any) => api('/v1/auth/profile', { method: 'PATCH', body: data }),
      getMe: () => api('/v1/auth/profile')  // Alias for getProfile
    },

    // Teams
    teams: {
      list: () => api('/v1/auth/teams'),
      switchTeam: (teamId: string) => api('/v1/auth/switch-team', { method: 'POST', body: { team_id: teamId } })
    },

    // Cases
    cases: {
      list: () => api<CaseListResponse>('/v1/cases'),
      get: (id: string) => api(`/v1/cases/${id}`),
      create: (data: any) => api('/v1/cases', { method: 'POST', body: data }),
      update: (id: string, data: any) => api(`/v1/cases/${id}`, { method: 'PUT', body: data }),
      delete: (id: string) => api(`/v1/cases/${id}`, { method: 'DELETE' }),
      load: (id: string) => api(`/v1/cases/${id}/load`, { method: 'POST' }),
      unload: (id: string) => api(`/v1/cases/${id}/unload`, { method: 'POST' }),
      archive: (id: string) => api(`/v1/cases/${id}/archive`, { method: 'POST' })
    },

    // Documents
    documents: {
      listByCase: (caseId: string | number) => api(`/v1/cases/${caseId}/documents`),
      listAll: (params?: { page?: number; page_size?: number; case_id?: number }) => {
        // Use the new efficient endpoint that includes case info in a single query
        return api<any>('/v1/documents', { params })
      },
      get: (id: string) => api(`/v1/documents/${id}`),
      upload: (caseId: string | number, formData: FormData) => api(`/v1/cases/${caseId}/documents`, { method: 'POST', body: formData }),
      delete: (id: string) => api(`/v1/documents/${id}`, { method: 'DELETE' }),
      download: (id: string) => api(`/v1/documents/${id}/download`),
      content: (id: string) => api(`/v1/documents/${id}/content`)
    },

    // Search
    search: {
      query: (params: any) => api('/v1/search', { params }),
      hybrid: (data: any) => api('/v1/search/hybrid', { method: 'POST', body: data }),
      semantic: (data: any) => api('/v1/search/semantic', { method: 'POST', body: data }),
      suggest: (q: string) => api('/v1/search/suggestions', { params: { q } })
    },

    // Transcriptions
    transcriptions: {
      listForCase: (caseId: number) => api(`/v1/cases/${caseId}/transcriptions`),
      listAll: (params?: { page?: number; page_size?: number; case_id?: number }) => {
        // Use the new paginated endpoint
        return api<any>('/v1/transcriptions', { params })
      },
      get: (id: number) => api(`/v1/transcriptions/${id}`),
      upload: (caseId: number, formData: FormData) =>
        api(`/v1/cases/${caseId}/transcriptions`, { method: 'POST', body: formData }),
      delete: (id: number) => api(`/v1/transcriptions/${id}`, { method: 'DELETE' }),
      download: (id: number, format: 'docx' | 'srt' | 'vtt' | 'txt' | 'json') =>
        api(`/v1/transcriptions/${id}/download/${format}`),

      // Summarization
      getSummary: (id: number) => api(`/v1/transcriptions/${id}/summary`),
      generateSummary: (id: number, options?: any) =>
        api(`/v1/transcriptions/${id}/summarize`, { method: 'POST', body: options || {} }),
      regenerateSummary: (id: number, components?: string[]) =>
        api(`/v1/transcriptions/${id}/summary/regenerate`, { method: 'POST', body: components }),
      quickSummary: (id: number) =>
        api(`/v1/transcriptions/${id}/summary/quick`, { method: 'POST' }),
      summaryStatus: (transcriptionId: number, taskId: string) =>
        api(`/v1/transcriptions/${transcriptionId}/summary/status/${taskId}`),

      // Key Moments
      toggleKeyMoment: (transcriptionId: number, segmentId: string, isKeyMoment: boolean) =>
        api(`/v1/transcriptions/${transcriptionId}/segments/${segmentId}/key-moment`, {
          method: 'PATCH',
          body: { is_key_moment: isKeyMoment }
        }),
      getKeyMoments: (transcriptionId: number) =>
        api(`/v1/transcriptions/${transcriptionId}/key-moments`),

      // Speakers
      updateSpeaker: (transcriptionId: number, speakerId: string, updates: { name: string, role?: string }) =>
        api(`/v1/transcriptions/${transcriptionId}/speakers/${speakerId}`, {
          method: 'PATCH',
          body: updates
        }),

      // Audio
      getAudio: (id: number) => api(`/v1/transcriptions/${id}/audio`)
    },

    // Forensic Exports
    forensicExports: {
      listForCase: (caseId: number) => api(`/v1/cases/${caseId}/forensic-exports`),
      listAll: () => api('/v1/forensic-exports'),
      get: (id: number) => api(`/v1/forensic-exports/${id}`),
      scan: (caseId: number, path: string) => api(`/v1/cases/${caseId}/forensic-exports/scan`, {
        method: 'POST',
        body: { path }
      }),
      verify: (id: number) => api(`/v1/forensic-exports/${id}/verify`, { method: 'POST' }),
      delete: (id: number) => api(`/v1/forensic-exports/${id}`, { method: 'DELETE' }),
      getReportUrl: (id: number) => `${baseURL}/v1/forensic-exports/${id}/report`,
      listFiles: (id: number, subpath?: string) => api(`/v1/forensic-exports/${id}/files${subpath ? `?subpath=${encodeURIComponent(subpath)}` : ''}`)
    },

    // Stats & Analytics
    stats: {
      dashboard: () => api('/v1/stats/dashboard'),
      cases: () => api('/v1/stats/cases'),
      search: (days: number = 30) => api('/v1/stats/search', { params: { days } })
    },

    // Activity
    activity: {
      recent: (limit: number = 10) => api('/v1/activity/recent', { params: { limit } })
    },

    // Entities
    entities: {
      list: (params?: any) => api('/v1/entities', { params }),
      get: (id: string) => api(`/v1/entities/${id}`),
      byType: (type: string) => api(`/v1/entities/type/${type}`)
    },

    // Knowledge Graph
    graph: {
      get: (caseId?: string) => api('/v1/graph', { params: { case_id: caseId } }),
      node: (id: string) => api(`/v1/graph/nodes/${id}`),
      neighbors: (id: string) => api(`/v1/graph/nodes/${id}/neighbors`)
    }
  }
}
