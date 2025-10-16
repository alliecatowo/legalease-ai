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
    baseURL: '/',
    cdnURL: '/',
    head: {
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
        { rel: 'alternate icon', type: 'image/x-icon', href: '/favicon.ico' }
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
    baseURL: '/',
    prerender: {
      routes: [
        '/'
      ],
      crawlLinks: true,
      failOnError: false
    }
  },

  vite: {
    base: '/'
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
