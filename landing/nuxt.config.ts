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
    baseURL: process.env.NUXT_APP_BASE_URL || '/',
    cdnURL: process.env.NUXT_APP_BASE_URL || '/',
    head: {
      link: [
        { rel: 'icon', type: 'image/x-icon', href: `${process.env.NUXT_APP_BASE_URL || ''}/favicon.ico` }
      ]
    }
  },

  routeRules: {
    '/docs': { redirect: '/docs/getting-started', prerender: true }
  },

  compatibilityDate: '2024-07-11',

  ssr: true,

  nitro: {
    baseURL: process.env.NUXT_APP_BASE_URL || '/',
    prerender: {
      routes: [
        '/'
      ],
      crawlLinks: true,
      failOnError: false
    }
  },

  vite: {
    base: process.env.NUXT_APP_BASE_URL || '/'
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
