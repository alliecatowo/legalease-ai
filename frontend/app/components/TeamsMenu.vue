<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

defineProps<{
  collapsed?: boolean
}>()

const toast = useToast()
const session = useUserSession()

const teams = computed(() => session.user.value?.teams ?? [])
const activeTeamId = computed(() => session.user.value?.activeTeamId ?? null)

const selectedTeam = computed(() => {
  if (!teams.value.length) {
    return null
  }
  return teams.value.find(team => team.id === activeTeamId.value) ?? teams.value[0]
})

async function handleSwitch(teamId: string) {
  if (teamId === activeTeamId.value) {
    return
  }

  try {
    await $fetch('/api/auth/switch-team', {
      method: 'POST',
      body: { teamId }
    })
    await session.fetch()
    toast.add({
      title: 'Team switched',
      color: 'success'
    })
  } catch (error: any) {
    console.error('Failed to switch team', error)
    toast.add({
      title: 'Failed to switch team',
      description: error?.data?.message || error.message || 'Unexpected error',
      color: 'error'
    })
  }
}

const items = computed<DropdownMenuItem[][]>(() => {
  if (!teams.value.length) {
    return [[{
      label: 'No teams available',
      disabled: true
    }]]
  }

  const switchItems = teams.value.map(team => ({
    label: team.name,
    icon: team.id === activeTeamId.value ? 'i-lucide-check' : undefined,
    onSelect: () => handleSwitch(team.id)
  }))

  return [switchItems, [{
    label: 'Manage teams',
    icon: 'i-lucide-cog',
    to: '/settings'
  }]]
})
</script>

<template>
  <UDropdownMenu
    :items="items"
    :content="{ align: 'center', collisionPadding: 12 }"
    :ui="{ content: collapsed ? 'w-40' : 'w-(--reka-dropdown-menu-trigger-width)' }"
  >
    <UButton
      v-if="!collapsed"
      :label="selectedTeam?.name || 'No teams'"
      icon="i-lucide-building"
      :trailing-icon="'i-lucide-chevrons-up-down'"
      color="neutral"
      variant="ghost"
      block
      class="data-[state=open]:bg-elevated py-2"
      :ui="{
        trailingIcon: 'text-dimmed'
      }"
      :disabled="!teams.length"
    />
    <UButton
      v-else
      icon="i-lucide-building"
      color="neutral"
      variant="ghost"
      square
      class="data-[state=open]:bg-elevated"
      :disabled="!teams.length"
    />
  </UDropdownMenu>
</template>
