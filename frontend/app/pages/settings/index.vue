<script setup lang="ts">
import * as z from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'

const fileRef = ref<HTMLInputElement>()
const api = useApi()
const session = useUserSession()
const toast = useToast()

const profileSchema = z.object({
  name: z.string().min(2, 'Too short'),
  email: z.string().email('Invalid email'),
  username: z.string().min(2, 'Too short').optional(),
  avatar: z.string().optional(),
  bio: z.string().optional()
})

type ProfileSchema = z.output<typeof profileSchema>

const profile = reactive<Partial<ProfileSchema>>({
  name: '',
  email: '',
  username: '',
  avatar: undefined,
  bio: undefined
})

const loading = ref(false)

// Load profile on mount
onMounted(async () => {
  try {
    console.log('[Settings] Fetching profile from backend...')
    const data = await api.user.getProfile()
    console.log('[Settings] Profile response:', data)
    profile.name = data.full_name || ''
    profile.email = data.email || ''
    profile.username = data.username || ''
    profile.avatar = data.avatar_url || undefined
    profile.bio = data.bio || undefined

    // Update session with fresh team data from backend
    if (data.memberships) {
      const teams = data.memberships.map((m: any) => ({
        id: m.team.id,
        name: m.team.name,
        slug: m.team.slug,
        role: m.role
      }))
      console.log('[Settings] Updating session teams:', teams)
      session.user.value = {
        ...session.user.value!,
        teams,
        activeTeamId: data.active_team?.id ?? null
      }
    }
  } catch (error) {
    console.error('Failed to load profile:', error)
  }
})

async function onSubmit(event: FormSubmitEvent<ProfileSchema>) {
  loading.value = true
  try {
    const updatedProfile = await api.user.updateProfile({
      full_name: event.data.name,
      username: event.data.username,
      avatar_url: event.data.avatar,
      bio: event.data.bio
    })

    // Refresh the user session with updated data
    await session.fetch()

    toast.add({
      title: 'Success',
      description: 'Your settings have been updated.',
      icon: 'i-lucide-check',
      color: 'success'
    })
  } catch (error: any) {
    // Error toast is already handled by useApi
    console.error('Failed to update profile:', error)
  } finally {
    loading.value = false
  }
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement

  if (!input.files?.length) {
    return
  }

  profile.avatar = URL.createObjectURL(input.files[0]!)
}

function onFileClick() {
  fileRef.value?.click()
}

// Team switching
const teams = computed(() => {
  const userTeams = session.user.value?.teams ?? []
  console.log('[Settings] Teams:', userTeams, 'User:', session.user.value)
  return userTeams
})
const activeTeamId = computed(() => session.user.value?.activeTeamId ?? null)

const selectedTeamId = ref(activeTeamId.value)

// Watch for changes in session active team
watch(activeTeamId, (newId) => {
  selectedTeamId.value = newId
})

async function switchTeam() {
  if (!selectedTeamId.value || selectedTeamId.value === activeTeamId.value) {
    return
  }

  loading.value = true
  try {
    await $fetch('/api/auth/switch-team', {
      method: 'POST',
      body: { teamId: selectedTeamId.value }
    })
    await session.fetch()
    toast.add({
      title: 'Team switched',
      description: 'Your active team has been updated.',
      icon: 'i-lucide-check',
      color: 'success'
    })
  } catch (error: any) {
    console.error('Failed to switch team:', error)
    toast.add({
      title: 'Failed to switch team',
      description: error?.data?.message || error.message || 'Unexpected error',
      color: 'error'
    })
    // Revert selection on error
    selectedTeamId.value = activeTeamId.value
  } finally {
    loading.value = false
  }
}

function createTeam() {
  // For now, just show a toast - TODO: implement team creation modal
  toast.add({
    title: 'Team Creation',
    description: 'Team creation UI coming soon. For now, teams are created automatically from Keycloak groups.',
    color: 'info'
  })
}
</script>

<template>
  <UForm
    id="settings"
    :schema="profileSchema"
    :state="profile"
    @submit="onSubmit"
  >
    <UPageCard
      title="Profile"
      description="These informations will be displayed publicly."
      variant="naked"
      orientation="horizontal"
      class="mb-4"
    >
      <UButton
        form="settings"
        label="Save changes"
        color="neutral"
        type="submit"
        :loading="loading"
        class="w-fit lg:ms-auto"
      />
    </UPageCard>

    <UPageCard variant="subtle">
      <UFormField
        label="Active Team"
        description="Select which team's data you want to work with."
        class="flex max-sm:flex-col justify-between items-start gap-4"
      >
        <div class="flex items-center gap-3 w-full">
          <div class="flex-1">
            <UButton
              v-if="!teams.length"
              label="Create Your First Team"
              icon="i-lucide-plus"
              color="primary"
              @click="createTeam"
              class="w-full justify-center"
            />
            <USelectMenu
              v-else
              v-model="selectedTeamId"
              :options="teams"
              value-attribute="id"
              placeholder="Select a team"
              class="w-full"
            >
              <template #label>
                <span v-if="selectedTeamId">
                  {{ teams.find(t => t.id === selectedTeamId)?.name || 'Select a team' }}
                </span>
                <span v-else>
                  Select a team
                </span>
              </template>
              <template #option="{ option }">
                <span>{{ option.name }}</span>
              </template>
            </USelectMenu>
          </div>
          <UButton
            v-if="selectedTeamId && selectedTeamId !== activeTeamId"
            label="Switch"
            color="primary"
            :loading="loading"
            @click="switchTeam"
          />
          <UButton
            v-else-if="teams.length > 0"
            label="New Team"
            icon="i-lucide-plus"
            color="neutral"
            variant="outline"
            @click="createTeam"
          />
        </div>
      </UFormField>
      <USeparator />
      <UFormField
        name="name"
        label="Name"
        description="Will appear on receipts, invoices, and other communication."
        required
        class="flex max-sm:flex-col justify-between items-start gap-4"
      >
        <UInput
          v-model="profile.name"
          autocomplete="off"
        />
      </UFormField>
      <USeparator />
      <UFormField
        name="email"
        label="Email"
        description="Email address from your identity provider (read-only)."
        required
        class="flex max-sm:flex-col justify-between items-start gap-4"
      >
        <UInput
          v-model="profile.email"
          type="email"
          autocomplete="off"
          disabled
        />
      </UFormField>
      <USeparator />
      <UFormField
        name="username"
        label="Username"
        description="Your unique username for logging in and your profile URL."
        required
        class="flex max-sm:flex-col justify-between items-start gap-4"
      >
        <UInput
          v-model="profile.username"
          type="username"
          autocomplete="off"
        />
      </UFormField>
      <USeparator />
      <UFormField
        name="avatar"
        label="Avatar URL"
        description="Enter a URL to an image for your avatar."
        class="flex max-sm:flex-col justify-between items-start gap-4"
      >
        <div class="flex items-center gap-3 w-full">
          <UAvatar
            :src="profile.avatar"
            :alt="profile.name"
            size="lg"
          />
          <UInput
            v-model="profile.avatar"
            placeholder="https://example.com/avatar.jpg"
            autocomplete="off"
            class="flex-1"
          />
        </div>
      </UFormField>
      <USeparator />
      <UFormField
        name="bio"
        label="Bio"
        description="Brief description for your profile. URLs are hyperlinked."
        class="flex max-sm:flex-col justify-between items-start gap-4"
        :ui="{ container: 'w-full' }"
      >
        <UTextarea
          v-model="profile.bio"
          :rows="5"
          autoresize
          class="w-full"
        />
      </UFormField>
    </UPageCard>
  </UForm>
</template>
