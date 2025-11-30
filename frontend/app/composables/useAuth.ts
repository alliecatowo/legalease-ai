import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  onAuthStateChanged,
  sendPasswordResetEmail,
  updateProfile,
  type User,
  type Auth
} from 'firebase/auth'

export interface AuthUser {
  uid: string
  email: string | null
  displayName: string | null
  photoURL: string | null
  emailVerified: boolean
}

// Global promise that resolves when auth state is determined
// This follows VueFire's pattern for reliable auth checking
let authReadyPromise: Promise<AuthUser | null> | null = null
let authReadyResolve: ((user: AuthUser | null) => void) | null = null

export function useAuth() {
  const { $auth } = useNuxtApp()
  const router = useRouter()

  // Auth state - using shared state across all composable instances
  const user = useState<AuthUser | null>('auth-user', () => null)
  const isLoading = useState<boolean>('auth-loading', () => true)
  const isReady = useState<boolean>('auth-ready', () => false)
  const error = useState<string | null>('auth-error', () => null)

  // Computed
  const isAuthenticated = computed(() => !!user.value)

  // Convert Firebase User to AuthUser
  const mapUser = (firebaseUser: User | null): AuthUser | null => {
    if (!firebaseUser) return null
    return {
      uid: firebaseUser.uid,
      email: firebaseUser.email,
      displayName: firebaseUser.displayName,
      photoURL: firebaseUser.photoURL,
      emailVerified: firebaseUser.emailVerified
    }
  }

  // VueFire-style getCurrentUser() - returns a Promise that resolves when auth is ready
  // This is the KEY pattern for reliable auth in middleware
  const getCurrentUser = (): Promise<AuthUser | null> => {
    // If auth is already ready, return current user immediately
    if (isReady.value) {
      return Promise.resolve(user.value)
    }

    // If we're already waiting for auth, return the existing promise
    if (authReadyPromise) {
      return authReadyPromise
    }

    // Create a new promise that will be resolved when onAuthStateChanged fires
    authReadyPromise = new Promise<AuthUser | null>((resolve) => {
      authReadyResolve = resolve
    })

    return authReadyPromise
  }

  // Initialize auth state listener
  const initAuth = (authInstance?: Auth) => {
    const auth = authInstance || $auth
    if (!auth) {
      isLoading.value = false
      isReady.value = true
      if (authReadyResolve) {
        authReadyResolve(null)
        authReadyResolve = null
      }
      return
    }

    // Set up the auth state listener - this is the source of truth
    onAuthStateChanged(auth, (firebaseUser) => {
      const mappedUser = mapUser(firebaseUser)
      user.value = mappedUser
      isLoading.value = false

      // Mark auth as ready and resolve any waiting promises
      if (!isReady.value) {
        isReady.value = true
        if (authReadyResolve) {
          authReadyResolve(mappedUser)
          authReadyResolve = null
        }
      }
    })
  }

  // Sign in with email/password
  const signInWithEmail = async (email: string, password: string) => {
    if (!$auth) throw new Error('Auth not initialized')

    error.value = null
    isLoading.value = true

    try {
      const result = await signInWithEmailAndPassword($auth, email, password)
      user.value = mapUser(result.user)
      return result.user
    } catch (e: any) {
      error.value = getErrorMessage(e.code)
      throw e
    } finally {
      isLoading.value = false
    }
  }

  // Sign up with email/password
  const signUpWithEmail = async (email: string, password: string, displayName?: string) => {
    if (!$auth) throw new Error('Auth not initialized')

    error.value = null
    isLoading.value = true

    try {
      const result = await createUserWithEmailAndPassword($auth, email, password)

      // Update display name if provided
      if (displayName) {
        await updateProfile(result.user, { displayName })
      }

      user.value = mapUser(result.user)
      return result.user
    } catch (e: any) {
      error.value = getErrorMessage(e.code)
      throw e
    } finally {
      isLoading.value = false
    }
  }

  // Sign in with Google
  const signInWithGoogle = async () => {
    if (!$auth) throw new Error('Auth not initialized')

    error.value = null
    isLoading.value = true

    try {
      const provider = new GoogleAuthProvider()
      const result = await signInWithPopup($auth, provider)
      user.value = mapUser(result.user)
      return result.user
    } catch (e: any) {
      error.value = getErrorMessage(e.code)
      throw e
    } finally {
      isLoading.value = false
    }
  }

  // Sign out
  const logout = async () => {
    if (!$auth) throw new Error('Auth not initialized')

    try {
      await signOut($auth)
      user.value = null
      router.push('/login')
    } catch (e: any) {
      error.value = getErrorMessage(e.code)
      throw e
    }
  }

  // Reset password
  const resetPassword = async (email: string) => {
    if (!$auth) throw new Error('Auth not initialized')

    error.value = null

    try {
      await sendPasswordResetEmail($auth, email)
    } catch (e: any) {
      error.value = getErrorMessage(e.code)
      throw e
    }
  }

  // Get Firebase ID token for API calls
  const getIdToken = async (): Promise<string | null> => {
    if (!$auth?.currentUser) return null
    return await $auth.currentUser.getIdToken()
  }

  // Map Firebase error codes to user-friendly messages
  const getErrorMessage = (code: string): string => {
    const errorMessages: Record<string, string> = {
      'auth/email-already-in-use': 'This email is already registered',
      'auth/invalid-email': 'Invalid email address',
      'auth/operation-not-allowed': 'This sign-in method is not enabled',
      'auth/weak-password': 'Password is too weak',
      'auth/user-disabled': 'This account has been disabled',
      'auth/user-not-found': 'No account found with this email',
      'auth/wrong-password': 'Incorrect password',
      'auth/invalid-credential': 'Invalid email or password',
      'auth/too-many-requests': 'Too many attempts. Please try again later',
      'auth/popup-closed-by-user': 'Sign-in popup was closed',
      'auth/cancelled-popup-request': 'Sign-in was cancelled'
    }
    return errorMessages[code] || 'An error occurred. Please try again.'
  }

  return {
    user,
    isLoading,
    isReady,
    isAuthenticated,
    error,
    initAuth,
    getCurrentUser,
    signInWithEmail,
    signUpWithEmail,
    signInWithGoogle,
    logout,
    resetPassword,
    getIdToken
  }
}
