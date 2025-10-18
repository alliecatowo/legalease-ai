import { setCookie, sendRedirect, createError } from 'h3'
import { createHash, randomBytes } from 'node:crypto'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const { public: publicConfig } = config

  const keycloakConfig = publicConfig.keycloak
  if (!keycloakConfig?.baseUrl || !keycloakConfig?.realm) {
    throw createError({ statusCode: 500, message: 'Keycloak configuration missing' })
  }

  const verifier = randomBytes(32).toString('base64url')
  const state = randomBytes(24).toString('base64url')
  const challenge = createHash('sha256').update(verifier).digest('base64url')

  const redirectUri = keycloakConfig.redirectUri
  const authorizeURL = new URL(`${keycloakConfig.baseUrl}/realms/${keycloakConfig.realm}/protocol/openid-connect/auth`)
  authorizeURL.searchParams.set('client_id', keycloakConfig.clientId)
  authorizeURL.searchParams.set('response_type', 'code')
  authorizeURL.searchParams.set('redirect_uri', redirectUri)
  authorizeURL.searchParams.set('scope', 'openid profile email')
  authorizeURL.searchParams.set('code_challenge', challenge)
  authorizeURL.searchParams.set('code_challenge_method', 'S256')
  authorizeURL.searchParams.set('state', state)

  const cookieOptions = {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax' as const,
    path: '/',
    maxAge: 300
  }

  setCookie(event, 'kc_pkce_verifier', verifier, cookieOptions)
  setCookie(event, 'kc_oauth_state', state, cookieOptions)

  return sendRedirect(event, authorizeURL.toString())
})
