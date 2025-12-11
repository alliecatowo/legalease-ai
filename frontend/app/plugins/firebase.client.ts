import { initializeApp, type FirebaseApp } from 'firebase/app'
import { getFirestore, type Firestore } from 'firebase/firestore'
import { getStorage, type FirebaseStorage } from 'firebase/storage'
import { getAuth, type Auth } from 'firebase/auth'
import { getFunctions, type Functions } from 'firebase/functions'

/**
 * Provider storage requirements (must match backend provider capabilities)
 * Each transcription provider declares whether it needs production GCS or can use emulator
 */
const PROVIDER_REQUIRES_PRODUCTION_STORAGE: Record<string, boolean> = {
  chirp: true, // Speech API requires real GCS URIs
  gemini: false // Gemini can download from emulator, no GCS dependency
}

export default defineNuxtPlugin(async () => {
  const config = useRuntimeConfig()
  const firebaseConfig = config.public.firebase

  // Only initialize if we have a valid config (projectId is required)
  if (!firebaseConfig.projectId) {
    console.warn('Firebase config not set. Skipping Firebase initialization.')
    return {
      provide: {
        firebase: null as FirebaseApp | null,
        firestore: null as Firestore | null,
        storage: null as FirebaseStorage | null,
        auth: null as Auth | null,
        functions: null as Functions | null
      }
    }
  }

  const app = initializeApp(firebaseConfig)
  const firestore = getFirestore(app)
  const storage = getStorage(app)
  const auth = getAuth(app)
  const functions = getFunctions(app, 'us-central1')

  // Connect services to emulators when enabled
  // Set NUXT_PUBLIC_USE_EMULATORS=true to use emulators
  const useEmulators = import.meta.dev && config.public.useEmulators
  if (useEmulators) {
    const { connectFirestoreEmulator } = await import('firebase/firestore')
    const { connectAuthEmulator } = await import('firebase/auth')
    const { connectFunctionsEmulator } = await import('firebase/functions')

    // Check if current transcription provider requires production storage
    const provider = config.public.transcriptionProvider as string
    const requiresProductionStorage = PROVIDER_REQUIRES_PRODUCTION_STORAGE[provider] ?? false

    console.log('🔧 Connecting to Firebase Emulator Suite...')
    console.log(`📝 Transcription provider: ${provider}`)

    try {
      connectFirestoreEmulator(firestore, 'localhost', 8080)
      connectAuthEmulator(auth, 'http://localhost:9099', { disableWarnings: true })
      connectFunctionsEmulator(functions, 'localhost', 5001)

      if (requiresProductionStorage) {
        console.log('⚠️  Storage uses production (provider requires real GCS)')
        console.log('✅ Connected to emulators (Firestore, Auth, Functions)')
      } else {
        const { connectStorageEmulator } = await import('firebase/storage')
        connectStorageEmulator(storage, 'localhost', 9199)
        console.log('✅ Connected to emulators (Firestore, Auth, Functions, Storage)')
      }
    } catch (error) {
      console.warn('⚠️ Emulator connection failed:', error)
    }
  } else if (import.meta.dev) {
    console.log('🔥 Using production Firebase (emulators disabled)')
  }

  const { initAuth } = useAuth()
  initAuth(auth)

  return {
    provide: {
      firebase: app,
      firestore,
      storage,
      auth,
      functions
    }
  }
})
