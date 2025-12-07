<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

defineProps<{
  collapsed?: boolean
}>()

const colorMode = useColorMode()
const appConfig = useAppConfig()
const { user: authUser, isReady: authReady, logout } = useAuth()

const colors = ['red', 'orange', 'amber', 'yellow', 'lime', 'green', 'emerald', 'teal', 'cyan', 'sky', 'blue', 'indigo', 'violet', 'purple', 'fuchsia', 'pink', 'rose']
const neutrals = ['slate', 'gray', 'zinc', 'neutral', 'stone']

// Computed user based on auth state - only show real data when auth is ready
const user = computed(() => {
  if (authUser.value) {
    return {
      name: authUser.value.displayName || authUser.value.email || 'User',
      avatar: authUser.value.photoURL
        ? {
            src: authUser.value.photoURL,
            alt: authUser.value.displayName || 'User'
          }
        : undefined
    }
  }
  return null
})

const items = computed<DropdownMenuItem[][]>(() => {
  if (!user.value) return []
  return [[{
    type: 'label',
    label: user.value.name,
    avatar: user.value.avatar
  }], [{
    label: 'Profile',
    icon: 'i-lucide-user',
    to: '/settings'
  }, {
    label: 'Settings',
    icon: 'i-lucide-settings',
    to: '/settings'
  }], [{
    label: 'Theme',
    icon: 'i-lucide-palette',
    children: [{
      label: 'Primary',
      slot: 'chip',
      chip: appConfig.ui.colors.primary,
      content: {
        align: 'center',
        collisionPadding: 16
      },
      children: colors.map(color => ({
        label: color,
        chip: color,
        slot: 'chip',
        checked: appConfig.ui.colors.primary === color,
        type: 'checkbox',
        onSelect: (e) => {
          e.preventDefault()
          appConfig.ui.colors.primary = color
        }
      }))
    }, {
      label: 'Neutral',
      slot: 'chip',
      chip: appConfig.ui.colors.neutral === 'neutral' ? 'old-neutral' : appConfig.ui.colors.neutral,
      content: {
        align: 'end',
        collisionPadding: 16
      },
      children: neutrals.map(color => ({
        label: color,
        chip: color === 'neutral' ? 'old-neutral' : color,
        slot: 'chip',
        type: 'checkbox',
        checked: appConfig.ui.colors.neutral === color,
        onSelect: (e) => {
          e.preventDefault()
          appConfig.ui.colors.neutral = color
        }
      }))
    }]
  }, {
    label: 'Appearance',
    icon: 'i-lucide-sun-moon',
    children: [{
      label: 'Light',
      icon: 'i-lucide-sun',
      type: 'checkbox',
      checked: colorMode.value === 'light',
      onSelect(e: Event) {
        e.preventDefault()
        colorMode.preference = 'light'
      }
    }, {
      label: 'Dark',
      icon: 'i-lucide-moon',
      type: 'checkbox',
      checked: colorMode.value === 'dark',
      onUpdateChecked(checked: boolean) {
        if (checked) {
          colorMode.preference = 'dark'
        }
      },
      onSelect(e: Event) {
        e.preventDefault()
      }
    }]
  }], [{
    label: 'Log out',
    icon: 'i-lucide-log-out',
    onSelect: () => logout()
  }]]
})
</script>

<template>
  <!-- Show loading skeleton while auth initializes -->
  <div v-if="!authReady" class="p-2">
    <USkeleton class="h-8 w-full rounded" />
  </div>

  <!-- Show user menu when authenticated -->
  <UDropdownMenu
    v-else-if="user"
    :items="items"
    :content="{ align: 'center', collisionPadding: 12 }"
    :ui="{ content: collapsed ? 'w-48' : 'w-(--reka-dropdown-menu-trigger-width)' }"
  >
    <UButton
      :label="collapsed ? undefined : user.name"
      :avatar="user.avatar"
      :trailing-icon="collapsed ? undefined : 'i-lucide-chevrons-up-down'"
      color="neutral"
      variant="ghost"
      block
      :square="collapsed"
      class="data-[state=open]:bg-elevated"
      :ui="{
        trailingIcon: 'text-dimmed'
      }"
    />

    <template #chip-leading>
      <span
        class="ms-0.5 size-2 rounded-full bg-primary/50"
      />
    </template>
  </UDropdownMenu>
</template>
