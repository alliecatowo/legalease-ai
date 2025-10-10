<template>
  <div class="bg-white rounded-lg border border-gray-200">
    <!-- Audio Player -->
    <div class="p-4 border-b border-gray-200">
      <AudioPlayer
        v-if="audioUrl"
        :url="audioUrl"
        :duration="duration"
        :current-time="currentTime"
        @time-update="onTimeUpdate"
        @play="onPlay"
        @pause="onPause"
        @seek="onSeek"
      />
      <div v-else class="text-center py-8">
        <UIcon name="i-heroicons-musical-note-20-solid" class="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <p class="text-gray-500">No audio file available</p>
      </div>
    </div>

    <!-- Transcript Content -->
    <div class="max-h-96 overflow-y-auto">
      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-12">
        <UIcon name="i-heroicons-arrow-path-20-solid" class="w-8 h-8 animate-spin text-blue-600 mr-3" />
        <span class="text-gray-600">Loading transcript...</span>
      </div>

      <!-- Transcript Segments -->
      <div v-else-if="segments.length > 0" class="divide-y divide-gray-100">
        <div
          v-for="segment in segments"
          :key="segment.id"
          class="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
          :class="{
            'bg-blue-50 border-l-4 border-blue-500': isActiveSegment(segment),
            'bg-yellow-50': segment.speaker === 'SPEAKER_01' && showSpeakerColors,
            'bg-green-50': segment.speaker === 'SPEAKER_02' && showSpeakerColors,
            'bg-purple-50': segment.speaker === 'SPEAKER_03' && showSpeakerColors
          }"
          @click="seekToSegment(segment)"
        >
          <!-- Segment Header -->
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center space-x-3">
              <!-- Speaker Badge -->
              <UBadge
                v-if="segment.speaker"
                :color="getSpeakerColor(segment.speaker)"
                variant="subtle"
                size="sm"
              >
                {{ formatSpeaker(segment.speaker) }}
              </UBadge>

              <!-- Timestamp -->
              <span class="text-xs text-gray-500 font-mono">
                {{ formatTime(segment.start) }}
              </span>

              <!-- Confidence Score -->
              <span
                v-if="segment.confidence"
                class="text-xs text-gray-400"
              >
                {{ Math.round(segment.confidence * 100) }}%
              </span>
            </div>

            <!-- Actions -->
            <div class="flex items-center space-x-1">
              <UButton
                variant="ghost"
                size="xs"
                @click.stop="editSegment(segment)"
              >
                <UIcon name="i-heroicons-pencil-20-solid" class="w-3 h-3" />
              </UButton>
              <UButton
                variant="ghost"
                size="xs"
                @click.stop="copySegmentText(segment)"
              >
                <UIcon name="i-heroicons-clipboard-20-solid" class="w-3 h-3" />
              </UButton>
            </div>
          </div>

          <!-- Segment Text -->
          <p class="text-gray-900 leading-relaxed">
            {{ segment.text }}
          </p>

          <!-- Edit Mode -->
          <div v-if="editingSegment === segment.id" class="mt-3">
            <UTextarea
              v-model="editText"
              placeholder="Edit transcript text..."
              rows="2"
              class="mb-2"
            />
            <div class="flex items-center space-x-2">
              <UButton
                size="xs"
                @click.stop="saveSegmentEdit(segment)"
              >
                Save
              </UButton>
              <UButton
                variant="outline"
                size="xs"
                @click.stop="cancelSegmentEdit"
              >
                Cancel
              </UButton>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="text-center py-12">
        <UIcon name="i-heroicons-chat-bubble-left-right-20-solid" class="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">No transcript available</h3>
        <p class="text-gray-500 mb-4">
          This document doesn't have a transcript yet.
        </p>
        <UButton
          v-if="canGenerateTranscript"
          color="primary"
          @click="generateTranscript"
          :loading="generating"
        >
          <UIcon name="i-heroicons-play-20-solid" class="w-4 h-4 mr-2" />
          Generate Transcript
        </UButton>
      </div>
    </div>

    <!-- Transcript Actions -->
    <div v-if="segments.length > 0" class="p-4 border-t border-gray-200 bg-gray-50">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <UButton
            variant="outline"
            size="sm"
            @click="exportTranscript('docx')"
          >
            <UIcon name="i-heroicons-document-20-solid" class="w-4 h-4 mr-2" />
            Export DOCX
          </UButton>

          <UButton
            variant="outline"
            size="sm"
            @click="exportTranscript('srt')"
          >
            <UIcon name="i-heroicons-queue-list-20-solid" class="w-4 h-4 mr-2" />
            Export SRT
          </UButton>

          <UButton
            variant="outline"
            size="sm"
            @click="toggleSpeakerColors"
          >
            <UIcon name="i-heroicons-swatch-20-solid" class="w-4 h-4 mr-2" />
            {{ showSpeakerColors ? 'Hide' : 'Show' }} Colors
          </UButton>
        </div>

        <div class="flex items-center space-x-2">
          <span class="text-sm text-gray-600">
            {{ segments.length }} segments
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

