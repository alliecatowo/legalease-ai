<script setup lang="ts">
import type { DiscoveryItemType, DiscoveryItemSource, DiscoveryItemFormFactor } from '~/types/discovery'

const open = defineModel<boolean>('open', { required: true })

const emit = defineEmits<{
  success: []
}>()

const toast = useToast()

// Form state
const form = reactive({
  caseId: null as number | null,
  type: 'PHOTO' as DiscoveryItemType,
  source: 'EVIDENCE' as DiscoveryItemSource,
  formFactor: 'SINGLE_ITEM' as DiscoveryItemFormFactor,
  file: null as File | null,
  metadata: {}
})

// Upload state
const uploading = ref(false)
const uploadProgress = ref(0)

// Cases for dropdown
const cases = ref<Array<{ id: number; name: string }>>([])

async function fetchCases() {
  try {
    const response = await $fetch('/api/v1/cases')
    cases.value = response.cases || []
  } catch (error) {
    console.error('Error fetching cases:', error)
  }
}

onMounted(() => {
  fetchCases()
})

// File input ref
const fileInput = ref<HTMLInputElement | null>(null)

// Options
const typeOptions = [
  { label: 'Photo', value: 'PHOTO' },
  { label: 'Video', value: 'VIDEO' },
  { label: 'Audio', value: 'AUDIO' },
  { label: 'Social Media Post', value: 'SOCIAL_MEDIA_POST' },
  { label: 'Email', value: 'EMAIL' },
  { label: 'Call Log', value: 'CALL_LOG' },
  { label: 'SMS', value: 'SMS' },
  { label: 'Document', value: 'DOCUMENT' }
]

const sourceOptions = [
  { label: 'Evidence', value: 'EVIDENCE' },
  { label: 'Cellebrite', value: 'CELLEBRITE' },
  { label: 'Prosecutor', value: 'PROSECUTOR' },
  { label: 'Surveillance', value: 'SURVEILLANCE' },
  { label: 'Body Cam', value: 'BODY_CAM' },
  { label: 'Social Media', value: 'SOCIAL_MEDIA' },
  { label: 'Email Export', value: 'EMAIL_EXPORT' },
  { label: 'Phone Records', value: 'PHONE_RECORDS' },
  { label: 'Other', value: 'OTHER' }
]

const formFactorOptions = [
  { label: 'Single Item', value: 'SINGLE_ITEM' },
  { label: 'Short Form', value: 'SHORT_FORM' },
  { label: 'Long Form', value: 'LONG_FORM' },
  { label: 'Batch Dump', value: 'BATCH_DUMP' }
]

// Computed
const caseOptions = computed(() => {
  return cases.value.map(c => ({
    label: `${c.name}`,
    value: c.id
  }))
})

const acceptedFileTypes = computed(() => {
  const types: Record<DiscoveryItemType, string> = {
    PHOTO: 'image/*',
    VIDEO: 'video/*',
    AUDIO: 'audio/*',
    SOCIAL_MEDIA_POST: '*',
    EMAIL: '.eml,.msg',
    CALL_LOG: '.csv,.json',
    SMS: '.csv,.json,.xml',
    DOCUMENT: '.pdf,.doc,.docx'
  }
  return types[form.type] || '*'
})

const isFormValid = computed(() => {
  return form.caseId && form.file
})

// File selection
function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    form.file = target.files[0]
  }
}

function removeFile() {
  form.file = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// Upload
async function handleUpload() {
  if (!isFormValid.value) return

  uploading.value = true
  uploadProgress.value = 0

  try {
    const formData = new FormData()
    formData.append('file', form.file!)
    formData.append('case_id', form.caseId!.toString())
    formData.append('item_type', form.type)
    formData.append('source', form.source)
    formData.append('form_factor', form.formFactor)
    if (Object.keys(form.metadata).length > 0) {
      formData.append('metadata', JSON.stringify(form.metadata))
    }

    // Upload with progress tracking
    const xhr = new XMLHttpRequest()

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        uploadProgress.value = Math.round((e.loaded / e.total) * 100)
      }
    })

    xhr.addEventListener('load', () => {
      if (xhr.status === 200 || xhr.status === 201) {
        toast.add({
          title: 'Success',
          description: 'Item uploaded successfully and queued for processing',
          color: 'green'
        })
        emit('success')
        resetForm()
      } else {
        toast.add({
          title: 'Error',
          description: 'Failed to upload item',
          color: 'red'
        })
      }
      uploading.value = false
    })

    xhr.addEventListener('error', () => {
      toast.add({
        title: 'Error',
        description: 'Failed to upload item',
        color: 'red'
      })
      uploading.value = false
    })

    xhr.open('POST', '/api/v1/discovery/items')
    xhr.send(formData)
  } catch (error) {
    console.error('Upload error:', error)
    toast.add({
      title: 'Error',
      description: 'Failed to upload item',
      color: 'red'
    })
    uploading.value = false
  }
}

