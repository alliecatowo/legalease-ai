export const useApi = () => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase

  const apiFetch = $fetch.create({
    baseURL: apiBase,
    onRequest({ options }) {
      // Add authorization headers if needed
      const token = useCookie('auth-token')
      if (token.value) {
        options.headers = new Headers(options.headers || {})
        options.headers.set('Authorization', `Bearer ${token.value}`)
      }
    },
    onResponseError({ response }) {
      // Handle API errors
      console.error('API Error:', response.status, response.statusText)
    },
  })

  // Create a typed wrapper
  const typedApiFetch = <T = any>(url: string, options?: any): Promise<T> => {
    return apiFetch(url, options)
  }

  return {
    apiFetch: typedApiFetch,
    apiBase,
  }
}
