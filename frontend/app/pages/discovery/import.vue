<script setup lang="ts">
import type { DiscoveryItemSource } from '~/types/discovery'

definePageMeta({
  title: 'Batch Import',
  layout: 'default'
})

const router = useRouter()
const toast = useToast()

// Form state
const form = reactive({
  caseId: null as number | null,
  source: 'CELLEBRITE' as DiscoveryItemSource,
  files: [] as File[],
  options: {
    autoProcess: true,
    extractMetadata: true,
    detectCategories: true
  }
})

// Upload state
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadedCount = ref(0)
const totalCount = ref(0)

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

// Source options
const sourceOptions = [
  { label: 'Cellebrite Export', value: 'CELLEBRITE', description: 'Mobile device forensics export' },
  { label: 'Email Export', value: 'EMAIL_EXPORT', description: '.eml or .msg files' },
  { label: 'Phone Records', value: 'PHONE_RECORDS', description: 'Call logs and SMS' },
  { label: 'Social Media Export', value: 'SOCIAL_MEDIA', description: 'Social media data exports' },
  { label: 'Surveillance Footage', value: 'SURVEILLANCE', description: 'Video surveillance files' },
  { label: 'Body Camera', value: 'BODY_CAM', description: 'Body camera footage' },
  { label: 'Evidence', value: 'EVIDENCE', description: 'General evidence files' },
  { label: 'Other', value: 'OTHER', description: 'Other sources' }
]

// Computed
const caseOptions = computed(() => {
  return cases.value.map(c => ({
    label: `${c.name}`,
    value: c.id
  }))
})

const isFormValid = computed(() => {
  return form.caseId && form.files.length > 0
})

// File selection
function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    form.files = Array.from(target.files)
  }
}

function removeFile(index: number) {
  form.files.splice(index, 1)
  if (fileInput.value && form.files.length === 0) {
    fileInput.value.value = ''
  }
}

