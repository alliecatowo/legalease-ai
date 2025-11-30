export default defineNuxtRouteMiddleware(async (to) => {
  // Skip auth check for public pages to prevent redirect loops
  const publicPaths = ['/login', '/signup', '/forgot-password']
  if (publicPaths.includes(to.path)) {
    return
  }

  // Only run auth check on client side - server doesn't have Firebase auth state
  if (import.meta.server) {
    return
  }

  const { getCurrentUser } = useAuth()

  // VueFire pattern: await getCurrentUser() which resolves when Firebase
  // has determined the auth state (either logged in or not)
  // This is much more reliable than watching isLoading
  const user = await getCurrentUser()

  // Redirect to login if not authenticated, preserving the original path
  if (!user) {
    return navigateTo({
      path: '/login',
      query: { redirect: to.fullPath }
    }, { replace: true })
  }
})
