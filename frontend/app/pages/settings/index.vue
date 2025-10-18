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
    const data = await api.user.getProfile()
    profile.name = data.full_name || ''
    profile.email = data.email || ''
    profile.username = data.username || ''
    profile.avatar = data.avatar_url || undefined
    profile.bio = data.bio || undefined
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
