<script setup lang="ts">
import type { NavigationMenuItem } from '@nuxt/ui'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const open = ref(false)

// Error boundary state
const error = ref<Error | null>(null)
const errorInfo = ref<string>('')

// Catch errors from child components
onErrorCaptured((err, instance, info) => {
  console.error('Error caught in layout:', err, info)
  error.value = err
  errorInfo.value = info
  return false // Prevent error from propagating further
})

// Clear error when route changes
watch(() => route.path, () => {
  error.value = null
  errorInfo.value = ''
})

function clearError() {
  error.value = null
  errorInfo.value = ''
  router.push('/')
}

const links = [[{
  label: 'Dashboard',
  icon: 'i-lucide-layout-dashboard',
  to: '/',
  onSelect: () => {
    open.value = false
  }
}, {
  label: 'Cases',
  icon: 'i-lucide-folder',
  to: '/cases',
  onSelect: () => {
    open.value = false
  }
}, {
  label: 'Documents',
  icon: 'i-lucide-file-text',
  to: '/documents',
  onSelect: () => {
    open.value = false
  }
}, {
  label: 'Search',
  icon: 'i-lucide-search',
  to: '/search',
  onSelect: () => {
    open.value = false
  }
}, {
  label: 'Transcriptions',
  icon: 'i-lucide-mic',
  to: '/transcripts',
  onSelect: () => {
    open.value = false
  }
}, {
  label: 'Forensic Exports',
  icon: 'i-lucide-hard-drive',
  to: '/forensic-exports',
  onSelect: () => {
    open.value = false
  }
}], [{
  label: 'Settings',
  to: '/settings',
  icon: 'i-lucide-settings',
  onSelect: () => {
    open.value = false
  }
}]] satisfies NavigationMenuItem[][]

const groups = computed(() => [{
  id: 'links',
  label: 'Go to',
  items: links.flat()
}, {
  id: 'code',
  label: 'Code',
  items: [{
    id: 'source',
    label: 'View page source',
    icon: 'i-simple-icons-github',
    to: `https://github.com/nuxt-ui-templates/dashboard/blob/main/app/pages${route.path === '/' ? '/index' : route.path}.vue`,
    target: '_blank'
  }]
}])

onMounted(async () => {
  const cookie = useCookie('cookie-consent')
  if (cookie.value === 'accepted') {
    return
  }

  toast.add({
    title: 'We use first-party cookies to enhance your experience on our website.',
    duration: 0,
    close: false,
    actions: [{
      label: 'Accept',
      color: 'neutral',
      variant: 'outline',
      onClick: () => {
        cookie.value = 'accepted'
      }
    }, {
      label: 'Opt out',
      color: 'neutral',
      variant: 'ghost'
    }]
  })
})
</script>

<template>
  <UDashboardGroup unit="rem">
    <ClientOnly>
      <UDashboardSidebar
        id="default"
        v-model:open="open"
        collapsible
        resizable
        class="bg-elevated/25"
        :ui="{ footer: 'lg:border-t lg:border-default' }"
      >
      <template #header="{ collapsed }">
        <ClientOnly>
          <TeamsMenu :collapsed="collapsed" />
        </ClientOnly>
      </template>

      <template #default="{ collapsed }">
        <ClientOnly>
          <UDashboardSearchButton :collapsed="collapsed" class="bg-transparent ring-default" />

          <UNavigationMenu
            :collapsed="collapsed"
            :items="links[0]"
            orientation="vertical"
            tooltip
            popover
          />

          <div class="mt-auto space-y-2">
            <UDashboardSidebarCollapse
              variant="subtle"
              block
              :icon="collapsed ? 'i-lucide-chevron-right' : 'i-lucide-chevron-left'"
              :label="collapsed ? undefined : 'Collapse sidebar'"
            />

            <UNavigationMenu
              :collapsed="collapsed"
              :items="links[1]"
              orientation="vertical"
              tooltip
            />
          </div>
        </ClientOnly>
      </template>

      <template #footer="{ collapsed }">
        <ClientOnly>
          <UserMenu :collapsed="collapsed" />
        </ClientOnly>
      </template>
    </UDashboardSidebar>
    </ClientOnly>

    <ClientOnly>
      <UDashboardSearch :groups="groups" />
    </ClientOnly>

    <!-- Error Boundary Content -->
    <UDashboardPanel v-if="error">
      <div class="flex items-center justify-center h-full p-8">
        <UCard class="max-w-2xl">
          <div class="space-y-4">
            <div class="flex items-start gap-4">
              <UIcon name="i-lucide-alert-triangle" class="size-12 text-red-500 flex-shrink-0" />
              <div class="flex-1">
                <h2 class="text-2xl font-bold text-red-600 dark:text-red-400 mb-2">Something went wrong</h2>
                <p class="text-gray-600 dark:text-gray-400 mb-4">
                  An error occurred while rendering this page. You can navigate to another page using the sidebar.
                </p>
              </div>
            </div>

            <UCard class="bg-gray-50 dark:bg-gray-900">
              <div class="space-y-2">
                <div>
                  <p class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">Error Message:</p>
                  <code class="text-sm text-red-600 dark:text-red-400 block bg-white dark:bg-gray-800 p-2 rounded">
                    {{ error.message }}
                  </code>
                </div>

                <div v-if="errorInfo">
                  <p class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">Component:</p>
                  <code class="text-sm text-gray-600 dark:text-gray-400 block bg-white dark:bg-gray-800 p-2 rounded">
                    {{ errorInfo }}
                  </code>
                </div>

                <div v-if="error.stack">
                  <p class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">Stack Trace:</p>
                  <pre class="text-xs text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-800 p-2 rounded overflow-auto max-h-40">{{ error.stack }}</pre>
                </div>
              </div>
            </UCard>

            <div class="flex gap-3">
              <UButton
                label="Go to Dashboard"
                icon="i-lucide-home"
                color="primary"
                @click="clearError"
              />
              <UButton
                label="Reload Page"
                icon="i-lucide-refresh-cw"
                color="neutral"
                variant="outline"
                @click="() => { error = null; errorInfo = ''; router.go(0) }"
              />
            </div>
          </div>
        </UCard>
      </div>
    </UDashboardPanel>

    <!-- Normal Content -->
    <slot v-else />
  </UDashboardGroup>

  <ClientOnly>
    <NotificationsSlideover />
  </ClientOnly>
</template>