function resetForm() {
  Object.assign(form, {
    caseId: null,
    type: 'PHOTO',
    source: 'EVIDENCE',
    formFactor: 'SINGLE_ITEM',
    file: null,
    metadata: {}
  })
  uploadProgress.value = 0
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function close() {
  if (!uploading.value) {
    open.value = false
    resetForm()
  }
}
</script>

<template>
  <UModal
    v-model:open="open"
    title="Upload Discovery Item"
    :dismissible="!uploading"
    :ui="{ footer: 'justify-end' }"
  >
    <template #body>
      <div class="space-y-4">
        <!-- Case Selection -->
        <UFormField label="Case" required>
          <USelectMenu
            v-model="form.caseId"
            :items="caseOptions"
            placeholder="Select a case"
            :disabled="uploading"
            by="value"
          >
            <template #label>
              <span v-if="form.caseId">{{ caseOptions.find(c => c.value === form.caseId)?.label }}</span>
              <span v-else>Select a case</span>
            </template>
          </USelectMenu>
        </UFormField>

        <!-- Type -->
        <UFormField label="Type" required>
          <USelectMenu
            v-model="form.type"
            :items="typeOptions"
            :disabled="uploading"
            by="value"
          >
            <template #label>
              {{ typeOptions.find(option => option.value === form.type)?.label }}
            </template>
          </USelectMenu>
        </UFormField>

        <!-- Source -->
        <UFormField label="Source" required>
          <USelectMenu
            v-model="form.source"
            :items="sourceOptions"
            :disabled="uploading"
            by="value"
          >
            <template #label>
              {{ sourceOptions.find(option => option.value === form.source)?.label }}
            </template>
          </USelectMenu>
        </UFormField>

        <!-- Form Factor -->
        <UFormField label="Form Factor" required>
          <USelectMenu
            v-model="form.formFactor"
            :items="formFactorOptions"
            :disabled="uploading"
            by="value"
          >
            <template #label>
              {{ formFactorOptions.find(option => option.value === form.formFactor)?.label }}
            </template>
          </USelectMenu>
        </UFormField>

        <!-- File Upload -->
        <UFormField label="File" required>
          <div class="space-y-2">
            <!-- File input -->
            <input
              ref="fileInput"
              type="file"
              :accept="acceptedFileTypes"
              :disabled="uploading"
              class="hidden"
              @change="handleFileSelect"
            />

            <!-- Upload button or selected file -->
            <div
              v-if="!form.file"
              class="border-2 border-dashed border-default rounded-lg p-8 text-center hover:border-primary transition-colors cursor-pointer"
              @click="fileInput?.click()"
            >
              <UIcon name="i-lucide-upload" class="size-12 text-dimmed mx-auto mb-2" />
              <p class="text-sm font-semibold mb-1">Click to upload</p>
              <p class="text-xs text-dimmed">or drag and drop</p>
            </div>

            <!-- Selected file -->
            <UCard v-else class="bg-elevated">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3 flex-1 min-w-0">
                  <UIcon name="i-lucide-file" class="size-8 text-primary flex-shrink-0" />
                  <div class="flex-1 min-w-0">
                    <p class="font-semibold truncate">{{ form.file.name }}</p>
                    <p class="text-sm text-dimmed">
                      {{ (form.file.size / 1024 / 1024).toFixed(2) }} MB
                    </p>
                  </div>
                </div>
                <UButton
                  icon="i-lucide-x"
                  color="neutral"
                  variant="ghost"
                  size="sm"
                  square
                  :disabled="uploading"
                  @click="removeFile"
                />
              </div>
            </UCard>
          </div>
        </UFormField>

        <!-- Upload Progress -->
        <div v-if="uploading" class="space-y-2">
          <div class="flex items-center justify-between text-sm">
            <span class="font-semibold">Uploading...</span>
            <span class="text-dimmed">{{ uploadProgress }}%</span>
          </div>
          <div class="w-full bg-elevated rounded-full h-2 overflow-hidden">
            <div
              class="bg-primary h-full transition-all duration-300"
              :style="{ width: `${uploadProgress}%` }"
            />
          </div>
        </div>
      </div>
    </template>

    <template #footer>
      <UButton
        label="Cancel"
        color="neutral"
        variant="outline"
        :disabled="uploading"
        @click="close"
      />
      <UButton
        label="Upload"
        icon="i-lucide-upload"
        color="primary"
        :disabled="!isFormValid || uploading"
        :loading="uploading"
        @click="handleUpload"
      />
    </template>
  </UModal>
</template>
