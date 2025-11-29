import { createSharedComposable } from '@vueuse/core'

const _useDashboard = () => {
  const route = useRoute()
  const router = useRouter()
  const isNotificationsSlideoverOpen = ref(false)

  defineShortcuts({
    'g-h': {
      usingInput: false,
      handler: () => router.push('/')
    },
    'g-c': {
      usingInput: false,
      handler: () => router.push('/cases')
    },
    'g-s': {
      usingInput: false,
      handler: () => router.push('/settings')
    },
    'n': {
      usingInput: false,
      handler: () => isNotificationsSlideoverOpen.value = !isNotificationsSlideoverOpen.value
    }
  })

  watch(() => route.fullPath, () => {
    isNotificationsSlideoverOpen.value = false
  })

  return {
    isNotificationsSlideoverOpen
  }
}

export const useDashboard = createSharedComposable(_useDashboard)
