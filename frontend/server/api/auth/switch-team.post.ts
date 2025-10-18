import { createError, readValidatedBody } from 'h3'
import { getUserSession, requireUserSession, setUserSession } from '#auth-utils'
import { z } from 'zod'

const bodySchema = z.object({
  teamId: z.string().uuid()
})

export default defineEventHandler(async (event) => {
  const { teamId } = await readValidatedBody(event, bodySchema.parse)
  const session = await requireUserSession(event)

  const accessToken = session.user?.accessToken
  if (!accessToken) {
    throw createError({ statusCode: 401, message: 'Missing access token' })
  }

  const config = useRuntimeConfig(event)
  const apiBase = config.public.apiBase

  const profile = await $fetch<{
    id: string
    keycloak_id: string
    email: string
    full_name?: string | null
    active_team?: { id: string; name: string; slug: string } | null
    memberships: Array<{
      team: { id: string; name: string; slug: string }
      role: string
    }>
  }>(`${apiBase}/api/v1/auth/switch-team`, {
    method: 'POST',
    body: { team_id: teamId },
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  })

  const teams = profile.memberships.map((membership) => ({
    id: membership.team.id,
    name: membership.team.name,
    slug: membership.team.slug,
    role: membership.role
  }))

  await setUserSession(event, {
    user: {
      ...session.user,
      id: profile.id,
      keycloakId: profile.keycloak_id,
      email: profile.email,
      fullName: profile.full_name ?? null,
      activeTeamId: profile.active_team?.id ?? null,
      teams
    }
  })

  const updatedSession = await getUserSession(event)

  return {
    user: updatedSession.user,
    loggedInAt: updatedSession.loggedInAt
  }
})
