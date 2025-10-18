import { deleteCookie, createError, getCookie, getQuery, H3Event, sendRedirect, setCookie } from 'h3'
import { URLSearchParams } from 'node:url'

interface TokenResponse {
  access_token: string
  refresh_token?: string
  expires_in: number
  token_type: string
  id_token?: string
}

interface BackendProfile {
  id: string
  keycloak_id: string
  email: string
  full_name?: string | null
  active_team?: {
    id: string
    name: string
    slug: string
  } | null
  memberships: Array<{
    team: {
      id: string
      name: string
      slug: string
    }
    role: string
  }>
}

function buildKeycloakTokenURL(event: H3Event) {
  const config = useRuntimeConfig(event)
  const { public: publicConfig } = config
  const keycloak = publicConfig.keycloak
  if (!keycloak?.baseUrl || !keycloak?.realm) {
    throw createError({ statusCode: 500, message: 'Keycloak configuration missing' })
  }
  return `${keycloak.baseUrl}/realms/${keycloak.realm}/protocol/openid-connect/token`
}

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const { public: publicConfig } = config
  const keycloak = publicConfig.keycloak
  const appUrl = publicConfig.appUrl || '/'

  const query = getQuery(event)
  const code = typeof query.code === 'string' ? query.code : undefined
  const state = typeof query.state === 'string' ? query.state : undefined

  const storedState = getCookie(event, 'kc_oauth_state')
  const verifier = getCookie(event, 'kc_pkce_verifier')

  deleteCookie(event, 'kc_oauth_state', { path: '/' })
  deleteCookie(event, 'kc_pkce_verifier', { path: '/' })

  if (!code || !state || !verifier || state !== storedState) {
    throw createError({ statusCode: 400, message: 'Invalid authorization response' })
  }

  const tokenURL = buildKeycloakTokenURL(event)
  const params = new URLSearchParams()
  params.set('grant_type', 'authorization_code')
  params.set('code', code)
  params.set('redirect_uri', keycloak.redirectUri)
  params.set('client_id', keycloak.clientId)
  params.set('code_verifier', verifier)

  const clientSecret = config.keycloak.clientSecret
  if (clientSecret) {
    params.set('client_secret', clientSecret)
  }

  let tokenResponse: TokenResponse
  try {
    tokenResponse = await $fetch<TokenResponse>(tokenURL, {
      method: 'POST',
      body: params.toString(),
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    })
  } catch (error) {
    console.error('Failed to exchange authorization code', error)
    throw createError({ statusCode: 401, message: 'Authentication failed' })
  }

  // Fetch the user profile from the backend to bootstrap membership data
  let profile: BackendProfile | null = null
  try {
    profile = await $fetch<BackendProfile>(`${publicConfig.apiBase}/api/v1/auth/profile`, {
      headers: {
        Authorization: `Bearer ${tokenResponse.access_token}`
      }
    })
  } catch (error) {
    console.error('Failed to load profile from backend', error)
    // Continue with minimal user data
  }

  const teams = profile?.memberships?.map((membership) => ({
    id: membership.team.id,
    name: membership.team.name,
    slug: membership.team.slug,
    role: membership.role
  })) ?? []

  await setUserSession(event, {
    user: {
      id: profile?.id ?? profile?.keycloak_id ?? 'unknown-user',
      keycloakId: profile?.keycloak_id,
      email: profile?.email ?? '',
      fullName: profile?.full_name ?? null,
      activeTeamId: profile?.active_team?.id ?? null,
      teams,
      accessToken: tokenResponse.access_token
    },
    secure: {
      refreshToken: tokenResponse.refresh_token,
      accessTokenExpiresAt: Date.now() + tokenResponse.expires_in * 1000
    },
    loggedInAt: Date.now()
  })

  // Clear initial auth cookies explicitly
  deleteCookie(event, 'kc_oauth_state', { path: '/' })
  deleteCookie(event, 'kc_pkce_verifier', { path: '/' })

  return sendRedirect(event, appUrl)
})
