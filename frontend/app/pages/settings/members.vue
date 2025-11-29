<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'
import type { Member } from '~/types'

const { user } = useAuth()
const {
  currentTeam,
  teams,
  members,
  invitations,
  isLoading,
  createTeam,
  loadTeams,
  loadMembers,
  loadInvitations,
  inviteMember,
  removeMember,
  updateMemberRole,
  cancelInvitation
} = useTeam()
const toast = useToast()

// Search
const q = ref('')

// Invite modal
const showInviteModal = ref(false)
const inviteSchema = z.object({
  email: z.string().email('Please enter a valid email'),
  role: z.enum(['admin', 'member'])
})
type InviteSchema = z.output<typeof inviteSchema>
const inviteForm = ref({ email: '', role: 'member' as 'admin' | 'member' })
const isInviting = ref(false)

// Create team modal
const showCreateTeamModal = ref(false)
const teamSchema = z.object({
  name: z.string().min(2, 'Team name must be at least 2 characters'),
  description: z.string().optional()
})
type TeamSchema = z.output<typeof teamSchema>
const teamForm = ref({ name: '', description: '' })
const isCreatingTeam = ref(false)

// Convert TeamMember to Member type for component
const formattedMembers = computed<Member[]>(() => {
  return members.value.map(m => ({
    id: m.id || m.userId,
    name: m.displayName || m.email?.split('@')[0] || 'Unknown',
    username: m.email?.split('@')[0] || '',
    email: m.email || '',
    role: m.role,
    avatar: {
      src: m.photoURL || undefined,
      alt: m.displayName || m.email || 'Member'
    }
  }))
})

const filteredMembers = computed(() => {
  if (!q.value) return formattedMembers.value
  const search = q.value.toLowerCase()
  return formattedMembers.value.filter(member =>
    member.name.toLowerCase().includes(search) ||
    member.email.toLowerCase().includes(search)
  )
})

// Check if current user is admin or owner
const isAdmin = computed(() => {
  const currentMember = members.value.find(m => m.userId === user.value?.uid)
  return currentMember?.role === 'admin' || currentMember?.role === 'owner'
})

// Load data on mount
onMounted(async () => {
  await loadTeams()
  if (currentTeam.value?.id) {
    await Promise.all([
      loadMembers(currentTeam.value.id),
      loadInvitations(currentTeam.value.id)
    ])
  }
})

// Watch for team changes
watch(currentTeam, async (team) => {
  if (team?.id) {
    await Promise.all([
      loadMembers(team.id),
      loadInvitations(team.id)
    ])
  }
})

async function handleInvite(event: FormSubmitEvent<InviteSchema>) {
  if (!currentTeam.value?.id) return

  isInviting.value = true
  try {
    await inviteMember(currentTeam.value.id, event.data.email, event.data.role)
    toast.add({
      title: 'Invitation sent',
      description: `An invitation has been sent to ${event.data.email}`,
      color: 'success'
    })
    showInviteModal.value = false
    inviteForm.value = { email: '', role: 'member' }
  } catch (error: any) {
    toast.add({
      title: 'Failed to send invitation',
      description: error.message || 'Please try again',
      color: 'error'
    })
  } finally {
    isInviting.value = false
  }
}

async function handleCreateTeam(event: FormSubmitEvent<TeamSchema>) {
  isCreatingTeam.value = true
  try {
    await createTeam(event.data.name, event.data.description)
    toast.add({
      title: 'Team created',
      description: `${event.data.name} has been created`,
      color: 'success'
    })
    showCreateTeamModal.value = false
    teamForm.value = { name: '', description: '' }
  } catch (error: any) {
    toast.add({
      title: 'Failed to create team',
      description: error.message || 'Please try again',
      color: 'error'
    })
  } finally {
    isCreatingTeam.value = false
  }
}

async function handleUpdateRole(memberId: string, role: 'admin' | 'member') {
  if (!currentTeam.value?.id) return

  try {
    await updateMemberRole(currentTeam.value.id, memberId, role)
    toast.add({
      title: 'Role updated',
      description: `Member role has been updated to ${role}`,
      color: 'success'
    })
  } catch (error: any) {
    toast.add({
      title: 'Failed to update role',
      description: error.message || 'Please try again',
      color: 'error'
    })
  }
}

async function handleRemoveMember(memberId: string) {
  if (!currentTeam.value?.id) return

  try {
    await removeMember(currentTeam.value.id, memberId)
    toast.add({
      title: 'Member removed',
      description: 'The member has been removed from the team',
      color: 'success'
    })
  } catch (error: any) {
    toast.add({
      title: 'Failed to remove member',
      description: error.message || 'Please try again',
      color: 'error'
    })
  }
}

async function handleCancelInvitation(invitationId: string) {
  if (!currentTeam.value?.id) return

  try {
    await cancelInvitation(currentTeam.value.id, invitationId)
    toast.add({
      title: 'Invitation cancelled',
      color: 'success'
    })
  } catch (error: any) {
    toast.add({
      title: 'Failed to cancel invitation',
      description: error.message || 'Please try again',
      color: 'error'
    })
  }
}
</script>

