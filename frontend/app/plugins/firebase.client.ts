import { initializeApp, type FirebaseApp } from 'firebase/app'
import { getFirestore, type Firestore } from 'firebase/firestore'
import { getStorage, type FirebaseStorage } from 'firebase/storage'
import { getAuth, type Auth } from 'firebase/auth'

export default defineNuxtPlugin(() => {
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

  return {
    provide: {
      firebase: app,
      firestore,
      storage,
      auth
    }
  }
})
