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

// Speaker colors for UI
const SPEAKER_COLORS = [
  '#3B82F6',
  '#8B5CF6',
  '#10B981',
  '#F59E0B',
  '#EF4444',
  '#EC4899',
  '#6366F1',
  '#14B8A6'
]

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
// Right sidebar state - which panel is active (null = collapsed, 'info' = metadata, 'summary' = summary)
const activeRightPanel = ref<'info' | 'summary' | null>(null)
const summaryData = ref<{
  summary: string
  keyMoments: Array<{ timestamp?: string, description: string, importance: 'high' | 'medium' | 'low', speakers?: string[] }>
  actionItems: string[]
  topics: string[]
  entities?: {
    people?: string[]
    organizations?: string[]
    locations?: string[]
    dates?: string[]
  }
} | null>(null)
const isGeneratingSummary = ref(false)

// Parse timestamp string (MM:SS or M:SS) to seconds
function parseTimestamp(timestamp: string): number | null {
  if (!timestamp) return null
  const match = timestamp.match(/^(\d+):(\d{2})$/)
  if (!match) return null
  const [, mins, secs] = match
  return parseInt(mins) * 60 + parseInt(secs)
}

// Find segment at a given timestamp
function findSegmentAtTime(timeSeconds: number): TranscriptSegment | null {
  if (!transcript.value) return null
  return transcript.value.segments.find(seg =>
    timeSeconds >= seg.start && timeSeconds <= seg.end
  ) || null
}

// Apply a single key moment from summary to transcript
async function applyKeyMoment(moment: { timestamp?: string, description: string }) {
  if (!transcript.value || !moment.timestamp) {
    toast.add({
      title: 'Cannot apply key moment',
      description: 'No valid timestamp available',
      color: 'warning'
    })
    return
  }

  const timeSeconds = parseTimestamp(moment.timestamp)
  if (timeSeconds === null) {
    toast.add({
      title: 'Cannot apply key moment',
      description: `Invalid timestamp format: ${moment.timestamp}`,
      color: 'warning'
    })
    return
  }

  const segment = findSegmentAtTime(timeSeconds)
  if (!segment) {
    toast.add({
      title: 'Cannot apply key moment',
      description: `No segment found at ${moment.timestamp}`,
      color: 'warning'
    })
    return
  }

  if (segment.isKeyMoment) {
    toast.add({
      title: 'Already marked',
      description: 'This segment is already a key moment',
      color: 'info'
    })
    return
  }

  await toggleKeyMoment(segment.id)
}

// Apply all key moments from summary to transcript
async function applyAllKeyMoments() {
  if (!transcript.value || !summaryData.value?.keyMoments?.length) return

  let applied = 0
  let skipped = 0

  for (const moment of summaryData.value.keyMoments) {
    if (!moment.timestamp) {
      skipped++
      continue
    }

    const timeSeconds = parseTimestamp(moment.timestamp)
    if (timeSeconds === null) {
      skipped++
      continue
    }

    const segment = findSegmentAtTime(timeSeconds)
    if (!segment) {
      skipped++
      continue
    }

    if (segment.isKeyMoment) {
      skipped++
      continue
    }

    // Mark as key moment
    segment.isKeyMoment = true
    applied++
  }

  if (applied > 0) {
    // Save all changes to Firestore
    await updateTranscription(transcriptId.value, {
      segments: transcript.value.segments
    })

    toast.add({
      title: 'Key moments applied',
      description: `${applied} segment${applied > 1 ? 's' : ''} marked as key moments${skipped > 0 ? ` (${skipped} skipped)` : ''}`,
      color: 'success'
    })
  } else {
    toast.add({
      title: 'No new key moments',
      description: skipped > 0 ? `${skipped} could not be applied (already marked or no matching segment)` : 'No key moments to apply',
      color: 'info'
    })
  }
}

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

// Generate transcript summary
async function generateSummary() {
  if (!transcript.value) return

  isGeneratingSummary.value = true

  try {
    // Build timestamped transcript text from segments
    const fullText = transcript.value.segments
      .map((seg) => {
        const speaker = getSpeaker(seg.speaker)
        const speakerName = speaker?.name || 'Unknown'
        const timestamp = formatTime(seg.start)
        return `[${timestamp}] ${speakerName}: ${seg.text}`
      })
      .join('\n')

    const result = await summarizeTranscript({
      transcript: fullText,
      outputType: 'detailed'
    })

    summaryData.value = result

    // Save to Firestore for persistence
    await updateTranscription(transcriptId.value, {
      summarization: result
    })

    toast.add({
      title: 'Summary generated',
      description: 'AI summary has been created and saved',
      color: 'success'
    })
  } catch (err: any) {
    console.error('Error generating summary:', err)
    toast.add({
      title: 'Failed to generate summary',
      description: err.message || 'An error occurred while generating the summary',
      color: 'error'
    })
  } finally {
    isGeneratingSummary.value = false
  }
}

