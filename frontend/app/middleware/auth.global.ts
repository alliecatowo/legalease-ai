export default defineNuxtRouteMiddleware(async (to) => {
  if (import.meta.server) {
    return
  }

  const session = useUserSession()

  if (!session.ready.value && !session.loggedIn.value) {
    await session.fetch().catch(() => {})
  }

  if (!session.loggedIn.value && to.path !== '/login') {
    return navigateTo('/login')
  }

  if (session.loggedIn.value && to.path === '/login') {
    return navigateTo('/')
  }
})
