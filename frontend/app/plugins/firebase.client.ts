import { initializeApp, type FirebaseApp } from 'firebase/app'
import { getFirestore, type Firestore } from 'firebase/firestore'
import { getStorage, type FirebaseStorage } from 'firebase/storage'
import { getAuth, type Auth } from 'firebase/auth'

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
        auth: null as Auth | null
      }
    }
  }

  const app = initializeApp(firebaseConfig)
  const firestore = getFirestore(app)
  const storage = getStorage(app)
  const auth = getAuth(app)

  // TEMPORARY: Always connect to emulators for testing
  const { connectFirestoreEmulator } = await import('firebase/firestore')
  const { connectStorageEmulator } = await import('firebase/storage')
  const { connectAuthEmulator } = await import('firebase/auth')

  console.log('🔧 Connecting to Firebase Emulators...')
  try {
    connectFirestoreEmulator(firestore, 'localhost', 8080)
    connectStorageEmulator(storage, 'localhost', 9199)
    connectAuthEmulator(auth, 'http://localhost:9099')
    console.log('✅ Connected to emulators')
  } catch (error) {
    console.error('❌ Failed to connect to emulators:', error)
  }

  const { initAuth } = useAuth()
  initAuth(auth)

  return {
    provide: {
      firebase: app,
      firestore,
      storage,
      auth
    }
  }
})
