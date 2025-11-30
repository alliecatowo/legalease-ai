<script setup lang="ts">
const props = defineProps<{
  caseId?: string
}>()

const open = defineModel<boolean>('open')
const emit = defineEmits<{
  'uploaded': [transcriptionId: string]
}>()

const toast = useToast()
const { uploadForTranscription, uploadProgress, isUploading, uploadError, resetUpload, cancelUpload } = useStorage()
const { transcribeMedia } = useAI()
const { createTranscription, updateTranscription, completeTranscription, failTranscription } = useFirestore()

// Input mode: 'file' or 'url'
const inputMode = ref<'file' | 'url'>('file')
const selectedFile = ref<File | null>(null)
const mediaUrl = ref('')
const transcriptionStatus = ref<'idle' | 'uploading' | 'transcribing' | 'completed' | 'failed'>('idle')
const transcriptionError = ref<string | null>(null)
const transcriptionId = ref<string | null>(null)

// Options
const enableDiarization = ref(true)
const enableSummary = ref(true)

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

const canSubmit = computed(() => {
  if (inputMode.value === 'file') {
    return !!selectedFile.value
  }
  return isValidUrl.value
})

async function handleUpload() {
  if (inputMode.value === 'file' && !selectedFile.value) return
  if (inputMode.value === 'url' && !isValidUrl.value) return

  transcriptionStatus.value = inputMode.value === 'file' ? 'uploading' : 'transcribing'
  transcriptionError.value = null

  try {
    let docId: string

    if (inputMode.value === 'file' && selectedFile.value) {
      // File upload flow
      // Step 1: Upload to Firebase Storage
      const uploadResult = await uploadForTranscription(selectedFile.value, props.caseId)

      // Step 2: Create document in Firestore (not transcription-specific)
      const { createDocument } = useDocuments()
      docId = await createDocument({
        filename: selectedFile.value.name,
        storagePath: uploadResult.path,
        downloadUrl: uploadResult.downloadUrl,
        mimeType: selectedFile.value.type,
        fileSize: selectedFile.value.size,
        status: 'processing',
        caseId: props.caseId || undefined
      })

      transcriptionId.value = docId
      transcriptionStatus.value = 'transcribing'

      // Step 3: Call transcription function
      const result = await transcribeMedia({
        url: uploadResult.downloadUrl,
        enableDiarization: enableDiarization.value,
        enableSummary: enableSummary.value
      })

      // Step 4: Update document with transcription results
      const { updateDocument } = useDocuments()
      await updateDocument(docId, {
        status: 'completed',
        extractedText: result.fullText,
        summary: result.summary,
        segments: result.segments,
        speakers: result.speakers,
        duration: result.duration,
        language: result.language
      })
    } else {
      // URL transcription flow
      // Step 1: Create transcription document
      docId = await createTranscription({
        caseId: props.caseId,
        userId: '',
        filename: isYouTubeUrl.value ? `YouTube: ${mediaUrl.value}` : mediaUrl.value.split('/').pop() || 'URL Media',
        storagePath: '',
        gsUri: '',
        downloadUrl: mediaUrl.value,
        mimeType: isYouTubeUrl.value ? 'video/youtube' : 'video/mp4',
        fileSize: 0,
        status: 'processing'
      })

      transcriptionId.value = docId

      // Step 2: Call Genkit transcription with URL
      const result = await transcribeMedia({
        url: mediaUrl.value,
        enableDiarization: enableDiarization.value,
        enableSummary: enableSummary.value
      })

      // Step 3: Save results to Firestore
      await completeTranscription(docId, {
        fullText: result.fullText,
        segments: result.segments,
        speakers: result.speakers,
        duration: result.duration,
        language: result.language,
        summary: result.summary
      })
    }

    transcriptionStatus.value = 'completed'

    toast.add({
      title: 'Transcription Complete',
      description: inputMode.value === 'file'
        ? `${selectedFile.value?.name} has been transcribed successfully.`
        : 'The media has been transcribed successfully.',
      color: 'success'
    })

    emit('uploaded', docId!)

    // Close modal after short delay
    setTimeout(() => {
      resetAndClose()
    }, 1500)

  } catch (error: any) {
    console.error('Transcription failed:', error)
    transcriptionStatus.value = 'failed'
    transcriptionError.value = error?.message || 'Failed to process transcription'

    // Update Firestore document with error
    if (transcriptionId.value && transcriptionError.value) {
      await failTranscription(transcriptionId.value, transcriptionError.value)
    }

    toast.add({
      title: 'Transcription Failed',
      description: transcriptionError.value || 'Unknown error',
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
  transcriptionStatus.value = 'idle'
  transcriptionError.value = null
  transcriptionId.value = null
  resetUpload()
  open.value = false
}

// Reset on modal close
watch(open, (isOpen) => {
  if (!isOpen) {
    selectedFile.value = null
    mediaUrl.value = ''
    inputMode.value = 'file'
    transcriptionStatus.value = 'idle'
    transcriptionError.value = null
    resetUpload()
  }
})

const statusMessage = computed(() => {
  switch (transcriptionStatus.value) {
    case 'uploading':
      return `Uploading... ${Math.round(uploadProgress.value?.progress || 0)}%`
    case 'transcribing':
      return 'Transcribing with AI... This may take a few minutes.'
    case 'completed':
      return 'Transcription complete!'
    case 'failed':
      return transcriptionError.value || 'Transcription failed'
    default:
      return ''
  }
})

const isProcessing = computed(() =>
  transcriptionStatus.value === 'uploading' || transcriptionStatus.value === 'transcribing'
)
</script>

<template>
  <UModal v-model:open="open" :ui="{ content: 'max-w-xl' }">
    <template #header>
      <div class="flex items-center gap-3">
        <UIcon name="i-lucide-mic" class="size-6 text-primary" />
        <div>
          <h2 class="text-xl font-semibold">Upload for Transcription</h2>
          <p class="text-sm text-muted mt-0.5">Upload audio/video or paste a URL to transcribe with AI</p>
        </div>
      </div>
    </template>

    <template #body>
      <div class="space-y-4">
        <!-- Input Mode Toggle -->
        <div v-if="transcriptionStatus === 'idle'" class="flex gap-2">
          <UButton
            :label="'Upload File'"
            :icon="'i-lucide-upload'"
            :color="inputMode === 'file' ? 'primary' : 'neutral'"
            :variant="inputMode === 'file' ? 'solid' : 'ghost'"
            @click="inputMode = 'file'"
          />
          <UButton
            :label="'From URL'"
            :icon="'i-lucide-link'"
            :color="inputMode === 'url' ? 'primary' : 'neutral'"
            :variant="inputMode === 'url' ? 'solid' : 'ghost'"
            @click="inputMode = 'url'"
          />
        </div>

        <!-- File Upload -->
        <div v-if="transcriptionStatus === 'idle' && inputMode === 'file'">
          <UFileUpload
            v-model="selectedFile"
            :accept="acceptedTypes"
            label="Drop your audio or video file here"
            description="MP3, MP4, WAV, M4A, WebM, OGG, FLAC"
            icon="i-lucide-upload-cloud"
            class="min-h-48"
          />
        </div>

        <!-- URL Input -->
        <div v-if="transcriptionStatus === 'idle' && inputMode === 'url'" class="space-y-3">
          <UFormField label="Media URL" hint="YouTube, direct media links">
            <UInput
              v-model="mediaUrl"
              placeholder="https://youtube.com/watch?v=... or https://example.com/video.mp4"
              icon="i-lucide-link"
              size="lg"
            />
          </UFormField>

          <div v-if="mediaUrl && isYouTubeUrl" class="flex items-center gap-2 p-3 bg-red-500/10 rounded-lg">
            <UIcon name="i-lucide-youtube" class="size-5 text-red-500" />
            <span class="text-sm">YouTube video detected</span>
          </div>

          <div v-if="mediaUrl && !isValidUrl" class="text-sm text-error">
            Please enter a valid URL
          </div>
        </div>

        <!-- Selected File Info -->
        <div v-if="selectedFile && transcriptionStatus === 'idle' && inputMode === 'file'" class="flex items-center gap-3 p-3 bg-muted/10 rounded-lg">
          <UIcon name="i-lucide-file-audio" class="size-8 text-primary" />
          <div class="flex-1 min-w-0">
            <p class="font-medium truncate">{{ selectedFile.name }}</p>
            <p class="text-sm text-muted">{{ (selectedFile.size / 1024 / 1024).toFixed(2) }} MB</p>
          </div>
          <UButton
            icon="i-lucide-x"
            color="neutral"
            variant="ghost"
            size="sm"
            @click="selectedFile = null"
          />
        </div>

        <!-- Options -->
        <div v-if="transcriptionStatus === 'idle' && canSubmit" class="space-y-3">
          <h3 class="font-medium">Options</h3>

          <UCheckbox
            v-model="enableDiarization"
            label="Speaker diarization"
            description="Identify different speakers in the recording"
          />

          <UCheckbox
            v-model="enableSummary"
            label="Generate summary"
            description="Create an AI summary of the transcript"
          />
        </div>

        <!-- Processing Status -->
        <div v-if="isProcessing || transcriptionStatus === 'completed' || transcriptionStatus === 'failed'" class="space-y-3">
          <div class="flex items-center gap-3">
            <UIcon
              :name="transcriptionStatus === 'completed' ? 'i-lucide-check-circle' :
                     transcriptionStatus === 'failed' ? 'i-lucide-x-circle' :
                     'i-lucide-loader-circle'"
              :class="[
                'size-6',
                transcriptionStatus === 'completed' ? 'text-success' :
                transcriptionStatus === 'failed' ? 'text-error' :
                'text-primary animate-spin'
              ]"
            />
            <span :class="[
              'font-medium',
              transcriptionStatus === 'completed' ? 'text-success' :
              transcriptionStatus === 'failed' ? 'text-error' : ''
            ]">
              {{ statusMessage }}
            </span>
          </div>

          <!-- Progress Bar -->
          <UProgress
            v-if="transcriptionStatus === 'uploading'"
            :model-value="uploadProgress?.progress || 0"
            color="primary"
          />

          <!-- Indeterminate progress for transcription -->
          <div v-if="transcriptionStatus === 'transcribing'" class="h-2 bg-muted/20 rounded-full overflow-hidden">
            <div class="h-full bg-primary rounded-full animate-pulse w-full" />
          </div>
        </div>

        <!-- Error Display -->
        <UAlert
          v-if="transcriptionError"
          color="error"
          variant="subtle"
          :description="transcriptionError"
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
          v-if="transcriptionStatus === 'idle'"
          label="Start Transcription"
          icon="i-lucide-sparkles"
          color="primary"
          :disabled="!canSubmit"
          @click="handleUpload"
        />
      </div>
    </template>
  </UModal>
</template>