interface TranscriptSegment {
  id: string
  start: number
  end: number
  text: string
  speaker?: string
  confidence?: number
}

interface Props {
  documentId: string
  audioUrl?: string
  segments: TranscriptSegment[]
  duration?: number
  loading?: boolean
  canGenerateTranscript?: boolean
}

interface Emits {
  'time-update': [time: number]
  'segment-click': [segment: TranscriptSegment]
  'export': [format: string]
  'generate-transcript': []
  'update-segments': [segments: TranscriptSegment[]]
}

const props = withDefaults(defineProps<Props>(), {
  segments: () => [],
  loading: false,
  canGenerateTranscript: false
})

const emit = defineEmits<Emits>()

// Reactive state
const currentTime = ref(0)
const isPlaying = ref(false)
const editingSegment = ref<string | null>(null)
const editText = ref('')
const showSpeakerColors = ref(true)
const generating = ref(false)

// Computed
const activeSegment = computed(() => {
  if (!isPlaying.value) return null

  return props.segments.find(segment =>
    currentTime.value >= segment.start && currentTime.value <= segment.end
  )
})

// Methods
function isActiveSegment(segment: TranscriptSegment): boolean {
  return activeSegment.value?.id === segment.id
}

function onTimeUpdate(time: number) {
  currentTime.value = time
  emit('time-update', time)
}

function onPlay() {
  isPlaying.value = true
}

function onPause() {
  isPlaying.value = false
}

function onSeek(time: number) {
  currentTime.value = time
}

function seekToSegment(segment: TranscriptSegment) {
  currentTime.value = segment.start
  emit('segment-click', segment)
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)
  return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`
}

function formatSpeaker(speaker: string): string {
  // Convert SPEAKER_01 to Speaker 1, etc.
  const match = speaker.match(/SPEAKER_(\d+)/)
  if (match) {
    return `Speaker ${match[1]}`
  }
  return speaker
}

function getSpeakerColor(speaker: string): string {
  const colors: Record<string, string> = {
    'SPEAKER_01': 'blue',
    'SPEAKER_02': 'green',
    'SPEAKER_03': 'purple',
    'SPEAKER_04': 'orange',
    'SPEAKER_05': 'red'
  }
  return colors[speaker] || 'gray'
}

function editSegment(segment: TranscriptSegment) {
  editingSegment.value = segment.id
  editText.value = segment.text
}

function cancelSegmentEdit() {
  editingSegment.value = null
  editText.value = ''
}

function saveSegmentEdit(segment: TranscriptSegment) {
  if (!editText.value.trim()) return

  // Update the segment text
  const updatedSegments = props.segments.map(s =>
    s.id === segment.id
      ? { ...s, text: editText.value.trim() }
      : s
  )

  emit('update-segments', updatedSegments)
  editingSegment.value = null
  editText.value = ''
}

function copySegmentText(segment: TranscriptSegment) {
  navigator.clipboard.writeText(segment.text).then(() => {
    // Could show a toast notification here
    console.log('Text copied to clipboard')
  })
}

function toggleSpeakerColors() {
  showSpeakerColors.value = !showSpeakerColors.value
}

async function generateTranscript() {
  generating.value = true
  try {
    emit('generate-transcript')
  } catch (error) {
    console.error('Failed to generate transcript:', error)
  } finally {
    generating.value = false
  }
}

async function exportTranscript(format: string) {
  emit('export', format)
}

// Auto-scroll to active segment
watch(activeSegment, (newSegment) => {
  if (newSegment) {
    // Could implement auto-scrolling to the active segment
    // This would require refs to the segment elements
  }
})
</script>