<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'

definePageMeta({
  layout: 'auth'
})

const { signUpWithEmail, signInWithGoogle, error, isLoading, isAuthenticated } = useAuth()
const router = useRouter()

// Redirect if already authenticated
watch(isAuthenticated, (authenticated) => {
  if (authenticated) {
    router.push('/')
  }
}, { immediate: true })

const schema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  confirmPassword: z.string()
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword']
})

type Schema = z.output<typeof schema>

const state = reactive({
  name: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const onSubmit = async (event: FormSubmitEvent<Schema>) => {
  try {
    await signUpWithEmail(event.data.email, event.data.password, event.data.name)
    router.push('/')
  } catch (e) {
    // Error is handled by useAuth
  }
}

const onGoogleSignUp = async () => {
  try {
    await signInWithGoogle()
    router.push('/')
  } catch (e) {
    // Error is handled by useAuth
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-default p-4">
    <UCard class="w-full max-w-md">
      <template #header>
        <div class="text-center">
          <h1 class="text-2xl font-bold">Create an account</h1>
          <p class="text-muted mt-1">Start using LegalEase today</p>
        </div>
      </template>

      <UForm :schema="schema" :state="state" class="space-y-4" @submit="onSubmit">
        <UFormField label="Full name" name="name">
          <UInput
            v-model="state.name"
            placeholder="John Doe"
            icon="i-lucide-user"
            autocomplete="name"
          />
        </UFormField>

        <UFormField label="Email" name="email">
          <UInput
            v-model="state.email"
            type="email"
            placeholder="you@example.com"
            icon="i-lucide-mail"
            autocomplete="email"
          />
        </UFormField>

        <UFormField label="Password" name="password">
          <UInput
            v-model="state.password"
            type="password"
            placeholder="Create a password"
            icon="i-lucide-lock"
            autocomplete="new-password"
          />
        </UFormField>

        <UFormField label="Confirm password" name="confirmPassword">
          <UInput
            v-model="state.confirmPassword"
            type="password"
            placeholder="Confirm your password"
            icon="i-lucide-lock"
            autocomplete="new-password"
          />
        </UFormField>

        <UAlert
          v-if="error"
          color="error"
          variant="subtle"
          :description="error"
          icon="i-lucide-alert-circle"
        />

        <UButton
          type="submit"
          block
          :loading="isLoading"
        >
          Create account
        </UButton>
      </UForm>

      <UDivider label="or" class="my-4" />

      <UButton
        block
        color="neutral"
        variant="outline"
        icon="i-simple-icons-google"
        :loading="isLoading"
        @click="onGoogleSignUp"
      >
        Continue with Google
      </UButton>

      <template #footer>
        <p class="text-center text-muted text-sm">
          Already have an account?
          <UButton variant="link" color="primary" to="/login" :padded="false">
            Sign in
          </UButton>
        </p>
      </template>
    </UCard>
  </div>
</template>
