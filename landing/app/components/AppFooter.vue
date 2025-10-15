<script setup lang="ts">
const columns = [{
  label: 'Features',
  children: [{
    label: 'Hybrid Search'
  }, {
    label: 'Case Management'
  }, {
    label: 'AI Transcription'
  }, {
    label: 'Entity Extraction'
  }]
}, {
  label: 'Resources',
  children: [{
    label: 'Documentation'
  }, {
    label: 'Quick Start'
  }, {
    label: 'API Reference'
  }, {
    label: 'Changelog'
  }]
}, {
  label: 'Community',
  children: [{
    label: 'GitHub'
  }, {
    label: 'Issues'
  }, {
    label: 'Contributing'
  }, {
    label: 'License'
  }]
}]

const toast = useToast()

const email = ref('')
const loading = ref(false)

function onSubmit() {
  loading.value = true

  toast.add({
    title: 'Subscribed!',
    description: 'You\'ve been subscribed to our newsletter.'
  })
}
</script>

<template>
  <USeparator
    class="h-px"
  />

  <UFooter :ui="{ top: 'border-b border-default' }">
    <template #top>
      <UContainer>
        <UFooterColumns :columns="columns">
          <template #right>
            <form @submit.prevent="onSubmit">
              <UFormField
                name="email"
                label="Subscribe to our newsletter"
                size="lg"
              >
                <UInput
                  v-model="email"
                  type="email"
                  class="w-full"
                  placeholder="Enter your email"
                >
                  <template #trailing>
                    <UButton
                      type="submit"
                      size="xs"
                      color="neutral"
                      label="Subscribe"
                    />
                  </template>
                </UInput>
              </UFormField>
            </form>
          </template>
        </UFooterColumns>
      </UContainer>
    </template>

    <template #left>
      <p class="text-muted text-sm">
        Built with Nuxt UI • LegalEase AI © {{ new Date().getFullYear() }}
      </p>
    </template>

    <template #right>
      <UButton
        to="https://github.com/AlliecatOwO/legalease-ai"
        target="_blank"
        icon="i-simple-icons-github"
        aria-label="LegalEase AI on GitHub"
        color="neutral"
        variant="ghost"
      />
    </template>
  </UFooter>
</template>
