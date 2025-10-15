// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/image',
    '@nuxt/ui',
    '@nuxt/content',
    '@vueuse/nuxt',
    'nuxt-og-image'
  ],

  devtools: {
    enabled: true
  },

  css: ['~/assets/css/main.css'],

  app: {
    baseURL: process.env.NODE_ENV === 'production' ? '/legalease-ai/' : '/',
    cdnURL: process.env.NODE_ENV === 'production' ? '/legalease-ai/' : '/',
    head: {
      link: [
        { rel: 'icon', type: 'image/x-icon', href: (process.env.NODE_ENV === 'production' ? '/legalease-ai' : '') + '/favicon.ico' }
      ]
    }
  },

  routeRules: {
    '/docs': { redirect: '/docs/getting-started', prerender: true }
  },

  compatibilityDate: '2024-07-11',

  ssr: true,

  nitro: {
    preset: 'static',
    baseURL: process.env.NODE_ENV === 'production' ? '/legalease-ai/' : '/',
    prerender: {
      routes: [
        '/'
      ],
      crawlLinks: true,
      failOnError: false
    }
  },

  vite: {
    base: process.env.NODE_ENV === 'production' ? '/legalease-ai/' : '/'
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
