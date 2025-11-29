import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  onAuthStateChanged,
  sendPasswordResetEmail,
  updateProfile,
  type User
} from 'firebase/auth'

export interface AuthUser {
  uid: string
  email: string | null
  displayName: string | null
  photoURL: string | null
  emailVerified: boolean
}

export function useAuth() {
  const { $auth } = useNuxtApp()
  const router = useRouter()

  // Auth state
  const user = useState<AuthUser | null>('auth-user', () => null)
  const isLoading = useState<boolean>('auth-loading', () => true)
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

  // Initialize auth state listener
  const initAuth = (authInstance?: any) => {
    const auth = authInstance || $auth
    if (!auth) {
      isLoading.value = false
      return
    }

    onAuthStateChanged(auth, (firebaseUser) => {
      user.value = mapUser(firebaseUser)
      isLoading.value = false
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
    isAuthenticated,
    error,
    initAuth,
    signInWithEmail,
    signUpWithEmail,
    signInWithGoogle,
    logout,
    resetPassword,
    getIdToken
  }
}
