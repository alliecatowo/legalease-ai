<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import WaveSurfer from 'wavesurfer.js'
import type { TranscriptSegment } from '~/composables/useTranscription'

const props = defineProps<{
  audioUrl: string
  currentTime?: number
  segments?: TranscriptSegment[]
  selectedSegmentId?: string | null
}>()

const emit = defineEmits<{
  'update:currentTime': [time: number]
  'update:isPlaying': [playing: boolean]
  'ready': [duration: number]
  'segment-click': [segment: TranscriptSegment]
}>()

const waveformRef = ref<HTMLDivElement | null>(null)
const wavesurfer = ref<WaveSurfer | null>(null)
const isReady = ref(false)
const duration = ref(0)
const isPlaying = ref(false)
const volume = ref(1)
const playbackRate = ref(1)

// Playback rate options
const playbackRates = [0.5, 0.75, 1, 1.25, 1.5, 2]

// Initialize WaveSurfer
async function initializeWaveSurfer() {
  if (!waveformRef.value) return

  wavesurfer.value = WaveSurfer.create({
    container: waveformRef.value,
    waveColor: '#94A3B8',
    progressColor: '#3B82F6',
    cursorColor: '#3B82F6',
    barWidth: 2,
    barGap: 1,
    barRadius: 2,
    height: 100,
    normalize: true,
    backend: 'WebAudio',
    interact: true
  })

  // Event listeners
  wavesurfer.value.on('ready', () => {
    isReady.value = true
    duration.value = wavesurfer.value!.getDuration()
    emit('ready', duration.value)
    drawSegmentMarkers()
  })

  wavesurfer.value.on('audioprocess', (time) => {
    emit('update:currentTime', time)
  })

  wavesurfer.value.on('seek', (progress) => {
    const time = progress * duration.value
    emit('update:currentTime', time)
  })

  wavesurfer.value.on('play', () => {
    isPlaying.value = true
    emit('update:isPlaying', true)
  })

  wavesurfer.value.on('pause', () => {
    isPlaying.value = false
    emit('update:isPlaying', false)
  })

  wavesurfer.value.on('finish', () => {
    isPlaying.value = false
    emit('update:isPlaying', false)
  })

  // Load audio
  await wavesurfer.value.load(props.audioUrl)
}

// Draw segment markers on waveform
function drawSegmentMarkers() {
  if (!wavesurfer.value || !props.segments) return

  // TODO: Add visual markers for segments on waveform
  // This would require a WaveSurfer plugin or custom overlay
}

// Play/pause
function togglePlayPause() {
  if (!wavesurfer.value) return
  wavesurfer.value.playPause()
}

// Seek to time
function seekTo(time: number) {
  if (!wavesurfer.value || !duration.value) return
  const progress = time / duration.value
  wavesurfer.value.seekTo(progress)
}

// Skip forward/backward
function skip(seconds: number) {
  if (!wavesurfer.value) return
  const currentTime = wavesurfer.value.getCurrentTime()
  seekTo(currentTime + seconds)
}

// Set volume
function setVolume(vol: number) {
  if (!wavesurfer.value) return
  volume.value = vol
  wavesurfer.value.setVolume(vol)
}

// Set playback rate
function setPlaybackRate(rate: number) {
  if (!wavesurfer.value) return
  playbackRate.value = rate
  wavesurfer.value.setPlaybackRate(rate)
}

// Format time display
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

// Watch for external currentTime updates
watch(() => props.currentTime, (newTime) => {
  if (newTime !== undefined && wavesurfer.value) {
    const currentWavesurferTime = wavesurfer.value.getCurrentTime()
    // Only seek if the difference is significant (>0.5s) to avoid feedback loops
    if (Math.abs(newTime - currentWavesurferTime) > 0.5) {
      seekTo(newTime)
    }
  }
})

// Expose methods
defineExpose({
  play: () => wavesurfer.value?.play(),
  pause: () => wavesurfer.value?.pause(),
  seekTo,
  skip,
  setVolume,
  setPlaybackRate
})

onMounted(() => {
  initializeWaveSurfer()
})

onBeforeUnmount(() => {
  wavesurfer.value?.destroy()
})
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Waveform Container -->
    <div ref="waveformRef" class="w-full bg-muted/20 rounded-lg" />

    <!-- Controls -->
    <div class="flex items-center justify-between gap-4">
      <!-- Playback Controls -->
      <div class="flex items-center gap-2">
        <!-- Skip Backward -->
        <UTooltip text="Skip Back 10s">
          <UButton
            icon="i-lucide-skip-back"
            color="neutral"
            variant="ghost"
            size="sm"
            :disabled="!isReady"
            @click="skip(-10)"
          />
        </UTooltip>

        <!-- Play/Pause -->
        <UButton
          :icon="isPlaying ? 'i-lucide-pause' : 'i-lucide-play'"
          color="primary"
          size="lg"
          :disabled="!isReady"
          @click="togglePlayPause"
        />

        <!-- Skip Forward -->
        <UTooltip text="Skip Forward 10s">
          <UButton
            icon="i-lucide-skip-forward"
            color="neutral"
            variant="ghost"
            size="sm"
            :disabled="!isReady"
            @click="skip(10)"
          />
        </UTooltip>

        <!-- Time Display -->
        <div class="text-sm text-muted ml-2">
          {{ formatTime(currentTime || 0) }} / {{ formatTime(duration) }}
        </div>
      </div>

      <!-- Additional Controls -->
      <div class="flex items-center gap-4">
        <!-- Playback Rate -->
        <USelectMenu
          :model-value="playbackRate"
          :items="playbackRates.map(rate => ({ label: `${rate}x`, value: rate }))"
          @update:model-value="setPlaybackRate"
          size="sm"
        >
          <template #label>
            <div class="flex items-center gap-2">
              <UIcon name="i-lucide-gauge" class="size-4" />
              <span>{{ playbackRate }}x</span>
            </div>
          </template>
        </USelectMenu>

        <!-- Volume -->
        <div class="flex items-center gap-2">
          <UIcon
            :name="volume === 0 ? 'i-lucide-volume-x' : volume < 0.5 ? 'i-lucide-volume-1' : 'i-lucide-volume-2'"
            class="size-4 text-muted"
          />
          <input
            :value="volume"
            type="range"
            min="0"
            max="1"
            step="0.1"
            class="w-24 h-1 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
            @input="(e) => setVolume(parseFloat((e.target as HTMLInputElement).value))"
          />
        </div>
      </div>
    </div>

    <!-- Segment Timeline (optional visual representation) -->
    <div v-if="segments && segments.length > 0" class="relative h-2 bg-muted/20 rounded-full overflow-hidden">
      <div
        v-for="segment in segments"
        :key="segment.id"
        class="absolute h-full cursor-pointer transition-opacity hover:opacity-80"
        :class="segment.id === selectedSegmentId ? 'opacity-100' : 'opacity-60'"
        :style="{
          left: `${(segment.start / duration) * 100}%`,
          width: `${((segment.end - segment.start) / duration) * 100}%`,
          backgroundColor: segment.isKeyMoment ? '#F59E0B' : '#3B82F6'
        }"
        @click="emit('segment-click', segment)"
      />
    </div>
  </div>
</template>
