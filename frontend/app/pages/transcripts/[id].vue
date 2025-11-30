<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import type { TranscriptSegment, Speaker } from '~/types/transcription'

definePageMeta({
  layout: 'default'
})

const route = useRoute()
const router = useRouter()
const toast = useToast()

const { getTranscription, updateTranscription, deleteTranscription: deleteTranscriptionDoc } = useFirestore()
const { getCase } = useCases()
const { transcribeMedia, summarizeTranscript } = useAI()

const transcriptId = computed(() => route.params.id as string)

// State
const transcript = ref<Transcription | null>(null)
const isLoading = ref(true)
const error = ref<string | null>(null)

// Playback state
const currentTime = ref(0)
const isPlaying = ref(false)
const selectedSegment = ref<TranscriptSegment | null>(null)

// Search and filters
const searchQuery = ref('')
const selectedSpeaker = ref<string | null>(null)
const showOnlyKeyMoments = ref(false)
const searchMode = ref<'smart' | 'keyword'>('smart')
const isSearching = ref(false)
const searchResults = ref<Set<number>>(new Set())

// UI state
const showExportMenu = ref(false)
const isExporting = ref(false)
const editingSegmentId = ref<string | null>(null)
const editText = ref('')
const editingSpeakerId = ref<string | null>(null)
const editSpeakerName = ref('')
const editSpeakerRole = ref('')
const autoScrollEnabled = ref(true)
const flashSegmentId = ref<string | null>(null)
// Metadata sidebar defaults: visible and expanded
const metadataSidebarOpen = ref(true)
const metadataSidebarCollapsed = ref(false)

// Smart search using backend API - DISABLED (needs backend)
async function performSmartSearch() {
  // TODO: Implement smart search with Qdrant/backend
  searchResults.value = new Set()
  isSearching.value = false
  
  toast.add({
    title: 'Smart search unavailable',
    description: 'Smart search requires backend support',
    color: 'warning'
  })
}

// Debounced smart search
const debouncedSmartSearch = useDebounceFn(performSmartSearch, 500)

// Computed property for active segment ID
const activeSegmentId = computed(() => {
  if (!transcript.value) return null
  const segment = transcript.value.segments.find(segment =>
    currentTime.value >= segment.start && currentTime.value <= segment.end
  )
  return segment?.id || null
})

// Watch for search changes
watch([searchQuery, searchMode], () => {
  if (searchMode.value === 'smart' && searchQuery.value.trim()) {
    debouncedSmartSearch()
  } else {
    searchResults.value = new Set()
  }
})

// Auto-scroll to follow active segment
watch(activeSegmentId, (newSegmentId) => {
  if (!autoScrollEnabled.value || !newSegmentId || !transcript.value) return

  const index = filteredSegments.value.findIndex(s => s.id === newSegmentId)

  if (index !== -1 && rowVirtualizer.value) {
    rowVirtualizer.value.scrollToIndex(index, { align: 'center', behavior: 'smooth' })
  }
})

// Computed
const filteredSegments = computed(() => {
  if (!transcript.value) return []

  let segments = transcript.value.segments

  if (searchQuery.value.trim()) {
    if (searchMode.value === 'smart') {
      if (!isSearching.value) {
        segments = segments.filter((s, index) => searchResults.value.has(index))
      }
    } else {
      const query = searchQuery.value.toLowerCase()
      segments = segments.filter(s =>
        s.text.toLowerCase().includes(query) ||
        (getSpeaker(s.speaker)?.name?.toLowerCase() || '').includes(query)
      )
    }
  }

  if (selectedSpeaker.value) {
    segments = segments.filter(s => s.speaker === selectedSpeaker.value)
  }

  if (showOnlyKeyMoments.value) {
    segments = segments.filter(s => s.isKeyMoment)
  }

  return segments
})

// TanStack Virtual Setup
const scrollContainerRef = ref<HTMLElement | null>(null)

const rowVirtualizerOptions = computed(() => {
  return {
    count: filteredSegments.value.length,
    getScrollElement: () => scrollContainerRef.value,
    estimateSize: () => 128,
    overscan: 8,
  }
})

const rowVirtualizer = useVirtualizer(rowVirtualizerOptions)
const virtualRows = computed(() => rowVirtualizer.value.getVirtualItems())
const totalSize = computed(() => rowVirtualizer.value.getTotalSize())

const currentSegment = computed(() => {
  if (!transcript.value) return null
  return transcript.value.segments.find(segment =>
    currentTime.value >= segment.start && currentTime.value <= segment.end
  ) || null
})

const keyMoments = computed(() => {
  if (!transcript.value) return []
  return transcript.value.segments.filter(s => s.isKeyMoment)
})

