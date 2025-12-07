<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { listTranscriptions, updateTranscription } = useFirestore()
const { cases, listCases } = useCases()
const toast = useToast()

// Transcriptions from Firestore
const transcriptions = ref<any[]>([])
const isLoading = ref(true)

// Load transcriptions
async function loadTranscriptions() {
  try {
    transcriptions.value = await listTranscriptions()
  } catch (err) {
    console.error('Failed to load transcriptions:', err)
    transcriptions.value = []
  }
}

// Load data on client-side only (Firestore SDK doesn't work during SSR)
onMounted(async () => {
  try {
    await Promise.all([loadTranscriptions(), listCases()])
  } catch (err) {
    console.error('Failed to load data:', err)
  } finally {
    isLoading.value = false
  }
})

const showUploadModal = ref(false)

function handleUploadComplete(transcriptionId: string) {
  showUploadModal.value = false
  // Refresh the list
  loadTranscriptions()
  toast.add({
    title: 'Upload complete',
    description: 'Your file has been uploaded and is being transcribed.',
    color: 'success'
  })
}

// Stats
const stats = computed(() => ({
  total: transcriptions.value.length,
  completed: transcriptions.value.filter(t => t.status === 'completed' || t.status === 'indexed').length,
  processing: transcriptions.value.filter(t => t.status === 'processing' || t.status === 'transcribing').length
}))

const statusColors: Record<string, string> = {
  uploading: 'warning',
  processing: 'info',
  transcribing: 'info',
  indexed: 'success',
  completed: 'success',
  failed: 'error'
}

function formatDate(date: any) {
  const d = date?.toDate?.() || new Date(date)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatBytes(bytes: number) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function getCaseName(caseId: string) {
  const c = cases.value?.find(c => c.id === caseId)
  return c?.name || 'Unknown Case'
}

async function startTranscription(doc: any) {
  if (!doc.downloadUrl && !doc.storagePath) {
    toast.add({ title: 'Error', description: 'No media source available', color: 'error' })
    return
  }

  try {
    // Just update status to "processing" - Firestore trigger will handle the rest
    // This is async and won't timeout for long videos
    await updateTranscription(doc.id, { status: 'processing' })

    toast.add({
      title: 'Transcription Started',
      description: 'Processing in background. Refresh to see progress.',
      color: 'info'
    })

    // Refresh after a short delay to show the status change
    setTimeout(() => loadTranscriptions(), 1000)
  } catch (err: any) {
    console.error('Failed to start transcription:', err)
    toast.add({ title: 'Error', description: err?.message || 'Failed to start transcription', color: 'error' })
  }
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Transcriptions">
        <template #trailing>
          <UButton label="Upload Transcriptions" icon="i-lucide-upload" @click="() => showUploadModal = true" />
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <!-- Loading State -->
      <div v-if="isLoading" class="flex items-center justify-center py-20">
        <div class="text-center space-y-4">
          <UIcon name="i-lucide-loader-circle" class="size-12 text-primary animate-spin mx-auto" />
          <p class="text-muted">
            Loading transcriptions...
          </p>
        </div>
      </div>

      <div v-else class="max-w-7xl mx-auto space-y-6">
        <!-- Stats -->
        <div class="grid grid-cols-3 gap-4">
          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-mic" class="size-8 text-primary" />
              <div>
                <p class="text-2xl font-bold">
                  {{ stats.total }}
                </p>
                <p class="text-sm text-muted">
                  Total
                </p>
              </div>
            </div>
          </UCard>
          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-check-circle" class="size-8 text-success" />
              <div>
                <p class="text-2xl font-bold">
                  {{ stats.completed }}
                </p>
                <p class="text-sm text-muted">
                  Completed
                </p>
              </div>
            </div>
          </UCard>
          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-loader-circle" class="size-8 text-warning" :class="{ 'animate-spin': stats.processing > 0 }" />
              <div>
                <p class="text-2xl font-bold">
                  {{ stats.processing }}
                </p>
                <p class="text-sm text-muted">
                  Processing
                </p>
              </div>
            </div>
          </UCard>
        </div>

        <!-- Info Notice -->
        <UAlert
          color="info"
          variant="subtle"
          icon="i-lucide-sparkles"
          title="AI-Powered Transcription"
          description="Click 'Transcribe' on any audio/video file to generate a full transcript with speaker identification using Gemini AI."
        />

        <!-- Transcriptions List -->
        <UCard v-if="transcriptions.length">
          <template #header>
            <h3 class="font-semibold">
              Audio/Video Files
            </h3>
          </template>

          <div class="space-y-2">
            <div
              v-for="t in transcriptions"
              :key="t.id"
              class="flex items-center gap-4 p-4 rounded-lg hover:bg-muted/50 transition-colors"
            >
              <NuxtLink :to="`/transcripts/${t.id}`" class="flex items-center gap-4 flex-1 min-w-0">
                <div class="p-2 rounded-lg" :class="t.status === 'completed' || t.status === 'indexed' ? 'bg-success/10' : (t.status === 'processing' || t.status === 'transcribing') ? 'bg-info/10' : 'bg-warning/10'">
                  <UIcon
                    :name="(t.status === 'processing' || t.status === 'transcribing') ? 'i-lucide-loader-circle' : 'i-lucide-mic'"
                    class="size-5"
                    :class="[
                      t.status === 'completed' || t.status === 'indexed' ? 'text-success' : (t.status === 'processing' || t.status === 'transcribing') ? 'text-info' : 'text-warning',
                      (t.status === 'processing' || t.status === 'transcribing') ? 'animate-spin' : ''
                    ]"
                  />
                </div>
                <div class="flex-1 min-w-0">
                  <p class="font-medium truncate">{{ t.title || t.filename }}</p>
                  <p class="text-sm text-muted">{{ getCaseName(t.caseId) }} &bull; {{ formatBytes(t.fileSize) }}</p>
                </div>
              </NuxtLink>
              <UBadge
                :label="t.status"
                :color="statusColors[t.status] || 'neutral'"
                variant="soft"
                class="capitalize"
              />
              <span class="text-sm text-muted hidden sm:block">{{ formatDate(t.createdAt) }}</span>
              <UButton
                v-if="t.status === 'failed'"
                label="Retry"
                icon="i-lucide-refresh-cw"
                size="sm"
                color="primary"
                @click.stop="startTranscription(t)"
              />
              <UButton
                v-else-if="t.status === 'completed'"
                label="View"
                icon="i-lucide-eye"
                size="sm"
                variant="outline"
                :to="`/transcripts/${t.id}`"
              />
            </div>
          </div>
        </UCard>

        <!-- Empty State -->
        <div v-else class="text-center py-20">
          <UIcon name="i-lucide-mic" class="size-16 text-muted mx-auto mb-4 opacity-30" />
          <h3 class="text-xl font-semibold mb-2">
            No audio/video files yet
          </h3>
          <p class="text-muted mb-6">
            Upload audio or video files to transcribe
          </p>
          <UButton label="Upload Transcription" icon="i-lucide-upload" @click="() => showUploadModal = true" />
        </div>

        <!-- Upload Modal -->
        <ModalsUploadTranscriptionModal
          v-model:open="showUploadModal"
          @uploaded="handleUploadComplete"
        />
      </div>
    </template>
  </UDashboardPanel>
</template>
