<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'

definePageMeta({
  layout: 'auth'
})

const { signInWithEmail, signInWithGoogle, error, isLoading, isAuthenticated } = useAuth()
const router = useRouter()

// Redirect if already authenticated
watch(isAuthenticated, (authenticated) => {
  if (authenticated) {
    router.push('/')
  }
}, { immediate: true })

const schema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters')
})

type Schema = z.output<typeof schema>

const state = reactive({
  email: '',
  password: ''
})

const onSubmit = async (event: FormSubmitEvent<Schema>) => {
  try {
    await signInWithEmail(event.data.email, event.data.password)
    router.push('/')
  } catch (e) {
    // Error is handled by useAuth
  }
}

const onGoogleSignIn = async () => {
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
          <h1 class="text-2xl font-bold">Welcome back</h1>
          <p class="text-muted mt-1">Sign in to your LegalEase account</p>
        </div>
      </template>

      <UForm :schema="schema" :state="state" class="space-y-4" @submit="onSubmit">
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
            placeholder="Your password"
            icon="i-lucide-lock"
            autocomplete="current-password"
          />
        </UFormField>

        <div class="flex items-center justify-between">
          <UCheckbox label="Remember me" />
          <UButton
            variant="link"
            color="primary"
            to="/forgot-password"
            :padded="false"
          >
            Forgot password?
          </UButton>
        </div>

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
          Sign in
        </UButton>
      </UForm>

      <UDivider label="or" class="my-4" />

      <UButton
        block
        color="neutral"
        variant="outline"
        icon="i-simple-icons-google"
        :loading="isLoading"
        @click="onGoogleSignIn"
      >
        Continue with Google
      </UButton>

      <template #footer>
        <p class="text-center text-muted text-sm">
          Don't have an account?
          <UButton variant="link" color="primary" to="/signup" :padded="false">
            Sign up
          </UButton>
        </p>
      </template>
    </UCard>
  </div>
</template>
