export default defineNuxtRouteMiddleware(async (to) => {
  // Skip auth check for login and signup pages
  if (to.path === '/login' || to.path === '/signup') {
    return
  }

  const { user, isLoading } = useAuth()

  // Wait for auth state to be determined
  if (isLoading.value) {
    // On client side, wait for auth to load
    if (import.meta.client) {
      await new Promise<void>((resolve) => {
        const unwatch = watch(isLoading, (loading) => {
          if (!loading) {
            unwatch()
            resolve()
          }
        })
      })
    }
  }

  // Redirect to login if not authenticated
  if (!user.value) {
    return navigateTo('/login', { replace: true })
  }
})
