<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { TranscriptSegment, Speaker, Transcription } from '~/composables/useTranscription'

definePageMeta({
  layout: 'default'
})

const route = useRoute()
const router = useRouter()
const api = useApi()
const toast = useToast()

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
const showMetadataSidebar = ref(true)
const showExportMenu = ref(false)
const isExporting = ref(false)
const editingSegmentId = ref<string | null>(null)
const editText = ref('')
const editingSpeakerId = ref<string | null>(null)
const editSpeakerName = ref('')
const editSpeakerRole = ref('')

// Perform smart search using backend API
async function performSmartSearch() {
  if (!transcript.value || !searchQuery.value.trim()) {
    searchResults.value = new Set()
    return
  }

  isSearching.value = true
  try {
    // Build search request - only include document_ids if we have one
    const searchRequest: any = {
      query: searchQuery.value,
      use_bm25: true,
      use_dense: true,
      fusion_method: 'rrf',
      top_k: 50,
      chunk_types: ['transcript_segment']  // Only search transcript segments
    }

    // Add document filter if available
    // Backend returns document_id in snake_case
    const docId = (transcript.value as any).document_id
    if (docId) {
      searchRequest.document_ids = [docId]
    }

    const response = await api.search.hybrid(searchRequest)

    console.log('[DEBUG] Search response:', {
      totalResults: response.results?.length,
      query: searchQuery.value,
      firstResult: response.results?.[0]
    })

    // Extract segment indices from search results
    // NOTE: Backend stores segment_index in metadata (the array index from segments)
    // Frontend segments have UUID ids, but we need to match by array index
    const segmentIndices = new Set<number>()
    response.results?.forEach((result: any, idx: number) => {
      // The segment_index is stored in metadata.segment_index by the backend
      const segmentIndex = result.metadata?.segment_index

      if (idx < 3) {
        console.log(`[DEBUG] Result ${idx}:`, {
          id: result.id,
          metadata: result.metadata,
          extractedSegmentIndex: segmentIndex
        })
      }

      if (segmentIndex !== undefined && segmentIndex !== null) {
        segmentIndices.add(segmentIndex)
      }
    })

    console.log('[DEBUG] Extracted segment indices:', Array.from(segmentIndices))
    console.log('[DEBUG] Sample transcript segments (first 3):', transcript.value.segments.slice(0, 3).map((s, i) => ({ index: i, id: s.id })))

    searchResults.value = segmentIndices
  } catch (err: any) {
    console.error('Smart search failed:', err)
    // Only log detailed error in development
    if (process.dev) {
      console.error('Error details:', err.response?._data || err.message)
    }
    searchResults.value = new Set()
  } finally {
    isSearching.value = false
  }
}

// Debounced smart search
const debouncedSmartSearch = useDebounceFn(performSmartSearch, 500)

// Watch for search changes
watch([searchQuery, searchMode], () => {
  if (searchMode.value === 'smart' && searchQuery.value.trim()) {
    debouncedSmartSearch()
  } else {
    searchResults.value = new Set()
  }
})

// Computed
const filteredSegments = computed(() => {
  if (!transcript.value) return []

  let segments = transcript.value.segments

  // Filter by search query FIRST (so indices match backend)
  if (searchQuery.value.trim()) {
    if (searchMode.value === 'smart') {
      // Use backend search results
      if (isSearching.value) {
        // Don't filter while searching to avoid flickering
        // Will apply other filters below
      } else {
        // Filter by segment index (array position in original segments array)
        segments = segments.filter((s, index) => searchResults.value.has(index))
      }
    } else {
      // Keyword mode - local filtering
      const query = searchQuery.value.toLowerCase()
      segments = segments.filter(s =>
        s.text.toLowerCase().includes(query) ||
        (getSpeaker(s.speaker)?.name?.toLowerCase() || '').includes(query)
      )
    }
  }

  // Filter by speaker
  if (selectedSpeaker.value) {
    segments = segments.filter(s => s.speaker === selectedSpeaker.value)
  }

  // Filter by key moments
  if (showOnlyKeyMoments.value) {
    segments = segments.filter(s => s.isKeyMoment)
  }

  return segments
})

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

