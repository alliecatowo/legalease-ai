export function useFirebase() {
  const nuxtApp = useNuxtApp()

  return {
    firebase: nuxtApp.$firebase,
    firestore: nuxtApp.$firestore,
    storage: nuxtApp.$storage,
    auth: nuxtApp.$auth
  }
}
