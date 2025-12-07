<script setup lang="ts">
const props = defineProps<{
  caseId?: string
}>()

const open = defineModel<boolean>('open')
const emit = defineEmits<{
  uploaded: [transcriptionId: string]
}>()

const toast = useToast()
const { uploadForTranscription, uploadProgress, isUploading, uploadError, resetUpload, cancelUpload } = useStorage()
const { createTranscription } = useFirestore()
const { cases, listCases } = useCases()

// Load cases when modal opens
watch(open, async (isOpen) => {
  if (isOpen && !cases.value?.length) {
    await listCases()
  }
})

// Input mode: 'file' or 'url'
const inputMode = ref<'file' | 'url'>('file')
const selectedFile = ref<File | null>(null)
const mediaUrl = ref('')
const uploadStatus = ref<'idle' | 'uploading' | 'completed' | 'failed'>('idle')
const uploadErrorMsg = ref<string | null>(null)

// Case selection - use prop or allow user to select
const selectedCaseId = ref<string | undefined>(props.caseId)

// Sync with prop when it changes
watch(() => props.caseId, (newCaseId) => {
  selectedCaseId.value = newCaseId
})

const acceptedTypes = 'audio/*,video/*,.mp3,.mp4,.wav,.m4a,.webm,.ogg,.flac'

// URL validation
const isValidUrl = computed(() => {
  if (!mediaUrl.value) return false
  try {
    new URL(mediaUrl.value)
    return true
  } catch {
    return false
  }
})

const isYouTubeUrl = computed(() => {
  const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/
  return youtubeRegex.test(mediaUrl.value)
})

const canSubmit = computed(() => !!selectedFile.value)

async function handleUpload() {
  if (!selectedFile.value) return

  uploadStatus.value = 'uploading'
  uploadErrorMsg.value = null

  try {
    // Upload file and immediately trigger transcription
    const uploadResult = await uploadForTranscription(selectedFile.value, selectedCaseId.value)

    // Create transcription document with "processing" status
    // This triggers the transcription function automatically
    const docId = await createTranscription({
      caseId: selectedCaseId.value,
      userId: '', // Will be set by useFirestore
      filename: selectedFile.value.name,
      storagePath: uploadResult.path,
      gsUri: uploadResult.gsUri,
      downloadUrl: uploadResult.downloadUrl,
      mimeType: selectedFile.value.type,
      fileSize: selectedFile.value.size,
      status: 'processing' // Triggers transcription automatically
    })

    uploadStatus.value = 'completed'

    toast.add({
      title: 'Transcription Started',
      description: 'Your file is being transcribed. This may take a few minutes.',
      color: 'success'
    })

    emit('uploaded', docId!)

    // Close modal after short delay
    setTimeout(() => {
      resetAndClose()
    }, 1000)
  } catch (error: any) {
    console.error('Upload failed:', error)
    uploadStatus.value = 'failed'
    uploadErrorMsg.value = error?.message || 'Failed to upload file'

    toast.add({
      title: 'Upload Failed',
      description: uploadErrorMsg.value || 'Unknown error',
      color: 'error'
    })
  }
}

function handleCancel() {
  if (isUploading.value) {
    cancelUpload()
  }
  resetAndClose()
}

function resetAndClose() {
  selectedFile.value = null
  mediaUrl.value = ''
  inputMode.value = 'file'
  uploadStatus.value = 'idle'
  uploadErrorMsg.value = null
  selectedCaseId.value = props.caseId
  resetUpload()
  open.value = false
}

// Reset on modal close
watch(open, (isOpen) => {
  if (!isOpen) {
    selectedFile.value = null
    mediaUrl.value = ''
    inputMode.value = 'file'
    uploadStatus.value = 'idle'
    uploadErrorMsg.value = null
    resetUpload()
  }
})

const statusMessage = computed(() => {
  switch (uploadStatus.value) {
    case 'uploading':
      return `Uploading... ${Math.round(uploadProgress.value?.progress || 0)}%`
    case 'completed':
      return 'Upload complete! Ready for transcription.'
    case 'failed':
      return uploadErrorMsg.value || 'Upload failed'
    default:
      return ''
  }
})

const isProcessing = computed(() => uploadStatus.value === 'uploading')
</script>

