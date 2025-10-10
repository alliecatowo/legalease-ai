<script setup lang="ts">
import { ref, onMounted } from 'vue'

definePageMeta({
  layout: 'default'
})

const route = useRoute()
const transcriptionId = route.params.id as string

const transcription = useTranscription()
const waveformRef = ref<any>(null)

const showSpeakers = ref(true)
const showKeyMomentsOnly = ref(false)

// Load transcription on mount
onMounted(() => {
  transcription.loadTranscription(transcriptionId)
})

// Handle segment seek from transcript
function handleSeekToSegment(segment: any) {
  transcription.seekToSegment(segment)
  waveformRef.value?.seekTo(segment.start)
}

// Handle segment click from waveform timeline
function handleSegmentClick(segment: any) {
  transcription.seekToSegment(segment)
}

// Export handlers
function handleExport(format: 'txt' | 'pdf' | 'docx' | 'srt' | 'vtt') {
  const content = transcription.exportTranscript(format)

  // Create download
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `transcript.${format}`
  link.click()
  URL.revokeObjectURL(url)
}

// Copy transcript to clipboard
async function copyToClipboard() {
  const text = transcription.exportTranscript('txt')
  await navigator.clipboard.writeText(text)
  // TODO: Show toast notification
}

// Search in transcript
function handleSearch(query: string) {
  transcription.searchQuery.value = query
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar
        :title="transcription.currentTranscription.value?.title || 'Transcription'"
      >
        <template #leading>
          <UButton
            icon="i-lucide-arrow-left"
            color="neutral"
            variant="ghost"
            to="/transcription"
          />
        </template>

        <template #trailing>
          <UButtonGroup>
            <!-- Search -->
            <UInput
              :model-value="transcription.searchQuery.value"
              icon="i-lucide-search"
              placeholder="Search transcript..."
              size="sm"
              class="w-64"
              @update:model-value="handleSearch"
            />

            <!-- Key Moments Filter -->
            <UTooltip :text="showKeyMomentsOnly ? 'Show All' : 'Show Key Moments Only'">
              <UButton
                icon="i-lucide-star"
                :color="showKeyMomentsOnly ? 'warning' : 'neutral'"
                variant="ghost"
                @click="showKeyMomentsOnly = !showKeyMomentsOnly; transcription.showOnlyKeyMoments.value = showKeyMomentsOnly"
              />
            </UTooltip>

            <!-- Export Menu -->
            <UDropdownMenu
              :items="[
                [
                  { label: 'Export as Text', icon: 'i-lucide-file-text', click: () => handleExport('txt') },
                  { label: 'Export as SRT', icon: 'i-lucide-subtitles', click: () => handleExport('srt') },
                  { label: 'Export as WebVTT', icon: 'i-lucide-captions', click: () => handleExport('vtt') }
                ],
                [
                  { label: 'Copy to Clipboard', icon: 'i-lucide-copy', click: copyToClipboard }
                ]
              ]"
            >
              <UButton
                icon="i-lucide-download"
                label="Export"
                color="neutral"
                variant="ghost"
              />
            </UDropdownMenu>

            <!-- More Options -->
            <UDropdownMenu
              :items="[
                [
                  { label: 'Add to Case', icon: 'i-lucide-folder-plus' },
                  { label: 'Share', icon: 'i-lucide-share' },
                  { label: 'Settings', icon: 'i-lucide-settings' }
                ]
              ]"
            >
              <UButton
                icon="i-lucide-more-horizontal"
                color="neutral"
                variant="ghost"
              />
            </UDropdownMenu>
          </UButtonGroup>
        </template>
      </UDashboardNavbar>
    </template>

    <!-- Loading State -->
    <div v-if="transcription.isLoading.value" class="flex items-center justify-center h-screen">
      <div class="text-center">
        <UIcon name="i-lucide-loader" class="size-12 text-primary animate-spin mb-4" />
        <p class="text-muted">Loading transcription...</p>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="transcription.error.value" class="flex items-center justify-center h-screen">
      <div class="text-center max-w-md">
        <UIcon name="i-lucide-alert-circle" class="size-12 text-error mx-auto mb-4" />
        <h3 class="text-lg font-semibold text-highlighted mb-2">Error Loading Transcription</h3>
        <p class="text-muted mb-4">{{ transcription.error.value }}</p>
        <UButton
          label="Retry"
          icon="i-lucide-refresh-cw"
          color="primary"
          @click="transcription.loadTranscription(transcriptionId)"
        />
      </div>
    </div>

    <!-- Main Content -->
    <div v-else-if="transcription.currentTranscription.value" class="flex flex-col h-[calc(100vh-64px)]">
      <!-- Info Bar -->
      <div class="p-4 border-b border-default bg-default">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <UIcon name="i-lucide-mic" class="size-5 text-primary" />
            <div>
              <h2 class="font-semibold text-highlighted">
                {{ transcription.currentTranscription.value.title }}
              </h2>
              <div class="flex items-center gap-3 text-sm text-muted mt-1">
                <span v-if="transcription.currentTranscription.value.caseName">
                  {{ transcription.currentTranscription.value.caseName }}
                </span>
                <span>•</span>
                <span>{{ transcription.formatTime(transcription.currentTranscription.value.duration) }}</span>
                <span>•</span>
                <span>{{ transcription.currentTranscription.value.segments.length }} segments</span>
                <span v-if="transcription.keyMoments.value.length > 0">
                  •
                  <span class="text-warning">{{ transcription.keyMoments.value.length }} key moments</span>
                </span>
              </div>
            </div>
          </div>
          <UBadge
            :label="transcription.currentTranscription.value.status"
            :color="transcription.currentTranscription.value.status === 'completed' ? 'success' : 'warning'"
            variant="soft"
          />
        </div>
      </div>

      <!-- Waveform Player -->
      <div class="p-6 border-b border-default bg-default">
        <WaveformPlayer
          ref="waveformRef"
          :audio-url="transcription.currentTranscription.value.audioUrl"
          :current-time="transcription.currentTime.value"
          :segments="transcription.currentTranscription.value.segments"
          :selected-segment-id="transcription.selectedSegment.value?.id"
          @update:current-time="(time) => transcription.currentTime.value = time"
          @update:is-playing="(playing) => transcription.isPlaying.value = playing"
          @segment-click="handleSegmentClick"
        />
      </div>

      <!-- Content Area -->
      <div class="flex-1 flex overflow-hidden">
        <!-- Transcript Panel -->
        <div class="flex-1 overflow-hidden border-r border-default">
          <TranscriptPanel
            :segments="transcription.filteredSegments.value"
            :speakers="transcription.currentTranscription.value.speakers"
            :current-time="transcription.currentTime.value"
            :selected-segment="transcription.selectedSegment.value"
            :search-query="transcription.searchQuery.value"
            @seek-to-segment="handleSeekToSegment"
            @toggle-key-moment="transcription.toggleKeyMoment"
            @edit-segment="transcription.editSegmentText"
            @assign-speaker="transcription.assignSpeaker"
          />
        </div>

        <!-- Speaker Sidebar -->
        <div v-if="showSpeakers" class="w-80 bg-default">
          <SpeakerManager
            :speakers="transcription.currentTranscription.value.speakers"
            :selected-speaker="transcription.selectedSpeaker.value"
            @select-speaker="(id) => transcription.selectedSpeaker.value = id"
            @add-speaker="transcription.addSpeaker"
            @update-speaker="transcription.updateSpeaker"
          />
        </div>

        <!-- Sidebar Toggle (when collapsed) -->
        <div v-else class="fixed right-0 top-1/2 -translate-y-1/2">
          <UButton
            icon="i-lucide-panel-right"
            color="neutral"
            variant="soft"
            @click="showSpeakers = true"
          />
        </div>
      </div>
    </div>
  </UDashboardPanel>
</template>
