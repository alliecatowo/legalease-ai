<script setup lang="ts">
import type { TranscriptSegment, Speaker } from '~/composables/useAI'

definePageMeta({ layout: 'default' })

const route = useRoute()
const router = useRouter()
const toast = useToast()

const documentId = computed(() => route.params.id as string)
const { getDocument, deleteDocument, updateDocument } = useDocuments()
const { getCase } = useCases()
const { transcribeMedia, indexDocument, summarizeTranscript } = useAI()

// State
const loading = ref(true)
const document = ref<any>(null)
const caseData = ref<any>(null)
const error = ref<string | null>(null)
const showDeleteModal = ref(false)
const isDeleting = ref(false)
const isTranscribing = ref(false)
const isAnalyzing = ref(false)

// Media player state
const mediaRef = ref<HTMLAudioElement | HTMLVideoElement | null>(null)
const currentTime = ref(0)
const isPlaying = ref(false)

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    document.value = await getDocument(documentId.value)
    if (!document.value) {
      error.value = 'File not found'
      return
    }
    if (document.value.caseId) {
      caseData.value = await getCase(document.value.caseId)
    }
  } catch (err: any) {
    error.value = err?.message || 'Failed to load file'
  } finally {
    loading.value = false
  }
}

await fetchData()

// Computed
const segments = computed<TranscriptSegment[]>(() => document.value?.segments || [])
const speakers = computed<Speaker[]>(() => document.value?.speakers || [])
const hasTranscript = computed(() => document.value?.status === 'completed' && document.value?.extractedText)
const isVideo = computed(() => document.value?.mimeType?.startsWith('video/'))

const activeSegmentIndex = computed(() => {
  if (!segments.value.length) return -1
  const time = currentTime.value
  return segments.value.findIndex((s, i) => {
    const next = segments.value[i + 1]
    return time >= s.start && (!next || time < next.start)
  })
})

// Helpers
function formatBytes(bytes: number) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function formatDate(date: any) {
  const d = date?.toDate?.() || new Date(date)
  return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
}