<template>
  <div>
    <!-- No team state -->
    <div v-if="!isLoading && teams.length === 0" class="text-center py-12">
      <UIcon name="i-lucide-users" class="size-16 mx-auto mb-4 text-muted opacity-50" />
      <h3 class="text-lg font-semibold mb-2">No team yet</h3>
      <p class="text-muted mb-6">Create a team to collaborate with others</p>
      <UButton
        label="Create Team"
        icon="i-lucide-plus"
        color="primary"
        @click="showCreateTeamModal = true"
      />
    </div>

    <!-- Team exists -->
    <template v-else>
      <UPageCard
        title="Team Members"
        :description="currentTeam ? `Manage members of ${currentTeam.name}` : 'Invite new members by email address.'"
        variant="naked"
        orientation="horizontal"
        class="mb-4"
      >
        <div class="flex gap-2 lg:ms-auto">
          <UButton
            v-if="isAdmin"
            label="Invite people"
            icon="i-lucide-user-plus"
            color="neutral"
            @click="showInviteModal = true"
          />
        </div>
      </UPageCard>

      <UPageCard
        variant="subtle"
        :ui="{ container: 'p-0 sm:p-0 gap-y-0', wrapper: 'items-stretch', header: 'p-4 mb-0 border-b border-default' }"
      >
        <template #header>
          <UInput
            v-model="q"
            icon="i-lucide-search"
            placeholder="Search members"
            class="w-full"
          />
        </template>

        <div v-if="isLoading" class="py-12 text-center">
          <UIcon name="i-lucide-loader-circle" class="size-8 animate-spin text-muted" />
        </div>

        <SettingsMembersList
          v-else
          :members="filteredMembers"
          :current-user-id="user?.uid"
          :is-admin="isAdmin"
          @update-role="handleUpdateRole"
          @remove="handleRemoveMember"
        />
      </UPageCard>

      <!-- Pending Invitations -->
      <UPageCard
        v-if="invitations.length > 0"
        title="Pending Invitations"
        variant="subtle"
        class="mt-4"
      >
        <ul class="divide-y divide-default">
          <li
            v-for="invitation in invitations"
            :key="invitation.id"
            class="flex items-center justify-between py-3"
          >
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-mail" class="size-5 text-muted" />
              <div>
                <p class="font-medium">{{ invitation.email }}</p>
                <p class="text-sm text-muted capitalize">{{ invitation.role }} role</p>
              </div>
            </div>
            <UButton
              v-if="isAdmin"
              icon="i-lucide-x"
              color="neutral"
              variant="ghost"
              size="sm"
              @click="handleCancelInvitation(invitation.id!)"
            />
          </li>
        </ul>
      </UPageCard>
    </template>

    <!-- Create Team Modal -->
    <UModal v-model:open="showCreateTeamModal">
      <template #header>
        <div class="flex items-center gap-3">
          <UIcon name="i-lucide-users" class="size-6 text-primary" />
          <h2 class="text-xl font-semibold">Create Team</h2>
        </div>
      </template>

      <template #body>
        <UForm :schema="teamSchema" :state="teamForm" class="space-y-4" @submit="handleCreateTeam">
          <UFormField label="Team Name" name="name" required>
            <UInput v-model="teamForm.name" placeholder="e.g., Smith & Associates" />
          </UFormField>

          <UFormField label="Description" name="description">
            <UTextarea v-model="teamForm.description" placeholder="What does this team work on?" />
          </UFormField>

          <div class="flex justify-end gap-2 pt-2">
            <UButton
              label="Cancel"
              color="neutral"
              variant="ghost"
              @click="showCreateTeamModal = false"
            />
            <UButton
              type="submit"
              label="Create Team"
              color="primary"
              :loading="isCreatingTeam"
            />
          </div>
        </UForm>
      </template>
    </UModal>

    <!-- Invite Modal -->
    <UModal v-model:open="showInviteModal">
      <template #header>
        <div class="flex items-center gap-3">
          <UIcon name="i-lucide-user-plus" class="size-6 text-primary" />
          <h2 class="text-xl font-semibold">Invite Team Member</h2>
        </div>
      </template>

      <template #body>
        <UForm :schema="inviteSchema" :state="inviteForm" class="space-y-4" @submit="handleInvite">
          <UFormField label="Email Address" name="email" required>
            <UInput
              v-model="inviteForm.email"
              type="email"
              placeholder="colleague@example.com"
              icon="i-lucide-mail"
            />
          </UFormField>

          <UFormField label="Role" name="role">
            <USelect
              v-model="inviteForm.role"
              :items="[
                { label: 'Member', value: 'member', description: 'Can view and edit cases' },
                { label: 'Admin', value: 'admin', description: 'Can manage team members' }
              ]"
            />
          </UFormField>

          <div class="flex justify-end gap-2 pt-2">
            <UButton
              label="Cancel"
              color="neutral"
              variant="ghost"
              @click="showInviteModal = false"
            />
            <UButton
              type="submit"
              label="Send Invitation"
              icon="i-lucide-send"
              color="primary"
              :loading="isInviting"
            />
          </div>
        </UForm>
      </template>
    </UModal>
  </div>
</template>