// Computed property for active segment ID - simple linear search
const activeSegmentId = computed(() => {
  if (!transcript.value?.segments?.length) return null

  const time = currentTime.value

  // Simple: find segment where time is between start and end
  for (const segment of transcript.value.segments) {
    if (time >= segment.start && time <= segment.end) {
      console.log('[activeSegmentId] time:', time.toFixed(2), '-> segment:', segment.id, `(${segment.start.toFixed(2)}-${segment.end.toFixed(2)})`)
      return segment.id
    }
  }

  // Debug: log when no segment found
  if (transcript.value.segments.length > 0) {
    const first3 = transcript.value.segments.slice(0, 3)
    console.log('[activeSegmentId] time:', time.toFixed(2), '-> NO MATCH. First 3 segments:', first3.map(s => `${s.id}(${s.start.toFixed(2)}-${s.end.toFixed(2)})`).join(', '))
  }

  return null
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
        s.text.toLowerCase().includes(query)
        || (getSpeaker(s.speaker)?.name?.toLowerCase() || '').includes(query)
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
    overscan: 8
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

  const speakerStats = transcript.value.speakers.map((speaker) => {
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

  transcript.value.segments.forEach((segment) => {
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

    // Transform speakers to add name and color for UI
    const rawSpeakers = doc.speakers || []
    const transformedSpeakers = rawSpeakers.map((s: any, index: number) => ({
      ...s,
      name: s.name || s.inferredName || s.id || `Speaker ${index + 1}`,
      color: s.color || SPEAKER_COLORS[index % SPEAKER_COLORS.length]
    }))

    // Transform segments to ensure they have proper IDs
    const transformedSegments = (doc.segments || []).map((s: any, index: number) => ({
      ...s,
      id: s.id || `seg-${index}`,
      isKeyMoment: s.isKeyMoment || false
    }))

    // Adapt Firestore document to transcript format
    transcript.value = {
      id: doc.id,
      title: doc.filename,
      audioUrl: doc.downloadUrl,
      duration: doc.duration || 0,
      segments: transformedSegments,
      speakers: transformedSpeakers,
      createdAt: doc.createdAt?.toDate?.()?.toISOString() || new Date().toISOString(),
      caseId: doc.caseId,
      status: doc.status,
      waveformPeaks: doc.waveformPeaks || null
    } as any

    // Load stored summarization if available
    if (doc.summarization) {
      summaryData.value = doc.summarization
    }

    // Debug: log all segments with their time ranges
    console.log('[loadTranscript] Loaded', transformedSegments.length, 'segments:')
    transformedSegments.slice(0, 10).forEach((s: any, i: number) => {
      console.log(`  [${i}] ${s.id}: ${s.start.toFixed(2)} - ${s.end.toFixed(2)} (duration: ${(s.end - s.start).toFixed(2)}s)`)
    })
    if (transformedSegments.length > 10) {
      console.log(`  ... and ${transformedSegments.length - 10} more segments`)
    }
  } catch (err: any) {
    error.value = err.message || 'Failed to load transcript'
    console.error('Error loading transcript:', err)
  } finally {
    isLoading.value = false
  }
}

// Keyboard shortcuts
defineShortcuts({
  space: {
    usingInput: false,
    handler: () => {
      isPlaying.value = !isPlaying.value
    }
  },
  meta_f: {
    handler: () => {
      const searchInput = document.querySelector('input[placeholder*="Search"]') as HTMLInputElement
      searchInput?.focus()
    }
  },
  escape: {
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
  a: {
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
  <UDashboardPanel id="transcript-main">
    <template #header>
      <div class="h-16 px-4 sm:px-6 flex items-center justify-between gap-4 border-b border-default">
        <div class="flex items-center gap-4 min-w-0">
          <UButton
            icon="i-lucide-arrow-left"
            color="neutral"
            variant="ghost"
            @click="router.push('/transcripts')"
          />
          <h1 class="text-xl font-semibold truncate">
            {{ transcript?.title || 'Transcript' }}
          </h1>
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
                    }
                    else {
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
        </div>
      </div>
    </template>

    <template #body>
      <!-- Loading State -->
      <div v-if="isLoading" class="flex items-center justify-center min-h-full p-6">
        <div class="text-center space-y-4">
          <UIcon name="i-lucide-loader-circle" class="size-12 text-primary animate-spin mx-auto" />
          <div>
            <h3 class="text-lg font-semibold">
              Loading transcript...
            </h3>
            <p class="text-sm text-muted">
              Please wait while we fetch your transcript
            </p>
          </div>
        </div>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="flex items-center justify-center min-h-full p-6">
        <UCard class="max-w-md">
          <div class="text-center space-y-4">
            <UIcon name="i-lucide-alert-circle" class="size-16 text-error mx-auto" />
            <div>
              <h3 class="text-xl font-bold text-highlighted mb-2">
                Error Loading Transcript
              </h3>
              <p class="text-muted">
                {{ error }}
              </p>
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
          :peaks="transcript.waveformPeaks"
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
                position: 'relative'
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
                  marginBottom: '8px'
                }"
                :class="[
                  'p-4 rounded-lg cursor-pointer overflow-hidden transition-colors duration-200',
                  {
                    'bg-primary/10 border-l-4 border-primary shadow-sm': filteredSegments[virtualRow.index].id === activeSegmentId,
                    'hover:bg-muted/30': filteredSegments[virtualRow.index].id !== activeSegmentId,
                    'animate-pulse bg-warning/20': filteredSegments[virtualRow.index].id === flashSegmentId
                  }
                ]"
                @click="() => { console.log('[SegmentClick] clicked segment', filteredSegments[virtualRow.index].id, 'start:', filteredSegments[virtualRow.index].start); currentTime = filteredSegments[virtualRow.index].start }"
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
                    <UBadge
                      v-else
                      label="Unknown Speaker"
                      color="neutral"
                      size="xs"
                      variant="soft"
                    />

                    <UBadge
                      v-if="filteredSegments[virtualRow.index].isKeyMoment"
                      label="Key Moment"
                      icon="i-lucide-star"
                      color="warning"
                      size="xs"
                    />

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
              <h3 class="text-xl font-semibold mb-2">
                No segments found
              </h3>
              <p class="text-muted mb-4">
                Try adjusting your filters or search query
              </p>
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
    </template>
  </UDashboardPanel>

  <!-- Right Side Panels with Vertical Icon Bar -->
  <div v-if="transcript" class="flex h-full border-l border-default">
    <!-- Vertical Icon Bar -->
    <div class="flex flex-col items-center py-4 px-2 gap-2 border-r border-default bg-elevated/50">
      <UTooltip text="Info & Speakers" :popper="{ placement: 'left' }">
        <UButton
          icon="i-lucide-info"
          :color="activeRightPanel === 'info' ? 'primary' : 'neutral'"
          :variant="activeRightPanel === 'info' ? 'soft' : 'ghost'"
          size="sm"
          @click="activeRightPanel = activeRightPanel === 'info' ? null : 'info'"
        />
      </UTooltip>
      <UTooltip text="AI Summary" :popper="{ placement: 'left' }">
        <UButton
          icon="i-lucide-sparkles"
          :color="activeRightPanel === 'summary' ? 'primary' : 'neutral'"
          :variant="activeRightPanel === 'summary' ? 'soft' : 'ghost'"
          size="sm"
          @click="activeRightPanel = activeRightPanel === 'summary' ? null : 'summary'"
        />
      </UTooltip>
    </div>

    <!-- Content Panel (slides in from right) -->
    <Transition name="slide-panel">
      <div v-if="activeRightPanel" class="w-80 bg-elevated/25 overflow-y-auto">
        <!-- Info Panel Content -->
        <div v-if="activeRightPanel === 'info'" class="p-4 space-y-6">
          <!-- Header -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <UIcon name="i-lucide-info" class="size-5 text-primary" />
              <h3 class="font-semibold">
                Info
              </h3>
            </div>
            <UButton
              icon="i-lucide-x"
              color="neutral"
              variant="ghost"
              size="xs"
              @click="activeRightPanel = null"
            />
          </div>

          <!-- Overview -->
          <div class="space-y-4">
            <h4 class="text-sm font-semibold text-muted uppercase tracking-wide">
              Overview
            </h4>
            <div class="space-y-3">
              <div class="flex justify-between text-sm">
                <span class="text-muted">Duration</span>
                <span class="font-medium">{{ formatDuration(transcriptStats?.duration || 0) }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-muted">Segments</span>
                <span class="font-medium">{{ transcriptStats?.totalSegments || 0 }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-muted">Words</span>
                <span class="font-medium">{{ transcriptStats?.totalWords?.toLocaleString() || 0 }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-muted">Key Moments</span>
                <span class="font-medium">{{ transcriptStats?.keyMoments || 0 }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-muted">Created</span>
                <span class="font-medium text-xs">{{ formatDate(transcript.createdAt) }}</span>
              </div>
            </div>
          </div>

          <USeparator />

          <!-- Speakers -->
          <div class="space-y-4">
            <h4 class="text-sm font-semibold text-muted uppercase tracking-wide flex items-center gap-2">
              <UIcon name="i-lucide-users" class="size-4" />
              Speakers ({{ transcript.speakers.length }})
            </h4>
            <div class="space-y-3">
              <div
                v-for="stat in transcriptStats?.speakerStats"
                :key="stat.speaker.id"
                class="p-3 rounded-lg bg-muted/20"
              >
                <div v-if="editingSpeakerId === stat.speaker.id" class="space-y-2">
                  <UInput
                    v-model="editSpeakerName"
                    placeholder="Speaker name"
                    size="sm"
                    autofocus
                  />
                  <UInput v-model="editSpeakerRole" placeholder="Role (optional)" size="sm" />
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
                <template v-else>
                  <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                      <div class="w-3 h-3 rounded-full" :style="{ backgroundColor: stat.speaker.color }" />
                      <span class="font-medium text-sm">{{ stat.speaker.name }}</span>
                    </div>
                    <UButton
                      icon="i-lucide-edit"
                      color="neutral"
                      variant="ghost"
                      size="xs"
                      @click="startEditSpeaker(stat.speaker)"
                    />
                  </div>
                  <div v-if="stat.speaker.role" class="text-xs text-muted mb-2">
                    {{ stat.speaker.role }}
                  </div>
                  <div class="space-y-1 text-xs text-muted">
                    <div class="flex justify-between">
                      <span>Speaking time</span>
                      <span>{{ formatDuration(stat.speakingTime) }}</span>
                    </div>
                    <div class="flex justify-between">
                      <span>Segments</span>
                      <span>{{ stat.segmentCount }}</span>
                    </div>
                    <div class="flex justify-between">
                      <span>Words</span>
                      <span>{{ stat.wordCount.toLocaleString() }}</span>
                    </div>
                  </div>
                  <UProgress
                    :value="stat.percentage"
                    size="xs"
                    class="mt-2"
                    :style="{ '--progress-color': stat.speaker.color }"
                  />
                </template>
              </div>
            </div>
          </div>

          <USeparator />

          <!-- Key Moments Quick Access -->
          <div v-if="keyMoments.length > 0" class="space-y-4">
            <h4 class="text-sm font-semibold text-muted uppercase tracking-wide flex items-center gap-2">
              <UIcon name="i-lucide-star" class="size-4" />
              Key Moments ({{ keyMoments.length }})
            </h4>
            <div class="space-y-2 max-h-48 overflow-y-auto">
              <div
                v-for="moment in keyMoments"
                :key="moment.id"
                class="p-2 rounded-lg bg-warning/10 cursor-pointer hover:bg-warning/20 transition-colors"
                @click="seekToSegment(moment)"
              >
                <div class="flex items-center gap-2 mb-1">
                  <UButton
                    :label="formatTime(moment.start)"
                    icon="i-lucide-clock"
                    color="warning"
                    variant="soft"
                    size="xs"
                  />
                  <span v-if="getSpeaker(moment.speaker)" class="text-xs font-medium" :style="{ color: getSpeaker(moment.speaker)!.color }">
                    {{ getSpeaker(moment.speaker)!.name }}
                  </span>
                </div>
                <p class="text-xs text-default line-clamp-2">
                  {{ moment.text }}
                </p>
              </div>
            </div>
          </div>

          <!-- Keyboard shortcuts -->
          <USeparator />
          <div class="space-y-3">
            <h4 class="text-sm font-semibold text-muted uppercase tracking-wide flex items-center gap-2">
              <UIcon name="i-lucide-keyboard" class="size-4" />
              Shortcuts
            </h4>
            <div class="space-y-2 text-xs">
              <div class="flex justify-between">
                <span class="text-muted">Play/Pause</span><UKbd value="space" />
              </div>
              <div class="flex justify-between">
                <span class="text-muted">Toggle Auto-scroll</span><UKbd value="A" />
              </div>
              <div class="flex justify-between">
                <span class="text-muted">Search</span><div class="flex gap-1">
                  <UKbd value="meta" /><UKbd value="F" />
                </div>
              </div>
              <div class="flex justify-between">
                <span class="text-muted">Clear filters</span><UKbd value="esc" />
              </div>
            </div>
          </div>
        </div>

        <!-- Summary Panel Content -->
        <div v-else-if="activeRightPanel === 'summary'" class="p-4 space-y-6">
          <!-- Header -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <UIcon name="i-lucide-sparkles" class="size-5 text-primary" />
              <h3 class="font-semibold">
                AI Summary
              </h3>
            </div>
            <UButton
              icon="i-lucide-x"
              color="neutral"
              variant="ghost"
              size="xs"
              @click="activeRightPanel = null"
            />
          </div>

          <!-- No summary yet -->
          <div v-if="!summaryData && !isGeneratingSummary" class="text-center py-8">
            <UIcon name="i-lucide-file-text" class="size-12 text-muted mx-auto mb-3 opacity-30" />
            <h4 class="text-base font-semibold mb-2">
              No Summary Yet
            </h4>
            <p class="text-sm text-muted mb-4">
              Generate an AI-powered summary including key moments, action items, and topics.
            </p>
            <UButton
              icon="i-lucide-sparkles"
              label="Generate Summary"
              color="primary"
              size="sm"
              @click="generateSummary"
            />
          </div>

          <!-- Loading state -->
          <div v-else-if="isGeneratingSummary" class="text-center py-8">
            <UIcon name="i-lucide-loader-circle" class="size-10 text-primary animate-spin mx-auto mb-3" />
            <h4 class="text-base font-semibold mb-2">
              Generating Summary...
            </h4>
            <p class="text-sm text-muted">
              AI is analyzing your transcript.
            </p>
          </div>

          <!-- Summary content -->
          <template v-else-if="summaryData">
            <!-- Main Summary -->
            <div class="space-y-2">
              <h4 class="text-sm font-semibold text-muted uppercase tracking-wide">
                Summary
              </h4>
              <p class="text-sm text-default leading-relaxed whitespace-pre-wrap">
                {{ summaryData.summary }}
              </p>
            </div>

            <USeparator />

            <!-- Key Moments -->
            <div v-if="summaryData.keyMoments?.length" class="space-y-3">
              <div class="flex items-center justify-between">
                <h4 class="text-sm font-semibold text-muted uppercase tracking-wide flex items-center gap-2">
                  <UIcon name="i-lucide-star" class="size-4 text-warning" />
                  Key Moments ({{ summaryData.keyMoments.length }})
                </h4>
                <UButton
                  icon="i-lucide-check-check"
                  label="Apply All"
                  color="warning"
                  variant="soft"
                  size="xs"
                  @click="applyAllKeyMoments"
                />
              </div>
              <div class="space-y-2 max-h-64 overflow-y-auto">
                <div
                  v-for="(moment, idx) in summaryData.keyMoments"
                  :key="idx"
                  class="p-2 rounded-lg text-xs"
                  :class="{
                    'bg-red-500/10 border border-red-500/20': moment.importance === 'high',
                    'bg-yellow-500/10 border border-yellow-500/20': moment.importance === 'medium',
                    'bg-muted/10 border border-default': moment.importance === 'low'
                  }"
                >
                  <div class="flex items-center justify-between gap-2 mb-1">
                    <div class="flex items-center gap-1">
                      <UBadge
                        :label="moment.importance"
                        :color="moment.importance === 'high' ? 'error' : moment.importance === 'medium' ? 'warning' : 'neutral'"
                        size="xs"
                        variant="soft"
                        class="capitalize"
                      />
                      <UButton
                        v-if="moment.timestamp"
                        :label="moment.timestamp"
                        icon="i-lucide-clock"
                        color="neutral"
                        variant="ghost"
                        size="xs"
                        @click="() => { const time = parseTimestamp(moment.timestamp!); if (time !== null) currentTime = time }"
                      />
                    </div>
                    <UButton
                      icon="i-lucide-star"
                      color="warning"
                      variant="ghost"
                      size="xs"
                      @click="applyKeyMoment(moment)"
                    />
                  </div>
                  <p class="text-default">
                    {{ moment.description }}
                  </p>
                </div>
              </div>
            </div>

            <USeparator v-if="summaryData.actionItems?.length" />

            <!-- Action Items -->
            <div v-if="summaryData.actionItems?.length" class="space-y-2">
              <h4 class="text-sm font-semibold text-muted uppercase tracking-wide flex items-center gap-2">
                <UIcon name="i-lucide-check-square" class="size-4 text-success" />
                Action Items ({{ summaryData.actionItems.length }})
              </h4>
              <ul class="space-y-1">
                <li v-for="(item, idx) in summaryData.actionItems" :key="idx" class="flex items-start gap-2 text-xs">
                  <UIcon name="i-lucide-circle" class="size-3 text-muted mt-0.5 shrink-0" />
                  <span class="text-default">{{ item }}</span>
                </li>
              </ul>
            </div>

            <USeparator v-if="summaryData.topics?.length" />

            <!-- Topics -->
            <div v-if="summaryData.topics?.length" class="space-y-2">
              <h4 class="text-sm font-semibold text-muted uppercase tracking-wide">
                Topics
              </h4>
              <div class="flex flex-wrap gap-1">
                <UBadge
                  v-for="topic in summaryData.topics"
                  :key="topic"
                  :label="topic"
                  color="primary"
                  variant="soft"
                  size="xs"
                />
              </div>
            </div>

            <USeparator v-if="summaryData.entities && (summaryData.entities.people?.length || summaryData.entities.organizations?.length || summaryData.entities.locations?.length || summaryData.entities.dates?.length)" />

            <!-- Entities -->
            <div v-if="summaryData.entities && (summaryData.entities.people?.length || summaryData.entities.organizations?.length || summaryData.entities.locations?.length || summaryData.entities.dates?.length)" class="space-y-3">
              <h4 class="text-sm font-semibold text-muted uppercase tracking-wide">
                Entities
              </h4>
              <div v-if="summaryData.entities.people?.length" class="space-y-1">
                <p class="text-xs text-muted flex items-center gap-1">
                  <UIcon name="i-lucide-user" class="size-3" /> People
                </p>
                <div class="flex flex-wrap gap-1">
                  <UBadge
                    v-for="person in summaryData.entities.people"
                    :key="person"
                    :label="person"
                    color="neutral"
                    size="xs"
                    variant="outline"
                  />
                </div>
              </div>
              <div v-if="summaryData.entities.organizations?.length" class="space-y-1">
                <p class="text-xs text-muted flex items-center gap-1">
                  <UIcon name="i-lucide-building" class="size-3" /> Organizations
                </p>
                <div class="flex flex-wrap gap-1">
                  <UBadge
                    v-for="org in summaryData.entities.organizations"
                    :key="org"
                    :label="org"
                    color="neutral"
                    size="xs"
                    variant="outline"
                  />
                </div>
              </div>
              <div v-if="summaryData.entities.locations?.length" class="space-y-1">
                <p class="text-xs text-muted flex items-center gap-1">
                  <UIcon name="i-lucide-map-pin" class="size-3" /> Locations
                </p>
                <div class="flex flex-wrap gap-1">
                  <UBadge
                    v-for="loc in summaryData.entities.locations"
                    :key="loc"
                    :label="loc"
                    color="neutral"
                    size="xs"
                    variant="outline"
                  />
                </div>
              </div>
              <div v-if="summaryData.entities.dates?.length" class="space-y-1">
                <p class="text-xs text-muted flex items-center gap-1">
                  <UIcon name="i-lucide-calendar" class="size-3" /> Dates
                </p>
                <div class="flex flex-wrap gap-1">
                  <UBadge
                    v-for="date in summaryData.entities.dates"
                    :key="date"
                    :label="date"
                    color="neutral"
                    size="xs"
                    variant="outline"
                  />
                </div>
              </div>
            </div>

            <!-- Regenerate button -->
            <div class="pt-4 border-t border-default">
              <UButton
                icon="i-lucide-refresh-cw"
                label="Regenerate"
                color="neutral"
                variant="outline"
                size="sm"
                block
                :loading="isGeneratingSummary"
                @click="generateSummary"
              />
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
[data-transcript-container] {
  -webkit-overflow-scrolling: touch;
}

/* Slide panel transition */
.slide-panel-enter-active,
.slide-panel-leave-active {
  transition: all 0.2s ease-out;
}

.slide-panel-enter-from,
.slide-panel-leave-to {
  width: 0;
  opacity: 0;
}

.slide-panel-enter-to,
.slide-panel-leave-from {
  width: 20rem; /* w-80 */
  opacity: 1;
}
</style>