function formatTime(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatDuration(seconds: number) {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m ${s}s`
}

function getSpeakerName(speakerId: string | undefined) {
  if (!speakerId) return null
  const speaker = speakers.value.find(s => s.id === speakerId)
  return speaker?.inferredName || speakerId
}

const statusColors: Record<string, string> = {
  uploading: 'warning',
  processing: 'info',
  indexed: 'success',
  completed: 'success',
  failed: 'error'
}

// Media controls
function onTimeUpdate() {
  if (mediaRef.value) {
    currentTime.value = mediaRef.value.currentTime
  }
}

function seekTo(time: number) {
  if (mediaRef.value) {
    mediaRef.value.currentTime = time
    mediaRef.value.play()
    isPlaying.value = true
  }
}

function togglePlayPause() {
  if (!mediaRef.value) return
  if (isPlaying.value) {
    mediaRef.value.pause()
  } else {
    mediaRef.value.play()
  }
  isPlaying.value = !isPlaying.value
}

// Actions
async function startTranscription() {
  if (!document.value?.downloadUrl) {
    toast.add({ title: 'Error', description: 'No download URL available', color: 'error' })
    return
  }

  isTranscribing.value = true
  try {
    await updateDocument(documentId.value, { status: 'processing' })
    document.value.status = 'processing'

    const result = await transcribeMedia({
      url: document.value.downloadUrl,
      enableDiarization: true,
      enableSummary: true
    })

    await updateDocument(documentId.value, {
      status: 'completed',
      extractedText: result.fullText,
      summary: result.summary,
      segments: result.segments,
      speakers: result.speakers,
      duration: result.duration,
      language: result.language
    })

    // Index transcript into Qdrant for search
    if (result.fullText) {
      try {
        await indexDocument({
          documentId: documentId.value,
          text: result.fullText,
          caseId: document.value.caseId,
          filename: document.value.filename,
          documentType: 'transcript'
        })
      } catch (indexErr) {
        console.warn('Failed to index transcript:', indexErr)
      }
    }

    toast.add({ title: 'Success', description: 'Transcription complete', color: 'success' })
    await fetchData()
  } catch (err: any) {
    console.error('Transcription failed:', err)
    await updateDocument(documentId.value, { status: 'failed' })
    toast.add({ title: 'Error', description: err?.message || 'Transcription failed', color: 'error' })
    await fetchData()
  } finally {
    isTranscribing.value = false
  }
}

async function generateAnalysis() {
  if (!document.value?.extractedText) {
    toast.add({ title: 'Error', description: 'No transcript text available', color: 'error' })
    return
  }

  isAnalyzing.value = true
  try {
    const result = await summarizeTranscript({
      transcript: document.value.extractedText,
      caseContext: caseData.value?.name,
      outputType: 'legal'
    })

    await updateDocument(documentId.value, {
      analysis: result
    })

    toast.add({ title: 'Success', description: 'Analysis complete', color: 'success' })
    await fetchData()
  } catch (err: any) {
    console.error('Analysis failed:', err)
    toast.add({ title: 'Error', description: err?.message || 'Analysis failed', color: 'error' })
  } finally {
    isAnalyzing.value = false
  }
}

function handleDownload() {
  if (!document.value?.downloadUrl) return
  window.open(document.value.downloadUrl, '_blank')
}

async function handleDelete() {
  if (!document.value) return
  isDeleting.value = true
  try {
    await deleteDocument(documentId.value)
    toast.add({ title: 'Deleted', description: 'File deleted successfully', color: 'success' })
    router.push('/transcripts')
  } catch (err) {
    toast.add({ title: 'Error', description: 'Failed to delete file', color: 'error' })
    isDeleting.value = false
  }
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar>
        <template #leading>
          <div class="flex items-center gap-3">
            <UButton icon="i-lucide-arrow-left" color="neutral" variant="ghost" @click="router.back()" />
            <USeparator orientation="vertical" class="h-6" />
            <UBreadcrumb :items="[
              { label: 'Transcriptions', to: '/transcripts', icon: 'i-lucide-mic' },
              { label: document?.filename || 'Audio File', icon: 'i-lucide-file-audio' }
            ]" />
          </div>
        </template>
        <template #trailing>
          <div class="flex items-center gap-2">
            <UButton icon="i-lucide-download" color="neutral" variant="ghost" @click="handleDownload" />
            <UButton icon="i-lucide-trash" color="error" variant="ghost" @click="showDeleteModal = true" />
          </div>
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <UIcon name="i-lucide-loader-circle" class="size-12 text-primary animate-spin" />
      </div>

      <!-- Error -->
      <div v-else-if="error || !document" class="text-center py-20">
        <UIcon name="i-lucide-alert-circle" class="size-16 text-error mx-auto mb-4 opacity-50" />
        <h3 class="text-xl font-semibold mb-2">File Not Found</h3>
        <p class="text-muted mb-6">{{ error || 'The file you are looking for does not exist.' }}</p>
        <UButton label="Back to Transcriptions" icon="i-lucide-arrow-left" to="/transcripts" />
      </div>

      <!-- Content -->
      <div v-else class="max-w-5xl mx-auto p-6 space-y-6">
        <!-- Header -->
        <div class="flex items-start gap-6 p-6 bg-muted/10 rounded-xl border border-default">
          <div class="p-4 bg-primary/10 rounded-xl">
            <UIcon :name="isVideo ? 'i-lucide-video' : 'i-lucide-mic'" class="size-12 text-primary" />
          </div>
          <div class="flex-1 min-w-0">
            <h1 class="text-2xl font-bold mb-2">{{ document.title || document.filename }}</h1>
            <div class="flex items-center gap-3 flex-wrap">
              <UBadge :label="document.status || 'pending'" :color="statusColors[document.status] || 'neutral'" variant="soft" />
              <span class="text-sm text-muted">{{ formatBytes(document.fileSize) }}</span>
              <span v-if="document.duration" class="text-sm text-muted">{{ formatDuration(document.duration) }}</span>
              <span v-if="document.language" class="text-sm text-muted">{{ document.language }}</span>
            </div>
            <div v-if="caseData" class="mt-3 flex items-center gap-2 text-sm">
              <UIcon name="i-lucide-briefcase" class="size-4 text-muted" />
              <NuxtLink :to="`/cases/${caseData.id}`" class="text-primary hover:underline">
                {{ caseData.name }}
              </NuxtLink>
            </div>
          </div>
          <UButton
            v-if="!hasTranscript && document.status !== 'processing'"
            label="Transcribe"
            icon="i-lucide-sparkles"
            :loading="isTranscribing"
            @click="startTranscription"
          />
        </div>

        <!-- Processing State -->
        <UAlert
          v-if="document.status === 'processing' || isTranscribing"
          color="info"
          variant="subtle"
          icon="i-lucide-loader-circle"
          title="Transcription in Progress"
          description="AI is processing your audio. This may take a few minutes depending on the file length."
        />

        <!-- Summary -->
        <UCard v-if="document.summary || document.analysis?.summary">
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-sparkles" class="size-5 text-primary" />
                <h3 class="font-semibold">AI Summary</h3>
              </div>
              <UButton
                v-if="hasTranscript && !document.analysis"
                label="Deep Analysis"
                icon="i-lucide-brain"
                size="sm"
                variant="outline"
                :loading="isAnalyzing"
                @click="generateAnalysis"
              />
            </div>
          </template>
          <p class="text-muted leading-relaxed whitespace-pre-wrap">{{ document.analysis?.summary || document.summary }}</p>
        </UCard>

        <!-- Detailed Analysis -->
        <div v-if="document.analysis" class="grid md:grid-cols-2 gap-4">
          <!-- Key Moments -->
          <UCard v-if="document.analysis.keyMoments?.length">
            <template #header>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-star" class="size-5 text-warning" />
                <h3 class="font-semibold">Key Moments</h3>
              </div>
            </template>
            <div class="space-y-3">
              <div v-for="(moment, i) in document.analysis.keyMoments" :key="i" class="flex gap-3">
                <UBadge
                  :label="moment.importance"
                  :color="moment.importance === 'high' ? 'error' : moment.importance === 'medium' ? 'warning' : 'neutral'"
                  variant="soft"
                  size="xs"
                  class="shrink-0"
                />
                <div class="text-sm">
                  <p>{{ moment.description }}</p>
                  <p v-if="moment.speakers?.length" class="text-xs text-muted mt-1">{{ moment.speakers.join(', ') }}</p>
                </div>
              </div>
            </div>
          </UCard>

          <!-- Action Items -->
          <UCard v-if="document.analysis.actionItems?.length">
            <template #header>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-check-square" class="size-5 text-success" />
                <h3 class="font-semibold">Action Items</h3>
              </div>
            </template>
            <ul class="space-y-2">
              <li v-for="(item, i) in document.analysis.actionItems" :key="i" class="flex items-start gap-2 text-sm">
                <UIcon name="i-lucide-circle" class="size-3 text-muted mt-1.5 shrink-0" />
                <span>{{ item }}</span>
              </li>
            </ul>
          </UCard>

          <!-- Topics -->
          <UCard v-if="document.analysis.topics?.length">
            <template #header>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-tags" class="size-5 text-info" />
                <h3 class="font-semibold">Topics</h3>
              </div>
            </template>
            <div class="flex flex-wrap gap-2">
              <UBadge
                v-for="topic in document.analysis.topics"
                :key="topic"
                :label="topic"
                variant="soft"
              />
            </div>
          </UCard>

          <!-- Entities -->
          <UCard v-if="document.analysis.entities">
            <template #header>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-users" class="size-5 text-primary" />
                <h3 class="font-semibold">Entities</h3>
              </div>
            </template>
            <div class="space-y-3 text-sm">
              <div v-if="document.analysis.entities.people?.length">
                <p class="text-xs text-muted mb-1">People</p>
                <p>{{ document.analysis.entities.people.join(', ') }}</p>
              </div>
              <div v-if="document.analysis.entities.organizations?.length">
                <p class="text-xs text-muted mb-1">Organizations</p>
                <p>{{ document.analysis.entities.organizations.join(', ') }}</p>
              </div>
              <div v-if="document.analysis.entities.locations?.length">
                <p class="text-xs text-muted mb-1">Locations</p>
                <p>{{ document.analysis.entities.locations.join(', ') }}</p>
              </div>
              <div v-if="document.analysis.entities.dates?.length">
                <p class="text-xs text-muted mb-1">Dates & Times</p>
                <p>{{ document.analysis.entities.dates.join(', ') }}</p>
              </div>
            </div>
          </UCard>
        </div>

        <!-- Generate Analysis Button (when transcript exists but no analysis) -->
        <UCard v-else-if="hasTranscript && !document.analysis" class="text-center">
          <div class="py-4">
            <UIcon name="i-lucide-brain" class="size-10 text-muted mx-auto mb-3 opacity-50" />
            <h4 class="font-medium mb-2">Deep Analysis Available</h4>
            <p class="text-sm text-muted mb-4">Extract key moments, action items, topics, and entities from this transcript</p>
            <UButton
              label="Generate Analysis"
              icon="i-lucide-sparkles"
              :loading="isAnalyzing"
              @click="generateAnalysis"
            />
          </div>
        </UCard>

        <!-- Media Player -->
        <UCard v-if="document.downloadUrl">
          <template #header>
            <div class="flex items-center justify-between">
              <h3 class="font-semibold">Media Player</h3>
              <span class="text-sm text-muted">{{ formatTime(currentTime) }}</span>
            </div>
          </template>
          <div class="space-y-4">
            <video
              v-if="isVideo"
              ref="mediaRef"
              :src="document.downloadUrl"
              controls
              class="w-full rounded-lg bg-black"
              @timeupdate="onTimeUpdate"
              @play="isPlaying = true"
              @pause="isPlaying = false"
            />
            <audio
              v-else
              ref="mediaRef"
              :src="document.downloadUrl"
              controls
              class="w-full"
              @timeupdate="onTimeUpdate"
              @play="isPlaying = true"
              @pause="isPlaying = false"
            />
          </div>
        </UCard>

        <!-- Speakers -->
        <div v-if="speakers.length > 1" class="flex items-center gap-2 flex-wrap">
          <span class="text-sm text-muted">Speakers:</span>
          <UBadge
            v-for="speaker in speakers"
            :key="speaker.id"
            :label="speaker.inferredName || speaker.id"
            variant="outline"
            size="sm"
          />
        </div>

        <!-- Transcript with Follow-Along -->
        <UCard v-if="hasTranscript">
          <template #header>
            <div class="flex items-center justify-between">
              <h3 class="font-semibold">Transcript</h3>
              <span class="text-sm text-muted">{{ segments.length }} segments</span>
            </div>
          </template>

          <!-- Segmented Transcript -->
          <div v-if="segments.length" class="space-y-2 max-h-[600px] overflow-y-auto">
            <div
              v-for="(segment, index) in segments"
              :key="index"
              class="flex gap-3 p-3 rounded-lg cursor-pointer transition-colors"
              :class="[
                activeSegmentIndex === index ? 'bg-primary/10 ring-1 ring-primary/30' : 'hover:bg-muted/30'
              ]"
              @click="seekTo(segment.start)"
            >
              <button
                class="text-xs text-primary font-mono shrink-0 hover:underline"
                @click.stop="seekTo(segment.start)"
              >
                {{ formatTime(segment.start) }}
              </button>
              <div class="flex-1 min-w-0">
                <span v-if="segment.speaker" class="text-xs font-medium text-primary mr-2">
                  {{ getSpeakerName(segment.speaker) }}:
                </span>
                <span class="text-sm">{{ segment.text }}</span>
              </div>
            </div>
          </div>

          <!-- Plain Text Fallback -->
          <div v-else class="prose prose-sm max-w-none">
            <p class="whitespace-pre-wrap text-muted">{{ document.extractedText }}</p>
          </div>
        </UCard>

        <!-- No Transcript Yet -->
        <div v-else-if="document.status !== 'processing' && !isTranscribing" class="text-center py-12">
          <UIcon name="i-lucide-mic-off" class="size-16 text-muted mx-auto mb-4 opacity-30" />
          <h3 class="text-xl font-semibold mb-2">No Transcript Yet</h3>
          <p class="text-muted mb-6">Click "Transcribe" to generate an AI-powered transcript with speaker identification</p>
          <UButton
            label="Start Transcription"
            icon="i-lucide-sparkles"
            :loading="isTranscribing"
            @click="startTranscription"
          />
        </div>

        <!-- Info -->
        <div class="grid grid-cols-2 gap-4">
          <UCard :ui="{ body: 'p-4' }">
            <p class="text-xs text-muted mb-1">Filename</p>
            <p class="font-medium truncate">{{ document.filename }}</p>
          </UCard>
          <UCard :ui="{ body: 'p-4' }">
            <p class="text-xs text-muted mb-1">Uploaded</p>
            <p class="font-medium">{{ formatDate(document.createdAt) }}</p>
          </UCard>
        </div>
      </div>
    </template>
  </UDashboardPanel>

  <!-- Delete Modal -->
  <ClientOnly>
    <UModal v-model:open="showDeleteModal" title="Delete File">
      <template #body>
        <p class="text-muted">
          Are you sure you want to delete <strong>{{ document?.filename }}</strong>? This cannot be undone.
        </p>
      </template>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton label="Cancel" variant="ghost" @click="showDeleteModal = false" />
          <UButton label="Delete" color="error" :loading="isDeleting" @click="handleDelete" />
        </div>
      </template>
    </UModal>
  </ClientOnly>
</template>