const transcriptStats = computed(() => {
  if (!transcript.value) return null

  const totalWords = transcript.value.segments.reduce((acc, seg) => {
    return acc + seg.text.split(/\s+/).length
  }, 0)

  const speakerStats = transcript.value.speakers.map(speaker => {
    const speakerSegments = transcript.value!.segments.filter(s => s.speaker === speaker.id)
    const speakingTime = speakerSegments.reduce((acc, seg) => acc + (seg.end - seg.start), 0)
    const wordCount = speakerSegments.reduce((acc, seg) => {
      return acc + seg.text.split(/\s+/).length
    }, 0)

    return {
      speaker,
      segmentCount: speakerSegments.length,
      speakingTime,
      wordCount,
      percentage: (speakingTime / transcript.value!.duration) * 100
    }
  })

  return {
    totalWords,
    totalSegments: transcript.value.segments.length,
    totalSpeakers: transcript.value.speakers.length,
    duration: transcript.value.duration,
    keyMoments: keyMoments.value.length,
    speakerStats
  }
})

// Helper functions
function getSpeaker(speakerId?: string): Speaker | undefined {
  return transcript.value?.speakers.find(s => s.id === speakerId)
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)

  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }
  return `${m}:${String(s).padStart(2, '0')}`
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)

  if (h > 0) return `${h}h ${m}m`
  return `${m} min`
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function seekToSegment(segment: TranscriptSegment, fromWaveform = false) {
  selectedSegment.value = segment
  currentTime.value = segment.start

  if (fromWaveform) {
    flashSegmentId.value = segment.id
    setTimeout(() => { flashSegmentId.value = null }, 1000)
    if (!autoScrollEnabled.value) autoScrollEnabled.value = true
  }

  const index = filteredSegments.value.findIndex(s => s.id === segment.id)
  if (index !== -1 && rowVirtualizer.value) {
    rowVirtualizer.value.scrollToIndex(index, { align: 'center' })
  }
}

function handleWaveformClick(time: number) {
  if (!transcript.value) return

  const segment = transcript.value.segments.find(s =>
    time >= s.start && time < s.end
  )

  if (segment) {
    seekToSegment(segment, true)
  }
}

async function toggleKeyMoment(segmentId: string) {
  if (!transcript.value) return

  const segment = transcript.value.segments.find(s => s.id === segmentId)
  if (!segment) return

  const newStatus = !segment.isKeyMoment

  try {
    segment.isKeyMoment = newStatus

    // Update in Firestore
    await updateTranscription(transcriptId.value, {
      segments: transcript.value.segments
    })

    toast.add({
      title: newStatus ? 'Marked as key moment' : 'Removed key moment',
      color: 'success'
    })
  } catch (err: any) {
    segment.isKeyMoment = !newStatus

    toast.add({
      title: 'Failed to update key moment',
      description: err.message || 'An error occurred',
      color: 'error'
    })
  }
}

async function exportTranscript(format: 'docx' | 'srt' | 'vtt') {
  // TODO: Implement export functionality
  toast.add({
    title: 'Export unavailable',
    description: 'Export feature requires backend support',
    color: 'warning'
  })
}

function getContentType(format: string): string {
  const types = {
    docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    srt: 'text/plain',
    vtt: 'text/vtt'
  }
  return types[format as keyof typeof types] || 'text/plain'
}

async function copyTranscriptToClipboard() {
  if (!transcript.value) return

  let text = `${transcript.value.title}\n\n`

  transcript.value.segments.forEach(segment => {
    const speaker = getSpeaker(segment.speaker)
    const speakerName = speaker?.name || 'Unknown'
    const timestamp = formatTime(segment.start)
    text += `[${timestamp}] ${speakerName}: ${segment.text}\n\n`
  })

  await navigator.clipboard.writeText(text)

  toast.add({
    title: 'Copied to clipboard',
    description: 'Full transcript copied',
    color: 'success'
  })
}

async function copySegmentToClipboard(segment: TranscriptSegment) {
  const speaker = getSpeaker(segment.speaker)
  const speakerName = speaker?.name || 'Unknown'
  const timestamp = formatTime(segment.start)
  const text = `[${timestamp}] ${speakerName}: ${segment.text}`

  await navigator.clipboard.writeText(text)

  toast.add({
    title: 'Copied to clipboard',
    description: 'Segment copied',
    color: 'success'
  })
}

function startEdit(segment: TranscriptSegment) {
  editingSegmentId.value = segment.id
  editText.value = segment.text
}

async function saveEdit(segmentId: string) {
  if (!transcript.value) return

  const segment = transcript.value.segments.find(s => s.id === segmentId)
  if (segment) {
    const originalText = segment.text
    segment.text = editText.value

    // Persist to Firestore
    try {
      await updateTranscription(transcriptId.value, {
        segments: transcript.value.segments
      })
      toast.add({
        title: 'Segment updated',
        color: 'success'
      })
    } catch (err: any) {
      // Rollback on error
      segment.text = originalText
      toast.add({
        title: 'Failed to save',
        description: err.message || 'An error occurred',
        color: 'error'
      })
    }
  }

  editingSegmentId.value = null
  editText.value = ''
}

function cancelEdit() {
  editingSegmentId.value = null
  editText.value = ''
}

