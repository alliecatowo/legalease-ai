// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    '@vueuse/nuxt',
    'nuxt-auth-utils'
  ],

  app: {
    head: {
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }
      ]
    }
  },

  devtools: {
    enabled: true
  },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    apiBase: process.env.NUXT_API_BASE_INTERNAL || 'https://api.localhost',
    session: {
      name: process.env.NUXT_SESSION_NAME || 'legalease-session',
      password: process.env.NUXT_SESSION_PASSWORD || 'please-change-this-session-password-32-chars',
      cookie: {
        sameSite: 'lax',
        secure: process.env.NODE_ENV === 'production'
      },
      maxAge: 60 * 60 * 24 * 7
    },
    keycloak: {
      clientSecret: process.env.KEYCLOAK_BACKEND_CLIENT_SECRET || ''
    },
    public: {
      appUrl: process.env.NUXT_PUBLIC_APP_URL || 'https://app.localhost',
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'https://api.localhost',
      keycloak: {
        baseUrl: process.env.NUXT_PUBLIC_KEYCLOAK_URL || 'https://auth.localhost',
        realm: process.env.NUXT_PUBLIC_KEYCLOAK_REALM || 'legalease',
        clientId: process.env.NUXT_PUBLIC_KEYCLOAK_CLIENT_ID || 'nuxt-dashboard',
        redirectUri: process.env.NUXT_PUBLIC_KEYCLOAK_REDIRECT_URI
          || `${process.env.NUXT_PUBLIC_APP_URL || 'https://app.localhost'}/api/auth/callback`
      }
    }
  },

  auth: {
    loadStrategy: 'client-only'
  },

  routeRules: {
    '/api/v1/**': {
      cors: true,
      proxy: {
        to: `${process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000'}/api/**`
      }
    }
  },

  compatibilityDate: '2024-07-11',

  icon: {
    serverBundle: {
      collections: ['lucide', 'simple-icons']
    },
    clientBundle: {
      scan: true,
      includeCustomCollections: true
    }
  },

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  },

  colorMode: {
    preference: 'dark',
    fallback: 'dark'
  }
})
