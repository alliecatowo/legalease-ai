<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'

const open = defineModel<boolean>('open')
const emit = defineEmits<{
  'created': [caseData: any]
}>()

const { createCase, getCase } = useCases()
const toast = useToast()
const router = useRouter()

const isSubmitting = ref(false)
const submitError = ref<string | null>(null)

// Form validation schema
const schema = z.object({
  name: z.string().min(1, 'Case name is required'),
  caseNumber: z.string().min(1, 'Case number is required'),
  client: z.string().min(1, 'Client name is required'),
  matterType: z.string().optional()
})

type Schema = z.output<typeof schema>

// Form data
const formData = ref({
  name: '',
  caseNumber: '',
  client: '',
  matterType: ''
})

const matterTypes = [
  { label: 'Civil Litigation', value: 'civil' },
  { label: 'Corporate', value: 'corporate' },
  { label: 'Patent/IP', value: 'patent' },
  { label: 'Employment', value: 'employment' },
  { label: 'Real Estate', value: 'real_estate' },
  { label: 'Criminal', value: 'criminal' },
  { label: 'Family Law', value: 'family' },
  { label: 'Personal Injury', value: 'personal_injury' },
  { label: 'Other', value: 'other' }
]

async function onSubmit(event: FormSubmitEvent<Schema>) {
  isSubmitting.value = true
  submitError.value = null

  try {
    const caseId = await createCase({
      name: event.data.name,
      caseNumber: event.data.caseNumber,
      client: event.data.client,
      matterType: event.data.matterType || undefined
    })

    const newCase = await getCase(caseId)

    toast.add({
      title: 'Case created',
      description: `${event.data.name} has been created successfully.`,
      color: 'success'
    })

    emit('created', newCase)
    open.value = false
    resetForm()

    // Navigate to the new case
    router.push(`/cases/${caseId}`)
  } catch (error: any) {
    console.error('Failed to create case:', error)
    submitError.value = error?.message || 'Failed to create case. Please try again.'
  } finally {
    isSubmitting.value = false
  }
}

function resetForm() {
  formData.value = {
    name: '',
    caseNumber: '',
    client: '',
    matterType: ''
  }
  submitError.value = null
}

// Reset form when modal closes
watch(open, (isOpen) => {
  if (!isOpen) {
    resetForm()
  }
})
</script>

<template>
  <UModal v-model:open="open" :ui="{ content: 'max-w-lg' }">
    <template #header>
      <div class="flex items-center gap-3">
        <UIcon name="i-lucide-folder-plus" class="size-6 text-primary" />
        <div>
          <h2 class="text-xl font-semibold">Create New Case</h2>
          <p class="text-sm text-muted mt-0.5">Add a new case to your workspace</p>
        </div>
      </div>
    </template>

    <template #body>
      <UForm :schema="schema" :state="formData" class="space-y-4" @submit="onSubmit">
        <UFormField label="Case Name" name="name" required>
          <UInput
            v-model="formData.name"
            placeholder="e.g., Acme Corp v. Global Tech"
            icon="i-lucide-briefcase"
          />
        </UFormField>

        <div class="grid grid-cols-2 gap-4">
          <UFormField label="Case Number" name="caseNumber" required>
            <UInput
              v-model="formData.caseNumber"
              placeholder="e.g., 2024-CV-12345"
              icon="i-lucide-hash"
            />
          </UFormField>

          <UFormField label="Matter Type" name="matterType">
            <USelect
              v-model="formData.matterType"
              :items="matterTypes"
              placeholder="Select type"
            />
          </UFormField>
        </div>

        <UFormField label="Client" name="client" required>
          <UInput
            v-model="formData.client"
            placeholder="e.g., Acme Corporation"
            icon="i-lucide-building"
          />
        </UFormField>

        <UAlert
          v-if="submitError"
          color="error"
          variant="subtle"
          :description="submitError"
          icon="i-lucide-alert-circle"
        />

        <div class="flex items-center justify-end gap-2 pt-2">
          <UButton
            label="Cancel"
            color="neutral"
            variant="ghost"
            @click="open = false"
          />
          <UButton
            type="submit"
            label="Create Case"
            icon="i-lucide-plus"
            color="primary"
            :loading="isSubmitting"
          />
        </div>
      </UForm>
    </template>
  </UModal>
</template>
