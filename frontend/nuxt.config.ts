// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    '@vueuse/nuxt'
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
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000'
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
  },

  vite: {
    optimizeDeps: {
      esbuildOptions: {
        supported: {
          'top-level-await': true
        }
      }
    },
    esbuild: {
      supported: {
        'top-level-await': true
      }
    }
  }
})
