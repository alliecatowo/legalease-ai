export default defineEventHandler(async (event) => {
  const session = await getUserSession(event)
  return {
    user: session.user ?? null,
    loggedInAt: session.loggedInAt ?? null
  }
})
