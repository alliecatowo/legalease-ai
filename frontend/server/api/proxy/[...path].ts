import { readBody, createError } from 'h3'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const path = event.context.params?.path || ''
  const apiBase = config.apiBase || config.public.apiBase

  console.log('[Proxy] Received request:', {
    path,
    params: event.context.params,
    url: event.node.req.url
  })

  // Get the session to extract the access token
  const session = await getUserSession(event)
  const token = session.user?.accessToken

  // Forward the request to the backend API
  const url = `${apiBase}/api/${path}`

  console.log('[Proxy] Forwarding to:', url, 'hasToken:', !!token)

  const headers: Record<string, string> = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  // Forward the original method and body
  const method = event.method
  const body = method !== 'GET' && method !== 'HEAD'
    ? await readBody(event)
    : undefined

  try {
    const response = await $fetch(url, {
      method,
      headers,
      body
    })
    return response
  } catch (error: any) {
    throw createError({
      statusCode: error.statusCode || 500,
      message: error.data?.detail || error.message
    })
  }
})
