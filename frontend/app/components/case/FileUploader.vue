<template>
  <div class="bg-white rounded-lg border border-gray-200 p-6">
    <div class="mb-4">
      <h3 class="text-lg font-semibold text-gray-900 mb-2">Upload Documents</h3>
      <p class="text-sm text-gray-600">
        Drag and drop files here or click to browse. Supports PDF, DOCX, TXT, and audio/video files.
      </p>
    </div>

    <!-- Drop Zone -->
    <div
      class="relative border-2 border-dashed rounded-lg p-8 text-center transition-colors"
      :class="{
        'border-blue-400 bg-blue-50': isDragOver,
        'border-gray-300': !isDragOver
      }"
      @dragover.prevent="onDragOver"
      @dragleave.prevent="onDragLeave"
      @drop.prevent="onDrop"
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        multiple
        accept=".pdf,.docx,.doc,.txt,.mp3,.wav,.mp4,.avi,.mov"
        class="hidden"
        @change="onFileSelect"
      />

      <div v-if="!files.length" class="space-y-4">
        <UIcon
          name="i-heroicons-cloud-arrow-up-20-solid"
          class="w-12 h-12 text-gray-400 mx-auto"
        />
        <div>
          <p class="text-lg font-medium text-gray-900 mb-1">
            Drop files here or click to upload
          </p>
          <p class="text-sm text-gray-500">
            Maximum file size: 100MB per file
          </p>
        </div>
      </div>

      <!-- File List -->
      <div v-else class="space-y-3">
        <div
          v-for="(file, index) in files"
          :key="index"
          class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
        >
          <div class="flex items-center space-x-3">
            <UIcon
              :name="getFileIcon(file.type)"
              class="w-8 h-8 text-gray-400"
            />
            <div>
              <p class="text-sm font-medium text-gray-900">{{ file.name }}</p>
              <p class="text-xs text-gray-500">{{ formatFileSize(file.size) }}</p>
            </div>
          </div>

          <div class="flex items-center space-x-2">
            <div v-if="file.status === 'uploading'" class="flex items-center">
              <UProgress :value="file.progress" class="w-16 mr-2" />
              <span class="text-xs text-gray-500">{{ file.progress }}%</span>
            </div>

            <UBadge
              :color="getStatusColor(file.status)"
              variant="subtle"
              size="sm"
            >
              {{ getStatusLabel(file.status) }}
            </UBadge>

            <UButton
              variant="ghost"
              size="sm"
              @click.stop="removeFile(index)"
              :disabled="file.status === 'uploading'"
            >
              <UIcon name="i-heroicons-x-mark-20-solid" class="w-4 h-4" />
            </UButton>
          </div>
        </div>

        <!-- Upload Controls -->
        <div class="flex items-center justify-between pt-4 border-t border-gray-200">
          <div class="flex items-center space-x-4">
            <UButton
              variant="outline"
              size="sm"
              @click.stop="addMoreFiles"
            >
              <UIcon name="i-heroicons-plus-20-solid" class="w-4 h-4 mr-2" />
              Add More
            </UButton>

            <UButton
              variant="ghost"
              size="sm"
              @click.stop="clearAll"
            >
              Clear All
            </UButton>
          </div>

          <UButton
            color="primary"
            :loading="uploading"
            :disabled="!hasValidFiles"
            @click.stop="uploadFiles"
          >
            <UIcon name="i-heroicons-cloud-arrow-up-20-solid" class="w-4 h-4 mr-2" />
            Upload {{ validFilesCount }} File{{ validFilesCount !== 1 ? 's' : '' }}
          </UButton>
        </div>
      </div>
    </div>

    <!-- Upload Progress -->
    <div v-if="totalProgress > 0" class="mt-4">
      <div class="flex items-center justify-between text-sm text-gray-600 mb-2">
        <span>Overall Progress</span>
        <span>{{ totalProgress }}%</span>
      </div>
      <UProgress :value="totalProgress" />
    </div>

    <!-- Error Messages -->
    <div v-if="errors.length > 0" class="mt-4 space-y-2">
      <div
        v-for="error in errors"
        :key="error"
        class="p-3 bg-red-50 border border-red-200 rounded-lg"
      >
        <p class="text-sm text-red-700">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface FileItem {
  file: File
  name: string
  size: number
  type: string
  status: 'pending' | 'uploading' | 'completed' | 'error'
  progress: number
  error?: string
}

interface Props {
  caseId: string
  maxFileSize?: number // in MB
  acceptedTypes?: string[]
}

interface Emits {
  uploaded: [files: FileItem[]]
  error: [error: string]
}

const props = withDefaults(defineProps<Props>(), {
  maxFileSize: 100,
  acceptedTypes: () => ['.pdf', '.docx', '.doc', '.txt', '.mp3', '.wav', '.mp4', '.avi', '.mov']
})

