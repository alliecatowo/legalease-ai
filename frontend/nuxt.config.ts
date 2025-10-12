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

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000'
    }
  },

  routeRules: {
    '/api/**': {
      proxy: {
        to: `${process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000'}/api/**`
      }
    },
    '/documents/**': { ssr: false },
    '/documents': { ssr: false },
    '/search': { ssr: false },
    '/transcripts/**': { ssr: false },
    '/transcripts': { ssr: false },
    '/transcription': { ssr: false }
  },

  compatibilityDate: '2024-07-11',

  icon: {
    serverBundle: {
      collections: ['lucide', 'simple-icons']
    },
    clientBundle: {
      // Include all icons in client bundle to prevent loading issues
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
  }
})