<template>
  <UModal v-model:open="open" :ui="{ content: 'max-w-xl' }">
    <template #header>
      <div class="flex items-center gap-3">
        <UIcon name="i-lucide-mic" class="size-6 text-primary" />
        <div>
          <h2 class="text-xl font-semibold">
            Upload for Transcription
          </h2>
          <p class="text-sm text-muted mt-0.5">
            Upload audio/video or paste a URL to transcribe with AI
          </p>
        </div>
      </div>
    </template>

    <template #body>
      <div class="space-y-4">
        <!-- File Upload -->
        <div v-if="uploadStatus === 'idle'">
          <UFileUpload
            v-model="selectedFile"
            :accept="acceptedTypes"
            label="Drop your audio or video file here"
            description="MP3, MP4, WAV, M4A, WebM, OGG, FLAC"
            icon="i-lucide-upload-cloud"
            class="min-h-48"
          />
        </div>

        <!-- Selected File Info -->
        <div v-if="selectedFile && uploadStatus === 'idle'" class="flex items-center gap-3 p-3 bg-muted/10 rounded-lg">
          <UIcon name="i-lucide-file-audio" class="size-8 text-primary" />
          <div class="flex-1 min-w-0">
            <p class="font-medium truncate">
              {{ selectedFile.name }}
            </p>
            <p class="text-sm text-muted">
              {{ (selectedFile.size / 1024 / 1024).toFixed(2) }} MB
            </p>
          </div>
          <UButton
            icon="i-lucide-x"
            color="neutral"
            variant="ghost"
            size="sm"
            @click="selectedFile = null"
          />
        </div>

        <!-- Case Selection (only show if no caseId prop provided) -->
        <div v-if="uploadStatus === 'idle' && !props.caseId" class="space-y-2">
          <UFormField label="Associate with Case" hint="Optional">
            <USelectMenu
              v-model="selectedCaseId"
              :items="[{ label: 'No case', value: undefined }, ...(cases || []).map(c => ({ label: c.name, value: c.id }))]"
              value-key="value"
              placeholder="Select a case (optional)"
              class="w-full"
            />
          </UFormField>
        </div>

        <!-- Info about async processing -->
        <UAlert
          v-if="uploadStatus === 'idle' && canSubmit"
          color="info"
          variant="subtle"
          icon="i-lucide-info"
          title="AI Transcription"
          description="Transcription starts automatically after upload. Long files may take several minutes."
        />

        <!-- Processing Status -->
        <div v-if="isProcessing || uploadStatus === 'completed' || uploadStatus === 'failed'" class="space-y-3">
          <div class="flex items-center gap-3">
            <UIcon
              :name="uploadStatus === 'completed' ? 'i-lucide-check-circle'
                : uploadStatus === 'failed' ? 'i-lucide-x-circle'
                  : 'i-lucide-loader-circle'"
              :class="[
                'size-6',
                uploadStatus === 'completed' ? 'text-success'
                : uploadStatus === 'failed' ? 'text-error'
                  : 'text-primary animate-spin'
              ]"
            />
            <span
              :class="[
                'font-medium',
                uploadStatus === 'completed' ? 'text-success'
                : uploadStatus === 'failed' ? 'text-error' : ''
              ]"
            >
              {{ statusMessage }}
            </span>
          </div>

          <!-- Progress Bar -->
          <UProgress
            v-if="uploadStatus === 'uploading'"
            :model-value="uploadProgress?.progress || 0"
            color="primary"
          />
        </div>

        <!-- Error Display -->
        <UAlert
          v-if="uploadErrorMsg"
          color="error"
          variant="subtle"
          :description="uploadErrorMsg"
          icon="i-lucide-alert-circle"
        />
      </div>
    </template>

    <template #footer>
      <div class="flex justify-end gap-2">
        <UButton
          :label="isProcessing ? 'Cancel' : 'Close'"
          color="neutral"
          variant="ghost"
          @click="handleCancel"
        />
        <UButton
          v-if="uploadStatus === 'idle'"
          label="Upload & Transcribe"
          icon="i-lucide-sparkles"
          color="primary"
          :disabled="!canSubmit"
          @click="handleUpload"
        />
      </div>
    </template>
  </UModal>
</template>
