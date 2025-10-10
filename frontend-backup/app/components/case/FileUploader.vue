<template>
  <UCard>
    <template #header>
      <h3 class="text-lg font-semibold">Upload Documents</h3>
      <p class="text-sm text-muted mt-1">
        Drag and drop files here or click to browse. Supports PDF, DOCX, TXT, and audio/video files.
      </p>
    </template>

    <UFileUpload
      v-model="files"
      accept=".pdf,.docx,.doc,.txt,.mp3,.wav,.mp4,.avi,.mov"
      multiple
      :max-file-size="maxFileSize * 1024 * 1024"
      label="Drop files here or click to upload"
      description="Maximum file size: 100MB per file"
      class="min-h-64"
    />

    <!-- Upload Controls -->
    <template v-if="files && files.length > 0" #footer>
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <UButton
            variant="outline"
            size="sm"
            @click="clearAll"
          >
            Clear All
          </UButton>
        </div>

        <UButton
          color="primary"
          :loading="uploading"
          :disabled="!files.length"
          @click="uploadFiles"
        >
          <UIcon name="i-heroicons-cloud-arrow-up-20-solid" class="w-4 h-4 mr-2" />
          Upload {{ files.length }} File{{ files.length !== 1 ? 's' : '' }}
        </UButton>
      </div>
    </template>

    <!-- Upload Progress -->
    <div v-if="totalProgress > 0" class="mt-4">
      <div class="flex items-center justify-between text-sm mb-2">
        <span class="font-medium">Overall Progress</span>
        <UBadge variant="outline" size="sm">
          {{ totalProgress }}%
        </UBadge>
      </div>
      <UProgress :value="totalProgress" />
    </div>

    <!-- Error Messages -->
    <div v-if="errors.length > 0" class="mt-4 space-y-2">
      <UAlert
        v-for="error in errors"
        :key="error"
        color="error"
        variant="subtle"
      >
        {{ error }}
      </UAlert>
    </div>
  </UCard>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  caseId: string
  maxFileSize?: number // in MB
}

interface Emits {
  uploaded: [files: File[]]
  error: [error: string]
}

const props = withDefaults(defineProps<Props>(), {
  maxFileSize: 100
})

const emit = defineEmits<Emits>()

// Refs
const files = ref<File[]>([])
const uploading = ref(false)
const errors = ref<string[]>([])

// Computed
const totalProgress = computed(() => {
  if (!files.value || files.value.length === 0) return 0
  // For simplicity, we'll show overall progress. In a real implementation,
  // you'd track progress per file
  return 50 // Mock progress
})

// Methods
function clearAll() {
  files.value = []
  errors.value = []
}

async function uploadFiles() {
  if (!files.value || files.value.length === 0) return

  uploading.value = true
  errors.value = []

  try {
    const formData = new FormData()

    // Add case ID
    formData.append('case_id', props.caseId)

    // Add files
    files.value.forEach(file => {
      formData.append('files', file)
    })

    // Upload files
    await $fetch(`/api/cases/${props.caseId}/upload`, {
      method: 'POST',
      body: formData
    })

    emit('uploaded', files.value)
    files.value = [] // Clear after successful upload

  } catch (error: any) {
    console.error('Upload failed:', error)
    errors.value.push('Upload failed. Please try again.')
    emit('error', error.message || 'Upload failed')
  } finally {
    uploading.value = false
  }
}

// Expose methods for parent component
defineExpose({
  clearAll
})
</script>