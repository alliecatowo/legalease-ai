// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    '@vueuse/nuxt'
  ],

  devtools: {
    enabled: true
  },

  app: {
    head: {
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }
      ]
    }
  },

  css: ['~/assets/css/main.css'],

  colorMode: {
    preference: 'dark',
    fallback: 'dark'
  },

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
      // Set NUXT_PUBLIC_USE_EMULATORS=true to connect to Firebase emulators in dev
      useEmulators: process.env.NUXT_PUBLIC_USE_EMULATORS === 'true',
      // Transcription provider (gemini or chirp) - must match backend TRANSCRIPTION_PROVIDER
      transcriptionProvider: process.env.TRANSCRIPTION_PROVIDER || 'gemini',
      // Firebase client config (set via environment variables)
      firebase: {
        apiKey: process.env.FIREBASE_API_KEY || '',
        authDomain: process.env.FIREBASE_AUTH_DOMAIN || '',
        projectId: process.env.FIREBASE_PROJECT_ID || '',
        storageBucket: process.env.FIREBASE_STORAGE_BUCKET || '',
        messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID || '',
        appId: process.env.FIREBASE_APP_ID || ''
      }
    }
  },

  routeRules: {
    '/api/**': {
      cors: true,
      proxy: {
        to: `${process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000'}/api/**`
      }
    }
  },

  compatibilityDate: '2024-07-11',

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  },

  icon: {
    serverBundle: {
      collections: ['lucide', 'simple-icons']
    },
    clientBundle: {
      scan: true,
      includeCustomCollections: true
    }
  }
})
