<script setup lang="ts">
definePageMeta({ layout: 'empty' })

const session = useUserSession()
const router = useRouter()
const loading = ref(false)

watchEffect(() => {
  if (session.loggedIn.value) {
    router.replace('/')
  }
})

function beginLogin() {
  if (loading.value) {
    return
  }
  loading.value = true
  window.location.href = '/api/auth/login'
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white p-6">
    <div class="max-w-md w-full space-y-6">
      <div class="space-y-4 text-center">
        <h1 class="text-3xl font-bold">Welcome back</h1>
        <p class="text-slate-300">
          Sign in with your Keycloak account to access the LegalEase dashboard.
        </p>
      </div>

      <UCard class="bg-slate-900/60 border border-white/10 backdrop-blur">
        <div class="space-y-6">
          <div class="flex items-center justify-center">
            <UIcon name="i-lucide-shield-check" class="size-12 text-primary" />
          </div>
          <div class="space-y-2 text-center">
            <h2 class="text-xl font-semibold">Secure Authentication</h2>
            <p class="text-sm text-slate-300">
              We use Keycloak and sealed cookies to keep your account secure.
            </p>
          </div>

          <UButton
            block
            color="primary"
            size="lg"
            :loading="loading"
            :disabled="loading"
            @click="beginLogin"
          >
            Sign in with Keycloak
          </UButton>
        </div>
      </UCard>

      <p class="text-center text-xs text-slate-400">
        Need access? Contact your workspace administrator to be added to the appropriate team.
      </p>
    </div>
  </div>
</template>
