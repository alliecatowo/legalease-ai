<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { Member } from '~/types'

const props = defineProps<{
  members: Member[]
  currentUserId?: string
  isAdmin?: boolean
}>()

const emit = defineEmits<{
  'update-role': [memberId: string, role: 'admin' | 'member']
  'remove': [memberId: string]
}>()

function getItems(member: Member): DropdownMenuItem[] {
  const items: DropdownMenuItem[] = []

  // Can't modify owner or yourself
  if (member.role === 'owner' || member.id === props.currentUserId) {
    return items
  }

  if (props.isAdmin) {
    items.push({
      label: member.role === 'admin' ? 'Make member' : 'Make admin',
      icon: member.role === 'admin' ? 'i-lucide-user' : 'i-lucide-shield',
      onSelect: () => emit('update-role', member.id, member.role === 'admin' ? 'member' : 'admin')
    })
    items.push({
      label: 'Remove member',
      icon: 'i-lucide-user-minus',
      color: 'error' as const,
      onSelect: () => emit('remove', member.id)
    })
  }

  return items
}

function getRoleBadgeColor(role: string) {
  switch (role) {
    case 'owner':
      return 'primary'
    case 'admin':
      return 'info'
    default:
      return 'neutral'
  }
}
</script>

<template>
  <div v-if="members.length === 0" class="py-12 text-center text-muted">
    <UIcon name="i-lucide-users" class="size-12 mx-auto mb-3 opacity-50" />
    <p>No team members yet</p>
    <p class="text-sm">Invite people to collaborate on cases</p>
  </div>

  <ul v-else role="list" class="divide-y divide-default">
    <li
      v-for="member in members"
      :key="member.id"
      class="flex items-center justify-between gap-3 py-3 px-4 sm:px-6"
    >
      <div class="flex items-center gap-3 min-w-0">
        <UAvatar
          v-bind="member.avatar"
          size="md"
        />

        <div class="text-sm min-w-0">
          <p class="text-highlighted font-medium truncate">
            {{ member.name }}
            <span v-if="member.id === currentUserId" class="text-muted font-normal">(you)</span>
          </p>
          <p class="text-muted truncate">
            {{ member.email }}
          </p>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <UBadge
          :color="getRoleBadgeColor(member.role)"
          variant="subtle"
          class="capitalize"
        >
          {{ member.role }}
        </UBadge>

        <UDropdownMenu
          v-if="getItems(member).length > 0"
          :items="getItems(member)"
          :content="{ align: 'end' }"
        >
          <UButton
            icon="i-lucide-ellipsis-vertical"
            color="neutral"
            variant="ghost"
          />
        </UDropdownMenu>
      </div>
    </li>
  </ul>
</template>