const emit = defineEmits<Emits>()

// Refs
const fileInput = ref<HTMLInputElement>()
const files = ref<FileItem[]>([])
const uploading = ref(false)
const isDragOver = ref(false)
const errors = ref<string[]>([])

// Computed
const validFilesCount = computed(() => {
  return files.value.filter(f => f.status === 'pending' || f.status === 'completed').length
})

const hasValidFiles = computed(() => validFilesCount.value > 0)

const totalProgress = computed(() => {
  if (files.value.length === 0) return 0

  const total = files.value.reduce((sum, file) => sum + file.progress, 0)
  return Math.round(total / files.value.length)
})

// Methods
function triggerFileInput() {
  fileInput.value?.click()
}

function addMoreFiles() {
  fileInput.value?.click()
}

function onDragOver() {
  isDragOver.value = true
}

function onDragLeave() {
  isDragOver.value = false
}

function onDrop(event: DragEvent) {
  isDragOver.value = false
  const droppedFiles = Array.from(event.dataTransfer?.files || [])
  addFiles(droppedFiles)
}

function onFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const selectedFiles = Array.from(target.files || [])
  addFiles(selectedFiles)
  // Reset input
  target.value = ''
}

function addFiles(newFiles: File[]) {
  errors.value = []

  for (const file of newFiles) {
    // Validate file size
    if (file.size > props.maxFileSize * 1024 * 1024) {
      errors.value.push(`File "${file.name}" is too large (max ${props.maxFileSize}MB)`)
      continue
    }

    // Validate file type
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!props.acceptedTypes.includes(fileExtension)) {
      errors.value.push(`File type "${fileExtension}" is not supported`)
      continue
    }

    // Check for duplicates
    const isDuplicate = files.value.some(f => f.name === file.name && f.size === file.size)
    if (isDuplicate) {
      errors.value.push(`File "${file.name}" is already added`)
      continue
    }

    // Add file
    files.value.push({
      file,
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'pending',
      progress: 0
    })
  }
}

function removeFile(index: number) {
  files.value.splice(index, 1)
}

function clearAll() {
  files.value = []
  errors.value = []
}

async function uploadFiles() {
  if (!hasValidFiles.value) return

  uploading.value = true
  errors.value = []

  const pendingFiles = files.value.filter(f => f.status === 'pending')

  try {
    const formData = new FormData()

    // Add case ID
    formData.append('case_id', props.caseId)

    // Add files
    for (const fileItem of pendingFiles) {
      formData.append('files', fileItem.file)
      fileItem.status = 'uploading'
      fileItem.progress = 0
    }

    // Upload files
    await $fetch(`/api/cases/${props.caseId}/upload`, {
      method: 'POST',
      body: formData,
      onUploadProgress: (progress: { loaded: number; total: number }) => {
        // Update progress for all files (simplified)
        const percent = Math.round((progress.loaded / progress.total) * 100)
        pendingFiles.forEach(file => {
          file.progress = percent
        })
      }
    })

    // Mark files as completed
    pendingFiles.forEach(file => {
      file.status = 'completed'
      file.progress = 100
    })

    emit('uploaded', files.value)

  } catch (error: any) {
    console.error('Upload failed:', error)

    // Mark files as error
    pendingFiles.forEach(file => {
      file.status = 'error'
      file.error = error.message || 'Upload failed'
    })

    errors.value.push('Upload failed. Please try again.')
    emit('error', error.message || 'Upload failed')

  } finally {
    uploading.value = false
  }
}

function getFileIcon(mimeType: string): string {
  if (mimeType.startsWith('application/pdf')) {
    return 'i-heroicons-document-text-20-solid'
  } else if (mimeType.startsWith('application/vnd.openxmlformats-officedocument')) {
    return 'i-heroicons-document-text-20-solid'
  } else if (mimeType.startsWith('audio/')) {
    return 'i-heroicons-musical-note-20-solid'
  } else if (mimeType.startsWith('video/')) {
    return 'i-heroicons-video-camera-20-solid'
  } else {
    return 'i-heroicons-document-20-solid'
  }
}

function getStatusColor(status: string): "primary" | "secondary" | "success" | "info" | "warning" | "error" | "neutral" {
  const colors: Record<string, "primary" | "secondary" | "success" | "info" | "warning" | "error" | "neutral"> = {
    pending: 'neutral',
    uploading: 'info',
    completed: 'success',
    error: 'error'
  }
  return colors[status] || 'neutral'
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: 'Pending',
    uploading: 'Uploading',
    completed: 'Completed',
    error: 'Error'
  }
  return labels[status] || status
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

// Expose methods for parent component
defineExpose({
  addFiles,
  clearAll
})
</script>