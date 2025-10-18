declare module '#auth-utils' {
  interface TeamSummary {
    id: string
    name: string
    slug: string
    role: string
  }

  interface User {
    id: string
    email: string
    fullName?: string | null
    username?: string | null
    avatarUrl?: string | null
    bio?: string | null
    keycloakId?: string
    activeTeamId?: string | null
    teams?: TeamSummary[]
    accessToken?: string
  }

  interface UserSession {
    user?: User | null
    loggedInAt?: number
  }

  interface SecureSessionData {
    refreshToken?: string
    accessTokenExpiresAt?: number
  }
}

export {}
