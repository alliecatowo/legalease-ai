import { setCookie, deleteCookie } from 'h3'

export default defineEventHandler(async (event) => {
  // Set access token cookie for browser-to-API communication
  const session = await getUserSession(event)

  if (session.user?.accessToken) {
    setCookie(event, 'kc_access_token', session.user.accessToken, {
      httpOnly: false, // Browser needs to read it
      secure: true,
      sameSite: 'lax',
      path: '/'
      // No domain - defaults to current domain
    })
  } else {
    // Clear cookie if no token
    deleteCookie(event, 'kc_access_token')
  }
})