function startEditSpeaker(speaker: Speaker) {
  editingSpeakerId.value = speaker.id
  editSpeakerName.value = speaker.name
  editSpeakerRole.value = speaker.role || ''
}

async function saveSpeakerEdit() {
  if (!transcript.value || !editingSpeakerId.value) return

  const speakerId = editingSpeakerId.value
  const speaker = transcript.value.speakers.find(s => s.id === speakerId)
  if (!speaker) return

  const originalName = speaker.name
  const originalRole = speaker.role

  try {
    speaker.name = editSpeakerName.value
    speaker.role = editSpeakerRole.value || undefined

    editingSpeakerId.value = null
    editSpeakerName.value = ''
    editSpeakerRole.value = ''

    // Update in Firestore
    await updateTranscription(transcriptId.value, {
      speakers: transcript.value.speakers
    })

    toast.add({
      title: 'Speaker updated',
      description: `Updated ${speaker.name}`,
      color: 'success'
    })
  } catch (err: any) {
    speaker.name = originalName
    speaker.role = originalRole

    toast.add({
      title: 'Failed to update speaker',
      description: err.message || 'An error occurred',
      color: 'error'
    })
  }
}

function cancelSpeakerEdit() {
  editingSpeakerId.value = null
  editSpeakerName.value = ''
  editSpeakerRole.value = ''
}

async function handleDeleteTranscription() {
  if (!transcript.value) return

  const confirmed = confirm(`Are you sure you want to delete "${transcript.value.title}"? This action cannot be undone.`)
  if (!confirmed) return

  try {
    await deleteTranscriptionDoc(transcriptId.value)
    toast.add({
      title: 'Transcription deleted',
      description: 'The transcription has been permanently deleted',
      color: 'success'
    })
    router.push('/transcripts')
  } catch (err: any) {
    toast.add({
      title: 'Failed to delete transcription',
      description: err.message || 'An error occurred',
      color: 'error'
    })
  }
}

async function loadTranscript() {
  isLoading.value = true
  error.value = null

  try {
    const doc = await getTranscription(transcriptId.value)
    if (!doc) {
      error.value = 'Transcript not found'
      return
    }

    // Adapt Firestore document to transcript format
    transcript.value = {
      id: doc.id,
      title: doc.filename,
      audioUrl: doc.downloadUrl,
      duration: doc.duration || 0,
      segments: doc.segments || [],
      speakers: doc.speakers || [],
      createdAt: doc.createdAt?.toDate?.()?.toISOString() || new Date().toISOString(),
      caseId: doc.caseId,
      status: doc.status
    } as any
  } catch (err: any) {
    error.value = err.message || 'Failed to load transcript'
    console.error('Error loading transcript:', err)
  } finally {
    isLoading.value = false
  }
}

// Keyboard shortcuts
defineShortcuts({
  'space': {
    usingInput: false,
    handler: () => {
      isPlaying.value = !isPlaying.value
    }
  },
  'meta_f': {
    handler: () => {
      const searchInput = document.querySelector('input[placeholder*="Search"]') as HTMLInputElement
      searchInput?.focus()
    }
  },
  'escape': {
    handler: () => {
      if (editingSegmentId.value) {
        cancelEdit()
      } else {
        searchQuery.value = ''
        selectedSpeaker.value = null
        showOnlyKeyMoments.value = false
        searchMode.value = 'smart'
      }
    }
  },
  'a': {
    usingInput: false,
    handler: () => {
      autoScrollEnabled.value = !autoScrollEnabled.value
    }
  }
})

onMounted(async () => {
  await loadTranscript()
})
</script>

