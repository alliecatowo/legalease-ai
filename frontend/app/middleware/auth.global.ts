import { getUserSession } from '#auth-utils'

export default defineNuxtRouteMiddleware(async (to) => {
  if (import.meta.server) {
    const event = useRequestEvent()
    if (!event) {
      return
    }
    const session = await getUserSession(event)
    const loggedIn = Boolean(session.user)

    if (!loggedIn && to.path !== '/login') {
      return navigateTo('/login')
    }
    if (loggedIn && to.path === '/login') {
      return navigateTo('/')
    }
    return
  }

  const session = useUserSession()

  if (!session.ready.value) {
    return
  }

  if (!session.loggedIn.value && to.path !== '/login') {
    return navigateTo('/login')
  }

  if (session.loggedIn.value && to.path === '/login') {
    return navigateTo('/')
  }
})