function clearFiles() {
  form.files = []
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// Upload
async function handleUpload() {
  if (!isFormValid.value) return

  uploading.value = true
  uploadProgress.value = 0
  uploadedCount.value = 0
  totalCount.value = form.files.length

  try {
    // Upload files one by one for better progress tracking
    for (let i = 0; i < form.files.length; i++) {
      const file = form.files[i]
      const formData = new FormData()
      formData.append('file', file)
      formData.append('case_id', form.caseId!.toString())
      formData.append('source', form.source)
      formData.append('options', JSON.stringify(form.options))

      await $fetch('/api/v1/discovery/items', {
        method: 'POST',
        body: formData
      })

      uploadedCount.value++
      uploadProgress.value = Math.round((uploadedCount.value / totalCount.value) * 100)
    }

    toast.add({
      title: 'Success',
      description: `Successfully uploaded ${uploadedCount.value} items`,
      color: 'green'
    })

    router.push('/discovery')
  } catch (error) {
    console.error('Upload error:', error)
    toast.add({
      title: 'Error',
      description: `Failed to upload items. ${uploadedCount.value} of ${totalCount.value} uploaded successfully.`,
      color: 'red'
    })
  } finally {
    uploading.value = false
  }
}

function formatFileSize(bytes: number) {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Batch Import Discovery Items">
        <template #leading>
          <UButton
            icon="i-lucide-arrow-left"
            color="neutral"
            variant="ghost"
            square
            @click="router.push('/discovery')"
          />
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <div class="p-6 max-w-5xl mx-auto">
        <!-- Info Card -->
        <UCard class="mb-6 bg-blue-500/10 border-blue-500/20">
          <div class="flex items-start gap-3">
            <UIcon name="i-lucide-info" class="size-5 text-blue-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 class="font-semibold mb-1">Batch Import</h3>
              <p class="text-sm text-dimmed">
                Upload multiple discovery items at once. Files will be automatically processed and categorized based on your settings.
              </p>
            </div>
          </div>
        </UCard>

        <!-- Form -->
        <div class="space-y-6">
          <!-- Case Selection -->
          <UCard>
            <template #header>
              <h3 class="font-semibold">1. Select Case</h3>
            </template>

            <UFormField label="Case" required>
              <USelect
                v-model="form.caseId"
                :options="caseOptions"
                option-attribute="label"
                value-attribute="value"
                placeholder="Select a case"
                :disabled="uploading"
              />
            </UFormField>
          </UCard>

          <!-- Source Selection -->
          <UCard>
            <template #header>
              <h3 class="font-semibold">2. Select Source Type</h3>
            </template>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <button
                v-for="option in sourceOptions"
                :key="option.value"
                :class="[
                  'p-4 rounded-lg border-2 transition-colors text-left',
                  form.source === option.value
                    ? 'border-primary bg-primary/10'
                    : 'border-default hover:border-primary/50'
                ]"
                :disabled="uploading"
                @click="form.source = option.value"
              >
                <p class="font-semibold mb-1">{{ option.label }}</p>
                <p class="text-sm text-dimmed">{{ option.description }}</p>
              </button>
            </div>
          </UCard>

          <!-- File Upload -->
          <UCard>
            <template #header>
              <div class="flex items-center justify-between">
                <h3 class="font-semibold">3. Upload Files</h3>
                <UButton
                  v-if="form.files.length > 0"
                  label="Clear All"
                  size="xs"
                  variant="ghost"
                  color="neutral"
                  :disabled="uploading"
                  @click="clearFiles"
                />
              </div>
            </template>

            <div class="space-y-4">
              <!-- File input -->
              <input
                ref="fileInput"
                type="file"
                multiple
                :disabled="uploading"
                class="hidden"
                @change="handleFileSelect"
              />

              <!-- Upload button or selected files -->
              <div
                v-if="form.files.length === 0"
                class="border-2 border-dashed border-default rounded-lg p-12 text-center hover:border-primary transition-colors cursor-pointer"
                @click="fileInput?.click()"
              >
                <UIcon name="i-lucide-folder-up" class="size-16 text-dimmed mx-auto mb-4" />
                <p class="text-lg font-semibold mb-2">Click to select files</p>
                <p class="text-sm text-dimmed">or drag and drop multiple files here</p>
              </div>

              <!-- Selected files list -->
              <div v-else class="space-y-2">
                <div
                  v-for="(file, index) in form.files"
                  :key="index"
                  class="flex items-center gap-3 p-3 rounded-lg border border-default bg-elevated"
                >
                  <UIcon name="i-lucide-file" class="size-6 text-primary flex-shrink-0" />
                  <div class="flex-1 min-w-0">
                    <p class="font-semibold truncate">{{ file.name }}</p>
                    <p class="text-sm text-dimmed">{{ formatFileSize(file.size) }}</p>
                  </div>
                  <UButton
                    icon="i-lucide-x"
                    color="neutral"
                    variant="ghost"
                    size="sm"
                    square
                    :disabled="uploading"
                    @click="removeFile(index)"
                  />
                </div>

                <!-- Add more button -->
                <UButton
                  label="Add More Files"
                  icon="i-lucide-plus"
                  color="neutral"
                  variant="outline"
                  block
                  :disabled="uploading"
                  @click="fileInput?.click()"
                />
              </div>
            </div>
          </UCard>

          <!-- Options -->
          <UCard>
            <template #header>
              <h3 class="font-semibold">4. Processing Options</h3>
            </template>

            <div class="space-y-3">
              <label class="flex items-center gap-3 cursor-pointer">
                <UCheckbox v-model="form.options.autoProcess" :disabled="uploading" />
                <div>
                  <p class="font-semibold">Auto-process files</p>
                  <p class="text-sm text-dimmed">Automatically start processing after upload</p>
                </div>
              </label>

              <label class="flex items-center gap-3 cursor-pointer">
                <UCheckbox v-model="form.options.extractMetadata" :disabled="uploading" />
                <div>
                  <p class="font-semibold">Extract metadata</p>
                  <p class="text-sm text-dimmed">Extract EXIF data, timestamps, and other metadata</p>
                </div>
              </label>

              <label class="flex items-center gap-3 cursor-pointer">
                <UCheckbox v-model="form.options.detectCategories" :disabled="uploading" />
                <div>
                  <p class="font-semibold">Auto-detect categories</p>
                  <p class="text-sm text-dimmed">Use AI to automatically categorize items</p>
                </div>
              </label>
            </div>
          </UCard>

          <!-- Upload Progress -->
          <UCard v-if="uploading">
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span class="font-semibold">Uploading files...</span>
                <span class="text-dimmed">{{ uploadedCount }} / {{ totalCount }}</span>
              </div>
              <div class="w-full bg-elevated rounded-full h-3 overflow-hidden">
                <div
                  class="bg-primary h-full transition-all duration-300"
                  :style="{ width: `${uploadProgress}%` }"
                />
              </div>
              <p class="text-sm text-dimmed text-center">{{ uploadProgress }}%</p>
            </div>
          </UCard>

          <!-- Actions -->
          <div class="flex justify-end gap-3">
            <UButton
              label="Cancel"
              color="neutral"
              variant="outline"
              :disabled="uploading"
              @click="router.push('/discovery')"
            />
            <UButton
              label="Start Upload"
              icon="i-lucide-upload"
              color="primary"
              :disabled="!isFormValid || uploading"
              :loading="uploading"
              @click="handleUpload"
            />
          </div>
        </div>
      </div>
    </template>
  </UDashboardPanel>
</template>
