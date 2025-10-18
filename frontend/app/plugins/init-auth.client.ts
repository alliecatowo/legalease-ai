export default defineNuxtPlugin(() => {
  const session = useUserSession()

  if (!session.ready.value) {
    session.fetch().catch((error) => {
      console.error('Failed to hydrate user session', error)
    })
  }
})