function isActiveSegment(segment: TranscriptSegment): boolean {
  return currentTime.value >= segment.start && currentTime.value <= segment.end
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

function highlightText(text: string): string {
  if (!searchQuery.value.trim()) return text

  const regex = new RegExp(`(${searchQuery.value.trim()})`, 'gi')

  // Use different colors based on search mode
  if (searchMode.value === 'keyword') {
    // Keyword/BM25 search - yellow highlighting
    return text.replace(regex, '<mark class="bg-warning/30 text-warning-700 dark:text-warning-300 px-0.5 rounded font-medium">$1</mark>')
  } else {
    // Smart/hybrid search - blue/primary highlighting
    return text.replace(regex, '<mark class="bg-primary/20 text-primary-700 dark:text-primary-300 px-0.5 rounded font-medium">$1</mark>')
  }
}

// Actions
function seekToSegment(segment: TranscriptSegment) {
  selectedSegment.value = segment
  currentTime.value = segment.start
}

async function toggleKeyMoment(segmentId: string) {
  if (!transcript.value) return

  const segment = transcript.value.segments.find(s => s.id === segmentId)
  if (!segment) return

  const newStatus = !segment.isKeyMoment

  try {
    // Optimistically update UI
    segment.isKeyMoment = newStatus

    // Save to backend
    await api.transcriptions.toggleKeyMoment(transcript.value.id, segmentId, newStatus)

    toast.add({
      title: newStatus ? 'Marked as key moment' : 'Removed key moment',
      color: 'success'
    })
  } catch (err: any) {
    // Revert on error
    segment.isKeyMoment = !newStatus

    toast.add({
      title: 'Failed to update key moment',
      description: err.message || 'An error occurred',
      color: 'error'
    })
  }
}

async function exportTranscript(format: 'docx' | 'srt' | 'vtt') {
  if (!transcript.value) return

  isExporting.value = true
  showExportMenu.value = false

  try {
    const response = await api.transcriptions.export(transcript.value.id, format)

    // Create download link
    const blob = new Blob([response], { type: getContentType(format) })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${transcript.value.title}.${format}`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)

    toast.add({
      title: 'Export successful',
      description: `Transcript exported as ${format.toUpperCase()}`,
      color: 'success'
    })
  } catch (err) {
    toast.add({
      title: 'Export failed',
      description: 'Unable to export transcript',
      color: 'error'
    })
  } finally {
    isExporting.value = false
  }
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

function saveEdit(segmentId: string) {
  if (!transcript.value) return

  const segment = transcript.value.segments.find(s => s.id === segmentId)
  if (segment) {
    segment.text = editText.value
    // TODO: Save to backend
    toast.add({
      title: 'Segment updated',
      color: 'success'
    })
  }

  editingSegmentId.value = null
  editText.value = ''
}

function cancelEdit() {
  editingSegmentId.value = null
  editText.value = ''
}

// Speaker editing functions
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

  // Store original values for rollback
  const originalName = speaker.name
  const originalRole = speaker.role

  try {
    // Optimistically update UI
    speaker.name = editSpeakerName.value
    speaker.role = editSpeakerRole.value || undefined

    // Clear editing state
    editingSpeakerId.value = null
    editSpeakerName.value = ''
    editSpeakerRole.value = ''

    // Save to backend
    await api.transcriptions.updateSpeaker(transcript.value.id, speakerId, {
      name: speaker.name,
      role: speaker.role
    })

    toast.add({
      title: 'Speaker updated',
      description: `Updated ${speaker.name}`,
      color: 'success'
    })
  } catch (err: any) {
    // Revert on error
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

// Delete transcription
async function deleteTranscription() {
  if (!transcript.value) return

  const confirmed = confirm(`Are you sure you want to delete "${transcript.value.title}"? This action cannot be undone.`)
  if (!confirmed) return

  try {
    await api.transcriptions.delete(transcript.value.id)
    toast.add({
      title: 'Transcription deleted',
      description: 'The transcription has been permanently deleted',
      color: 'success'
    })
    // Navigate back to transcripts list
    router.push('/transcripts')
  } catch (err: any) {
    toast.add({
      title: 'Failed to delete transcription',
      description: err.message || 'An error occurred',
      color: 'error'
    })
  }
}

// Load transcript
async function loadTranscript() {
  isLoading.value = true
  error.value = null

  try {
    const response = await api.transcriptions.get(transcriptId.value)
    transcript.value = response
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
  }
})

onMounted(() => {
  loadTranscript()
})
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar :title="transcript?.title || 'Transcript'">
        <template #leading>
          <UButton
            icon="i-lucide-arrow-left"
            color="neutral"
            variant="ghost"
            @click="router.push('/transcripts')"
          />
        </template>
        <template #trailing>
          <UFieldGroup v-if="transcript">
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
                  { label: 'Export as DOCX', icon: 'i-lucide-file-text', click: () => exportTranscript('docx') },
                  { label: 'Export as SRT', icon: 'i-lucide-captions', click: () => exportTranscript('srt') },
                  { label: 'Export as VTT', icon: 'i-lucide-captions', click: () => exportTranscript('vtt') }
                ],
                [
                  { label: 'Delete Transcription', icon: 'i-lucide-trash-2', click: deleteTranscription, class: 'text-error' }
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
              :icon="showMetadataSidebar ? 'i-lucide-sidebar-close' : 'i-lucide-sidebar-open'"
              color="neutral"
              variant="ghost"
              @click="showMetadataSidebar = !showMetadataSidebar"
            />
          </UFieldGroup>
        </template>
      </UDashboardNavbar>
    </template>

    <div class="flex flex-1 min-h-0">
      <!-- Main Content -->
      <div class="flex-1 flex flex-col min-h-0">
        <!-- Loading State -->
        <div v-if="isLoading" class="flex items-center justify-center h-full">
          <div class="text-center space-y-4">
            <UIcon name="i-lucide-loader-circle" class="size-12 text-primary animate-spin mx-auto" />
            <div>
              <h3 class="text-lg font-semibold">Loading transcript...</h3>
              <p class="text-sm text-muted">Please wait while we fetch your transcript</p>
            </div>
          </div>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="flex items-center justify-center h-full">
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

        <!-- Transcript Content -->
        <template v-else-if="transcript">
          <!-- Audio Player (if available) -->
          <div v-if="transcript.audioUrl" class="p-6 border-b border-default bg-default">
            <WaveformPlayer
              :audio-url="transcript.audioUrl"
              :current-time="currentTime"
              :segments="transcript.segments"
              :selected-segment-id="selectedSegment?.id"
              @update:current-time="currentTime = $event"
              @update:is-playing="isPlaying = $event"
              @segment-click="seekToSegment"
            />
          </div>

          <!-- Search and Filters Bar -->
          <div class="p-4 border-b border-default bg-default space-y-3">
            <div class="flex items-center gap-3">
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

              <!-- Search Mode Toggle -->
              <UFieldGroup v-if="searchQuery">
                <UTooltip text="Smart Search (AI-powered semantic + keyword matching)">
                  <UButton
                    :icon="searchMode === 'smart' ? 'i-lucide-sparkles' : 'i-lucide-sparkles'"
                    :color="searchMode === 'smart' ? 'primary' : 'neutral'"
                    :variant="searchMode === 'smart' ? 'soft' : 'ghost'"
                    label="Smart"
                    size="sm"
                    @click="searchMode = 'smart'"
                  />
                </UTooltip>
                <UTooltip text="Keyword Search (Exact BM25 text matching)">
                  <UButton
                    :icon="searchMode === 'keyword' ? 'i-lucide-search' : 'i-lucide-search'"
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

              <UCheckbox
                v-model="showOnlyKeyMoments"
                label="Key Moments Only"
              >
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

          <!-- Transcript Segments -->
          <div class="flex-1 overflow-y-auto p-6">
            <div class="max-w-5xl mx-auto space-y-3">
              <!-- Segments -->
              <div
                v-for="segment in filteredSegments"
                :key="segment.id"
                class="p-4 rounded-lg transition-all cursor-pointer"
                :class="[
                  isActiveSegment(segment)
                    ? 'bg-primary/10 ring-2 ring-primary shadow-sm'
                    : selectedSegment?.id === segment.id
                      ? 'bg-muted/30 ring-1 ring-default'
                      : 'bg-default hover:bg-muted/10'
                ]"
                @click="seekToSegment(segment)"
              >
                <!-- Header -->
                <div class="flex items-start justify-between gap-3 mb-3">
                  <div class="flex items-center gap-2 flex-wrap">
                    <!-- Timestamp Badge -->
                    <UButton
                      :label="formatTime(segment.start)"
                      icon="i-lucide-clock"
                      color="neutral"
                      variant="soft"
                      size="xs"
                      @click.stop="seekToSegment(segment)"
                    />

                    <!-- Speaker Badge -->
                    <div
                      v-if="getSpeaker(segment.speaker)"
                      class="px-3 py-1 rounded-full text-sm font-medium"
                      :style="{
                        backgroundColor: getSpeaker(segment.speaker)!.color + '20',
                        color: getSpeaker(segment.speaker)!.color
                      }"
                    >
                      {{ getSpeaker(segment.speaker)!.name }}
                    </div>
                    <UBadge v-else label="Unknown Speaker" color="neutral" size="xs" variant="soft" />

                    <!-- Key Moment Badge -->
                    <UBadge v-if="segment.isKeyMoment" label="Key Moment" icon="i-lucide-star" color="warning" size="xs" />

                    <!-- Confidence Badge -->
                    <UTooltip v-if="segment.confidence" :text="`Confidence: ${Math.round(segment.confidence * 100)}%`">
                      <UBadge
                        :label="`${Math.round(segment.confidence * 100)}%`"
                        :color="segment.confidence > 0.9 ? 'success' : segment.confidence > 0.7 ? 'warning' : 'neutral'"
                        size="xs"
                        variant="subtle"
                      />
                    </UTooltip>
                  </div>

                  <!-- Actions -->
                  <div class="flex items-center gap-1">
                    <!-- Mark as Key Moment -->
                    <UTooltip :text="segment.isKeyMoment ? 'Remove Key Moment' : 'Mark as Key Moment'">
                      <UButton
                        :icon="segment.isKeyMoment ? 'i-lucide-star' : 'i-lucide-star'"
                        :color="segment.isKeyMoment ? 'warning' : 'neutral'"
                        variant="ghost"
                        size="xs"
                        @click.stop="toggleKeyMoment(segment.id)"
                      />
                    </UTooltip>

                    <!-- Copy Segment -->
                    <UTooltip text="Copy Segment">
                      <UButton
                        icon="i-lucide-copy"
                        color="neutral"
                        variant="ghost"
                        size="xs"
                        @click.stop="copySegmentToClipboard(segment)"
                      />
                    </UTooltip>

                    <!-- Edit -->
                    <UTooltip text="Edit Text">
                      <UButton
                        icon="i-lucide-edit"
                        color="neutral"
                        variant="ghost"
                        size="xs"
                        @click.stop="startEdit(segment)"
                      />
                    </UTooltip>
                  </div>
                </div>

                <!-- Text Content -->
                <div class="mt-2">
                  <div v-if="editingSegmentId === segment.id" class="space-y-2" @click.stop>
                    <UTextarea
                      v-model="editText"
                      autofocus
                      rows="3"
                      @keydown.meta.enter="saveEdit(segment.id)"
                      @keydown.esc="cancelEdit"
                    />
                    <div class="flex gap-2">
                      <UButton
                        label="Save"
                        icon="i-lucide-check"
                        color="primary"
                        size="xs"
                        @click="saveEdit(segment.id)"
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
                    class="text-default leading-relaxed text-base"
                    v-html="highlightText(segment.text)"
                  />
                </div>

                <!-- Tags -->
                <div v-if="segment.tags && segment.tags.length > 0" class="flex flex-wrap gap-1 mt-3">
                  <UBadge
                    v-for="tag in segment.tags"
                    :key="tag"
                    :label="tag"
                    color="neutral"
                    size="xs"
                    variant="outline"
                  />
                </div>
              </div>

              <!-- Empty State -->
              <div v-if="filteredSegments.length === 0" class="text-center py-20">
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
        </template>
      </div>

      <!-- Metadata Sidebar -->
      <div
        v-if="showMetadataSidebar && transcript"
        class="w-96 border-l border-default bg-default overflow-y-auto"
      >
        <div class="p-6 space-y-6">
          <!-- Transcript Info -->
          <div>
            <h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
              <UIcon name="i-lucide-info" class="size-5 text-primary" />
              Transcript Information
            </h3>

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
          </div>

          <USeparator />

          <!-- Statistics -->
          <div v-if="transcriptStats">
            <h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
              <UIcon name="i-lucide-bar-chart" class="size-5 text-primary" />
              Statistics
            </h3>

            <div class="grid grid-cols-2 gap-3">
              <UCard :ui="{ body: 'p-3 space-y-1' }">
                <p class="text-2xl font-bold text-primary">{{ formatDuration(transcriptStats.duration) }}</p>
                <p class="text-xs text-muted">Duration</p>
              </UCard>

              <UCard :ui="{ body: 'p-3 space-y-1' }">
                <p class="text-2xl font-bold text-primary">{{ transcriptStats.totalWords }}</p>
                <p class="text-xs text-muted">Words</p>
              </UCard>

              <UCard :ui="{ body: 'p-3 space-y-1' }">
                <p class="text-2xl font-bold text-primary">{{ transcriptStats.totalSpeakers }}</p>
                <p class="text-xs text-muted">Speakers</p>
              </UCard>

              <UCard :ui="{ body: 'p-3 space-y-1' }">
                <p class="text-2xl font-bold text-primary">{{ transcriptStats.totalSegments }}</p>
                <p class="text-xs text-muted">Segments</p>
              </UCard>

              <UCard v-if="transcriptStats.keyMoments > 0" :ui="{ body: 'p-3 space-y-1' }" class="col-span-2">
                <p class="text-2xl font-bold text-warning">{{ transcriptStats.keyMoments }}</p>
                <p class="text-xs text-muted">Key Moments</p>
              </UCard>
            </div>
          </div>

          <USeparator />

          <!-- Speakers -->
          <div>
            <h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
              <UIcon name="i-lucide-users" class="size-5 text-primary" />
              Speakers
            </h3>

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

                  <!-- Speaking time bar -->
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

          <USeparator />

          <!-- Key Moments -->
          <div v-if="keyMoments.length > 0">
            <h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
              <UIcon name="i-lucide-star" class="size-5 text-warning" />
              Key Moments ({{ keyMoments.length }})
            </h3>

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
          </div>

          <USeparator />

          <!-- Metadata -->
          <div v-if="transcript.metadata">
            <h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
              <UIcon name="i-lucide-file-audio" class="size-5 text-primary" />
              Audio Details
            </h3>

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
          </div>

          <USeparator />

          <!-- Keyboard Shortcuts -->
          <div>
            <h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
              <UIcon name="i-lucide-keyboard" class="size-5 text-primary" />
              Keyboard Shortcuts
            </h3>

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
                <span class="text-muted">Clear Filters</span>
                <UKbd value="Esc" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </UDashboardPanel>
</template>