<template>
  <UDashboardPanel id="transcript-main" resizable>
    <template #header>
      <div class="h-16 px-4 sm:px-6 flex items-center justify-between gap-4 border-b border-default">
        <div class="flex items-center gap-4 min-w-0">
          <UButton
            icon="i-lucide-arrow-left"
            color="neutral"
            variant="ghost"
            @click="router.push('/transcripts')"
          />
          <h1 class="text-xl font-semibold truncate">{{ transcript?.title || 'Transcript' }}</h1>
        </div>

        <div v-if="transcript" class="flex items-center gap-2 shrink-0">
          <UButton
            icon="i-lucide-copy"
            color="neutral"
            variant="ghost"
            label="Copy All"
            @click="copyTranscriptToClipboard"
          />

          <UDropdownMenu
            :items="[
              [
                {
                  label: 'Download Original Audio',
                  icon: 'i-lucide-music',
                  click: async () => {
                    const audioUrl = transcript?.audioUrl
                    if (audioUrl) {
                      const link = document.createElement('a')
                      link.href = audioUrl
                      link.download = `${transcript.title}.mp3`
                      link.click()
                    } else {
                      toast.add({
                        title: 'Audio not available',
                        description: 'No audio file found for this transcript',
                        color: 'warning'
                      })
                    }
                  }
                },
                { label: 'Export as DOCX', icon: 'i-lucide-file-text', click: () => exportTranscript('docx') },
                { label: 'Export as SRT', icon: 'i-lucide-captions', click: () => exportTranscript('srt') },
                { label: 'Export as VTT', icon: 'i-lucide-captions', click: () => exportTranscript('vtt') }
              ],
              [
                { label: 'Delete Transcription', icon: 'i-lucide-trash-2', click: handleDeleteTranscription, class: 'text-error' }
              ]
            ]"
          >
            <UButton
              icon="i-lucide-download"
              color="primary"
              :loading="isExporting"
              label="Export"
            />
          </UDropdownMenu>

          <UButton
            :icon="metadataSidebarOpen ? 'i-lucide-panel-right-close' : 'i-lucide-panel-right-open'"
            color="neutral"
            variant="ghost"
            @click="metadataSidebarOpen = !metadataSidebarOpen"
          />
        </div>
      </div>
    </template>

    <template #body>
      <div class="h-full overflow-y-auto -m-4 sm:-m-6 p-4 sm:p-6">
        <!-- Loading State -->
        <div v-if="isLoading" class="flex items-center justify-center min-h-full p-6">
          <div class="text-center space-y-4">
            <UIcon name="i-lucide-loader-circle" class="size-12 text-primary animate-spin mx-auto" />
            <div>
              <h3 class="text-lg font-semibold">Loading transcript...</h3>
              <p class="text-sm text-muted">Please wait while we fetch your transcript</p>
            </div>
          </div>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="flex items-center justify-center min-h-full p-6">
          <UCard class="max-w-md">
            <div class="text-center space-y-4">
              <UIcon name="i-lucide-alert-circle" class="size-16 text-error mx-auto" />
              <div>
                <h3 class="text-xl font-bold text-highlighted mb-2">Error Loading Transcript</h3>
                <p class="text-muted">{{ error }}</p>
              </div>
              <UButton
                label="Try Again"
                icon="i-lucide-refresh-cw"
                color="primary"
                @click="loadTranscript"
              />
            </div>
          </UCard>
        </div>

        <!-- Main Content -->
        <div v-else-if="transcript" class="space-y-6">
          <!-- Audio Player -->
          <LazyWaveformPlayer
            v-if="transcript.audioUrl"
            :audio-url="transcript.audioUrl"
            :transcription-id="transcript.id"
            :current-time="currentTime"
            :segments="transcript.segments"
            :selected-segment-id="selectedSegment?.id"
            :key-moments="keyMoments"
            @update:current-time="currentTime = $event"
            @update:is-playing="isPlaying = $event"
            @segment-click="seekToSegment"
            @waveform-click="handleWaveformClick"
          />

          <!-- Search and Filters -->
          <div class="space-y-3">
            <div class="flex items-center gap-3">
              <UTooltip :text="autoScrollEnabled ? 'Click to stop following (or press A)' : 'Click to follow along (or press A)'">
                <UButton
                  :icon="autoScrollEnabled ? 'i-lucide-radio' : 'i-lucide-circle'"
                  :label="autoScrollEnabled ? 'Following' : 'Paused'"
                  :color="autoScrollEnabled ? 'primary' : 'neutral'"
                  :variant="autoScrollEnabled ? 'solid' : 'outline'"
                  size="sm"
                  @click="autoScrollEnabled = !autoScrollEnabled"
                />
              </UTooltip>

              <UInput
                v-model="searchQuery"
                icon="i-lucide-search"
                placeholder="Search in transcript... (Cmd+F)"
                class="flex-1"
                size="md"
              >
                <template #trailing>
                  <UButton
                    v-if="searchQuery"
                    icon="i-lucide-x"
                    color="neutral"
                    variant="ghost"
                    size="xs"
                    @click="searchQuery = ''"
                  />
                </template>
              </UInput>

              <UFieldGroup v-if="searchQuery">
                <UTooltip text="Smart Search (AI-powered semantic + keyword matching)">
                  <UButton
                    icon="i-lucide-sparkles"
                    :color="searchMode === 'smart' ? 'primary' : 'neutral'"
                    :variant="searchMode === 'smart' ? 'soft' : 'ghost'"
                    label="Smart"
                    size="sm"
                    @click="searchMode = 'smart'"
                  />
                </UTooltip>
                <UTooltip text="Keyword Search (Exact BM25 text matching)">
                  <UButton
                    icon="i-lucide-search"
                    :color="searchMode === 'keyword' ? 'warning' : 'neutral'"
                    :variant="searchMode === 'keyword' ? 'soft' : 'ghost'"
                    label="Keyword"
                    size="sm"
                    @click="searchMode = 'keyword'"
                  />
                </UTooltip>
              </UFieldGroup>

              <USelectMenu
                v-model="selectedSpeaker"
                :items="[
                  { label: 'All Speakers', value: null },
                  ...transcript.speakers.map(s => ({ label: s.name, value: s.id }))
                ]"
                placeholder="Filter by speaker"
                class="min-w-[200px]"
              >
                <template #label>
                  <div class="flex items-center gap-2">
                    <UIcon name="i-lucide-users" class="size-4" />
                    <span>{{ selectedSpeaker ? getSpeaker(selectedSpeaker)?.name : 'All Speakers' }}</span>
                  </div>
                </template>
              </USelectMenu>

              <UCheckbox v-model="showOnlyKeyMoments" label="Key Moments Only">
                <template #label>
                  <div class="flex items-center gap-2">
                    <UIcon name="i-lucide-star" class="size-4" />
                    <span>Key Moments</span>
                  </div>
                </template>
              </UCheckbox>
            </div>

            <!-- Active Filters -->
            <div v-if="searchQuery || selectedSpeaker || showOnlyKeyMoments" class="flex items-center gap-2">
              <span class="text-xs text-muted">Active filters:</span>
              <div class="flex flex-wrap gap-1.5">
                <UBadge
                  v-if="searchQuery"
                  :label="`Search: ${searchQuery}`"
                  :color="searchMode === 'keyword' ? 'warning' : 'primary'"
                  variant="soft"
                  size="sm"
                >
                  <template #leading>
                    <UIcon :name="searchMode === 'smart' ? 'i-lucide-sparkles' : 'i-lucide-search'" class="size-3" />
                  </template>
                  <template #trailing>
                    <UIcon name="i-lucide-x" class="size-3 cursor-pointer" @click="searchQuery = ''" />
                  </template>
                </UBadge>
                <UBadge
                  v-if="selectedSpeaker"
                  :label="`Speaker: ${getSpeaker(selectedSpeaker)?.name}`"
                  color="info"
                  variant="soft"
                  size="sm"
                >
                  <template #trailing>
                    <UIcon name="i-lucide-x" class="size-3 cursor-pointer" @click="selectedSpeaker = null" />
                  </template>
                </UBadge>
                <UBadge
                  v-if="showOnlyKeyMoments"
                  label="Key Moments"
                  color="warning"
                  variant="soft"
                  size="sm"
                >
                  <template #trailing>
                    <UIcon name="i-lucide-x" class="size-3 cursor-pointer" @click="showOnlyKeyMoments = false" />
                  </template>
                </UBadge>
              </div>
              <UButton
                label="Clear All"
                color="neutral"
                variant="ghost"
                size="xs"
                @click="searchQuery = ''; selectedSpeaker = null; showOnlyKeyMoments = false; searchMode = 'smart'"
              />
            </div>

            <!-- Results count -->
            <div v-if="filteredSegments.length !== transcript.segments.length" class="text-xs text-muted">
              Showing {{ filteredSegments.length }} of {{ transcript.segments.length }} segments
            </div>
          </div>

          <!-- Transcript Segments Container -->
          <div>
            <div
              ref="scrollContainerRef"
              class="overflow-y-auto max-h-[60vh]"
              data-transcript-container
            >
            <!-- Virtual list -->
            <div
              v-if="filteredSegments.length > 0"
              :style="{
                height: `${totalSize}px`,
                width: '100%',
                position: 'relative',
              }"
            >
              <div
                v-for="virtualRow in virtualRows"
                :key="virtualRow.key"
                :data-index="virtualRow.index"
                :style="{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  transform: `translateY(${virtualRow.start}px)`,
                  width: '100%',
                  height: '120px',
                  marginBottom: '8px',
                }"
                :class="[
                  'p-4 rounded-lg cursor-pointer overflow-hidden transition-colors duration-200',
                  {
                    'bg-primary/10 border-l-4 border-primary shadow-sm': filteredSegments[virtualRow.index].id === activeSegmentId,
                    'hover:bg-muted/30': filteredSegments[virtualRow.index].id !== activeSegmentId,
                    'animate-pulse bg-warning/20': filteredSegments[virtualRow.index].id === flashSegmentId
                  }
                ]"
                @click="currentTime = filteredSegments[virtualRow.index].start"
              >
                <!-- Header -->
                <div class="flex items-start justify-between gap-3 mb-3">
                  <div class="flex items-center gap-2 flex-wrap">
                    <UButton
                      :label="formatTime(filteredSegments[virtualRow.index].start)"
                      icon="i-lucide-clock"
                      color="neutral"
                      variant="soft"
                      size="xs"
                      @click.stop="seekToSegment(filteredSegments[virtualRow.index])"
                    />

                    <div
                      v-if="getSpeaker(filteredSegments[virtualRow.index].speaker)"
                      class="px-3 py-1 rounded-full text-sm font-medium"
                      :style="{
                        backgroundColor: getSpeaker(filteredSegments[virtualRow.index].speaker)!.color + '20',
                        color: getSpeaker(filteredSegments[virtualRow.index].speaker)!.color
                      }"
                    >
                      {{ getSpeaker(filteredSegments[virtualRow.index].speaker)!.name }}
                    </div>
                    <UBadge v-else label="Unknown Speaker" color="neutral" size="xs" variant="soft" />

                    <UBadge v-if="filteredSegments[virtualRow.index].isKeyMoment" label="Key Moment" icon="i-lucide-star" color="warning" size="xs" />

                    <UTooltip v-if="filteredSegments[virtualRow.index].confidence" :text="`Confidence: ${Math.round(filteredSegments[virtualRow.index].confidence * 100)}%`">
                      <UBadge
                        :label="`${Math.round(filteredSegments[virtualRow.index].confidence * 100)}%`"
                        :color="filteredSegments[virtualRow.index].confidence > 0.9 ? 'success' : filteredSegments[virtualRow.index].confidence > 0.7 ? 'warning' : 'neutral'"
                        size="xs"
                        variant="subtle"
                      />
                    </UTooltip>
                  </div>

                  <!-- Actions -->
                  <div class="flex items-center gap-1">
                    <UTooltip :text="filteredSegments[virtualRow.index].isKeyMoment ? 'Remove Key Moment' : 'Mark as Key Moment'">
                      <UButton
                        icon="i-lucide-star"
                        :color="filteredSegments[virtualRow.index].isKeyMoment ? 'warning' : 'neutral'"
                        variant="ghost"
                        size="xs"
                        @click.stop="toggleKeyMoment(filteredSegments[virtualRow.index].id)"
                      />
                    </UTooltip>

                    <UTooltip text="Copy Segment">
                      <UButton
                        icon="i-lucide-copy"
                        color="neutral"
                        variant="ghost"
                        size="xs"
                        @click.stop="copySegmentToClipboard(filteredSegments[virtualRow.index])"
                      />
                    </UTooltip>

                    <UTooltip text="Edit Text">
                      <UButton
                        icon="i-lucide-edit"
                        color="neutral"
                        variant="ghost"
                        size="xs"
                        @click.stop="startEdit(filteredSegments[virtualRow.index])"
                      />
                    </UTooltip>
                  </div>
                </div>

                <!-- Text Content -->
                <div class="mt-2">
                  <div v-if="editingSegmentId === filteredSegments[virtualRow.index].id" class="space-y-2" @click.stop>
                    <UTextarea
                      v-model="editText"
                      autofocus
                      rows="3"
                      @keydown.meta.enter="saveEdit(filteredSegments[virtualRow.index].id)"
                      @keydown.esc="cancelEdit"
                    />
                    <div class="flex gap-2">
                      <UButton
                        label="Save"
                        icon="i-lucide-check"
                        color="primary"
                        size="xs"
                        @click="saveEdit(filteredSegments[virtualRow.index].id)"
                      />
                      <UButton
                        label="Cancel"
                        icon="i-lucide-x"
                        color="neutral"
                        variant="ghost"
                        size="xs"
                        @click="cancelEdit"
                      />
                    </div>
                  </div>
                  <p
                    v-else
                    class="text-default leading-relaxed text-base line-clamp-3"
                  >
                    {{ filteredSegments[virtualRow.index].text }}
                  </p>
                </div>

                <!-- Tags -->
                <div v-if="filteredSegments[virtualRow.index].tags && filteredSegments[virtualRow.index].tags.length > 0" class="flex flex-wrap gap-1 mt-3">
                  <UBadge
                    v-for="tag in filteredSegments[virtualRow.index].tags"
                    :key="tag"
                    :label="tag"
                    color="neutral"
                    size="xs"
                    variant="outline"
                  />
                </div>
              </div>
            </div>

            <!-- Empty State -->
            <div v-else class="text-center py-20 px-6">
              <UIcon name="i-lucide-search-x" class="size-16 text-muted mx-auto mb-4 opacity-30" />
              <h3 class="text-xl font-semibold mb-2">No segments found</h3>
              <p class="text-muted mb-4">Try adjusting your filters or search query</p>
              <UButton
                label="Clear Filters"
                icon="i-lucide-x"
                color="neutral"
                @click="searchQuery = ''; selectedSpeaker = null; showOnlyKeyMoments = false; searchMode = 'smart'"
              />
            </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </UDashboardPanel>

  <!-- Right Metadata Sidebar -->
  <UDashboardSidebar
    v-if="transcript"
    id="transcript-metadata"
    v-model:open="metadataSidebarOpen"
    v-model:collapsed="metadataSidebarCollapsed"
    side="right"
    resizable
    collapsible
    :min-size="20"
    :max-size="40"
    :default-size="25"
  >
    <template #header>
      <div class="flex items-center justify-center gap-3">
        <UTooltip :text="metadataSidebarCollapsed ? 'Show metadata' : 'Hide metadata'">
          <UButton
            :icon="metadataSidebarCollapsed ? 'i-lucide-info' : 'i-lucide-x'"
            color="neutral"
            variant="ghost"
            size="md"
            @click="metadataSidebarCollapsed = !metadataSidebarCollapsed"
          />
        </UTooltip>
        <h2 v-if="!metadataSidebarCollapsed" class="text-lg font-semibold">Metadata</h2>
      </div>
    </template>

    <template #default>
      <div v-if="!metadataSidebarCollapsed" class="space-y-6">
          <!-- Transcript Info -->
          <UCard>
            <template #header>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-info" class="size-5 text-primary" />
                <h3 class="font-semibold text-lg">Information</h3>
              </div>
            </template>

            <div class="space-y-3">
              <div>
                <p class="text-xs text-muted mb-1">Title</p>
                <p class="font-medium">{{ transcript.title }}</p>
              </div>

              <div v-if="transcript.caseName">
                <p class="text-xs text-muted mb-1">Case</p>
                <NuxtLink
                  v-if="transcript.caseId"
                  :to="`/cases/${transcript.caseId}`"
                  class="font-medium text-primary hover:underline"
                >
                  {{ transcript.caseName }}
                </NuxtLink>
                <p v-else class="font-medium">{{ transcript.caseName }}</p>
              </div>

              <div>
                <p class="text-xs text-muted mb-1">Created</p>
                <p class="font-medium">{{ formatDate(transcript.createdAt) }}</p>
              </div>

              <div>
                <p class="text-xs text-muted mb-1">Status</p>
                <UBadge
                  :label="transcript.status"
                  :color="transcript.status === 'completed' ? 'success' : transcript.status === 'processing' ? 'warning' : 'error'"
                  variant="soft"
                  class="capitalize"
                />
              </div>
            </div>
          </UCard>

          <!-- Statistics -->
          <UCard v-if="transcriptStats">
            <template #header>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-bar-chart" class="size-5 text-primary" />
                <h3 class="font-semibold text-lg">Statistics</h3>
              </div>
            </template>

            <div class="grid grid-cols-2 gap-3">
              <div class="p-3 bg-muted/10 rounded-lg space-y-1">
                <p class="text-2xl font-bold text-primary">{{ formatDuration(transcriptStats.duration) }}</p>
                <p class="text-xs text-muted">Duration</p>
              </div>

              <div class="p-3 bg-muted/10 rounded-lg space-y-1">
                <p class="text-2xl font-bold text-primary">{{ transcriptStats.totalWords }}</p>
                <p class="text-xs text-muted">Words</p>
              </div>

              <div class="p-3 bg-muted/10 rounded-lg space-y-1">
                <p class="text-2xl font-bold text-primary">{{ transcriptStats.totalSpeakers }}</p>
                <p class="text-xs text-muted">Speakers</p>
              </div>

              <div class="p-3 bg-muted/10 rounded-lg space-y-1">
                <p class="text-2xl font-bold text-primary">{{ transcriptStats.totalSegments }}</p>
                <p class="text-xs text-muted">Segments</p>
              </div>

              <div v-if="transcriptStats.keyMoments > 0" class="col-span-2 p-3 bg-muted/10 rounded-lg space-y-1">
                <p class="text-2xl font-bold text-warning">{{ transcriptStats.keyMoments }}</p>
                <p class="text-xs text-muted">Key Moments</p>
              </div>
            </div>
          </UCard>

          <!-- Speakers -->
          <UCard>
            <template #header>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-users" class="size-5 text-primary" />
                <h3 class="font-semibold text-lg">Speakers</h3>
              </div>
            </template>

            <div class="space-y-3">
              <div
                v-for="speakerStat in transcriptStats?.speakerStats"
                :key="speakerStat.speaker.id"
                class="p-3 bg-muted/10 rounded-lg"
              >
                <!-- Editing Mode -->
                <div v-if="editingSpeakerId === speakerStat.speaker.id" class="space-y-2" @click.stop>
                  <UInput
                    v-model="editSpeakerName"
                    placeholder="Speaker name"
                    size="sm"
                    autofocus
                  />
                  <UInput
                    v-model="editSpeakerRole"
                    placeholder="Role (optional)"
                    size="sm"
                    @keydown.enter="saveSpeakerEdit"
                  />
                  <div class="flex gap-2">
                    <UButton
                      label="Save"
                      icon="i-lucide-check"
                      color="primary"
                      size="xs"
                      @click="saveSpeakerEdit"
                    />
                    <UButton
                      label="Cancel"
                      icon="i-lucide-x"
                      color="neutral"
                      variant="ghost"
                      size="xs"
                      @click="cancelSpeakerEdit"
                    />
                  </div>
                </div>

                <!-- Display Mode -->
                <div v-else>
                  <div class="flex items-start justify-between mb-2">
                    <div class="flex-1 min-w-0">
                      <div
                        class="px-2 py-1 rounded text-xs font-medium inline-block mb-1"
                        :style="{
                          backgroundColor: speakerStat.speaker.color + '20',
                          color: speakerStat.speaker.color
                        }"
                      >
                        {{ speakerStat.speaker.name }}
                      </div>
                      <p v-if="speakerStat.speaker.role" class="text-xs text-muted">
                        {{ speakerStat.speaker.role }}
                      </p>
                    </div>
                    <div class="flex items-center gap-1">
                      <UTooltip text="Edit Speaker">
                        <UButton
                          icon="i-lucide-edit"
                          color="neutral"
                          variant="ghost"
                          size="xs"
                          @click.stop="startEditSpeaker(speakerStat.speaker)"
                        />
                      </UTooltip>
                      <UTooltip text="Filter by Speaker">
                        <UButton
                          icon="i-lucide-filter"
                          color="neutral"
                          variant="ghost"
                          size="xs"
                          @click="selectedSpeaker = speakerStat.speaker.id"
                        />
                      </UTooltip>
                    </div>
                  </div>

                  <div class="space-y-1 text-xs">
                    <div class="flex justify-between">
                      <span class="text-muted">Speaking time</span>
                      <span class="font-medium">{{ formatDuration(speakerStat.speakingTime) }}</span>
                    </div>
                    <div class="flex justify-between">
                      <span class="text-muted">Segments</span>
                      <span class="font-medium">{{ speakerStat.segmentCount }}</span>
                    </div>
                    <div class="flex justify-between">
                      <span class="text-muted">Words</span>
                      <span class="font-medium">{{ speakerStat.wordCount }}</span>
                    </div>

                    <div class="mt-2">
                      <div class="h-1.5 bg-muted/30 rounded-full overflow-hidden">
                        <div
                          class="h-full rounded-full"
                          :style="{
                            width: `${speakerStat.percentage}%`,
                            backgroundColor: speakerStat.speaker.color
                          }"
                        />
                      </div>
                      <p class="text-xs text-muted mt-1">{{ speakerStat.percentage.toFixed(1) }}% of total</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </UCard>

          <!-- Key Moments -->
          <UCard v-if="keyMoments.length > 0">
            <template #header>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-star" class="size-5 text-warning" />
                <h3 class="font-semibold text-lg">Key Moments ({{ keyMoments.length }})</h3>
              </div>
            </template>

            <div class="space-y-2">
              <div
                v-for="moment in keyMoments"
                :key="moment.id"
                class="p-3 bg-yellow-500/5 border border-yellow-500/20 rounded-lg cursor-pointer hover:bg-yellow-500/10 transition-colors"
                @click="seekToSegment(moment)"
              >
                <div class="flex items-center gap-2 mb-2">
                  <UBadge
                    :label="formatTime(moment.start)"
                    color="warning"
                    size="xs"
                    variant="soft"
                  />
                  <div
                    v-if="getSpeaker(moment.speaker)"
                    class="px-2 py-0.5 rounded text-xs font-medium"
                    :style="{
                      backgroundColor: getSpeaker(moment.speaker)!.color + '20',
                      color: getSpeaker(moment.speaker)!.color
                    }"
                  >
                    {{ getSpeaker(moment.speaker)!.name }}
                  </div>
                </div>
                <p class="text-sm text-default line-clamp-2">{{ moment.text }}</p>
              </div>
            </div>
          </UCard>

          <!-- Metadata -->
          <UCard v-if="transcript.metadata">
            <template #header>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-file-audio" class="size-5 text-primary" />
                <h3 class="font-semibold text-lg">Audio Details</h3>
              </div>
            </template>

            <div class="space-y-2 text-sm">
              <div v-if="transcript.metadata.format" class="flex justify-between">
                <span class="text-muted">Format</span>
                <span class="font-medium">{{ transcript.metadata.format }}</span>
              </div>
              <div v-if="transcript.metadata.fileSize" class="flex justify-between">
                <span class="text-muted">File Size</span>
                <span class="font-medium">{{ (transcript.metadata.fileSize / 1024 / 1024).toFixed(2) }} MB</span>
              </div>
              <div v-if="transcript.metadata.sampleRate" class="flex justify-between">
                <span class="text-muted">Sample Rate</span>
                <span class="font-medium">{{ transcript.metadata.sampleRate }} Hz</span>
              </div>
              <div v-if="transcript.metadata.bitRate" class="flex justify-between">
                <span class="text-muted">Bit Rate</span>
                <span class="font-medium">{{ transcript.metadata.bitRate }} kbps</span>
              </div>
            </div>
          </UCard>

          <!-- Keyboard Shortcuts -->
          <UCard>
            <template #header>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-keyboard" class="size-5 text-primary" />
                <h3 class="font-semibold text-lg">Keyboard Shortcuts</h3>
              </div>
            </template>

            <div class="space-y-2 text-sm">
              <div class="flex items-center justify-between">
                <span class="text-muted">Play/Pause</span>
                <UKbd value="Space" />
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted">Search</span>
                <UKbd value="⌘F" />
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted">Follow/Unfollow</span>
                <UKbd value="A" />
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted">Clear Filters</span>
                <UKbd value="Esc" />
              </div>
            </div>
          </UCard>
      </div>
    </template>
  </UDashboardSidebar>
</template>

<style scoped>
[data-transcript-container] {
  -webkit-overflow-scrolling: touch;
}
</style>
