<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import WaveSurfer from 'wavesurfer.js'
import type { TranscriptSegment } from '~/composables/useTranscription'
import { useThrottleFn } from '@vueuse/core'

const props = defineProps<{
  audioUrl: string
  transcriptionId?: number  // Optional transcription ID for fetching pre-computed waveform
  currentTime?: number
  segments?: TranscriptSegment[]
  selectedSegmentId?: string | null
  keyMoments?: TranscriptSegment[]
}>()

const emit = defineEmits<{
  'update:currentTime': [time: number]
  'update:isPlaying': [playing: boolean]
  'ready': [duration: number]
  'segment-click': [segment: TranscriptSegment]
  'waveform-click': [time: number]
}>()

const waveformRef = ref<HTMLDivElement | null>(null)
const wavesurfer = ref<WaveSurfer | null>(null)
const isReady = ref(false)
const isAudioReady = ref(false) // Audio can play before waveform is drawn
const isLoading = ref(false)
const loadingProgress = ref(0)
const duration = ref(0)
const isPlaying = ref(false)
const volume = ref(1)
const playbackRate = ref(1)
const timelineCanvasRef = ref<HTMLCanvasElement | null>(null)
const keyMomentsCanvasRef = ref<HTMLCanvasElement | null>(null)

// Playback rate options
const playbackRates = [0.5, 0.75, 1, 1.25, 1.5, 2]

// Pre-computed waveform API removed - Firebase backend doesn't support it
// Always use client-side waveform generation

// Initialize WaveSurfer
async function initializeWaveSurfer() {
  if (!waveformRef.value) return

  isLoading.value = true
  loadingProgress.value = 0

  // Create audio element with optimal streaming settings
  const audio = document.createElement('audio')
  audio.preload = 'metadata' // Load metadata quickly, stream rest on demand
  audio.crossOrigin = 'anonymous'

  wavesurfer.value = WaveSurfer.create({
    container: waveformRef.value,
    waveColor: '#94A3B8',
    progressColor: '#3B82F6',
    cursorColor: '#3B82F6',
    barWidth: 3,
    barGap: 1,
    barRadius: 2,
    height: 80,
    normalize: true,
    backend: 'MediaElement',
    mediaControls: false,
    interact: true,
    media: audio
  })

  // Enable play button immediately - browser will buffer on play
  // This is how native audio works - no waiting!
  setTimeout(() => {
    isAudioReady.value = true
  }, 100)

  // Loading progress
  wavesurfer.value.on('loading', (percent: number) => {
    // Validate percent is a valid number
    if (isFinite(percent) && percent >= 0 && percent <= 100) {
      loadingProgress.value = percent
    }
  })

  // Ready event - waveform fully loaded
  wavesurfer.value.on('ready', () => {
    isReady.value = true
    isLoading.value = false
    loadingProgress.value = 100
    duration.value = wavesurfer.value!.getDuration()
    emit('ready', duration.value)
    drawSegmentMarkers()
    drawKeyMomentsOverlay()
  })

  // Throttle audioprocess to 100ms instead of 60fps for better performance
  const throttledAudioProcess = useThrottleFn((time: number) => {
    emit('update:currentTime', time)
  }, 100)

  wavesurfer.value.on('audioprocess', throttledAudioProcess)

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

  // Error handling
  wavesurfer.value.on('error', (error: string) => {
    console.error('WaveSurfer error:', error)
    isLoading.value = false
    isReady.value = false
  })

  // Load audio and generate waveform on client
  console.log('Loading audio and generating waveform:', props.audioUrl)
  wavesurfer.value.load(props.audioUrl).catch((error) => {
    console.error('Failed to load audio:', error)
    isLoading.value = false
    isAudioReady.value = false
  })
}

// Draw segment markers on waveform
function drawSegmentMarkers() {
  if (!wavesurfer.value || !props.segments) return

  // Segment markers are now handled by the timeline canvas below
  // This function is kept for future enhancements
}

// Draw key moments overlay on waveform
function drawKeyMomentsOverlay() {
  if (!keyMomentsCanvasRef.value || !props.keyMoments || !duration.value) return

  const canvas = keyMomentsCanvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // Set canvas dimensions to match waveform container
  const waveformContainer = waveformRef.value
  if (!waveformContainer) return

  const rect = waveformContainer.getBoundingClientRect()
  canvas.width = rect.width * window.devicePixelRatio
  canvas.height = rect.height * window.devicePixelRatio
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

  // Clear canvas
  ctx.clearRect(0, 0, rect.width, rect.height)

  // Draw key moment markers
  props.keyMoments.forEach((moment) => {
    const x = (moment.start / duration.value) * rect.width

    // Draw vertical line
    ctx.strokeStyle = '#F59E0B' // Warning color
    ctx.lineWidth = 2
    ctx.globalAlpha = 0.8

    // Draw a dotted line
    ctx.setLineDash([4, 4])
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, rect.height)
    ctx.stroke()

    // Draw star icon at top
    ctx.globalAlpha = 1.0
    ctx.fillStyle = '#F59E0B'
    ctx.setLineDash([]) // Reset to solid line
    const starSize = 6
    const starY = 8

    // Simple star shape (triangle for performance)
    ctx.beginPath()
    ctx.moveTo(x, starY)
    ctx.lineTo(x - starSize / 2, starY + starSize)
    ctx.lineTo(x + starSize / 2, starY + starSize)
    ctx.closePath()
    ctx.fill()
  })

  ctx.globalAlpha = 1.0
}

// Handle waveform click - emit time and find segment
function handleWaveformClick(event: MouseEvent) {
  if (!waveformRef.value || !duration.value) return

  const rect = waveformRef.value.getBoundingClientRect()
  const clickX = event.clientX - rect.left
  const clickTime = (clickX / rect.width) * duration.value

  // Emit waveform click event with time
  emit('waveform-click', clickTime)

  // Also seek to that time
  seekTo(clickTime)
}

// Draw segment timeline on canvas
function drawSegmentTimeline() {
  if (!timelineCanvasRef.value || !props.segments || !duration.value) return

  const canvas = timelineCanvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // Set canvas dimensions to match display size
  const rect = canvas.getBoundingClientRect()
  canvas.width = rect.width * window.devicePixelRatio
  canvas.height = rect.height * window.devicePixelRatio
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

  // Clear canvas
  ctx.clearRect(0, 0, rect.width, rect.height)

  // Draw each segment
  props.segments.forEach((segment) => {
    const left = (segment.start / duration.value) * rect.width
    const width = ((segment.end - segment.start) / duration.value) * rect.width

    // Set color based on segment type and selection
    const isSelected = segment.id === props.selectedSegmentId
    const baseColor = segment.isKeyMoment ? '#F59E0B' : '#3B82F6'
    const opacity = isSelected ? 1.0 : 0.6

    ctx.fillStyle = baseColor
    ctx.globalAlpha = opacity
    ctx.fillRect(left, 0, width, rect.height)
  })

  ctx.globalAlpha = 1.0
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

// Watch for changes that require redrawing the timeline
watch([() => props.segments, () => props.selectedSegmentId, duration], () => {
  drawSegmentTimeline()
}, { deep: true })

// Watch for changes that require redrawing key moments
watch([() => props.keyMoments, duration], () => {
  drawKeyMomentsOverlay()
}, { deep: true })

// Handle canvas click
function handleTimelineClick(event: MouseEvent) {
  if (!timelineCanvasRef.value || !props.segments || !duration.value) return

  const rect = timelineCanvasRef.value.getBoundingClientRect()
  const clickX = event.clientX - rect.left
  const clickTime = (clickX / rect.width) * duration.value

  // Find the segment at this time
  const segment = props.segments.find(s => clickTime >= s.start && clickTime <= s.end)
  if (segment) {
    emit('segment-click', segment)
  }
}

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

  // Add resize observer to redraw canvases on window resize
  if (waveformRef.value) {
    const resizeObserver = new ResizeObserver(() => {
      drawSegmentTimeline()
      drawKeyMomentsOverlay()
    })
    resizeObserver.observe(waveformRef.value)

    // Store observer for cleanup
    onBeforeUnmount(() => {
      resizeObserver.disconnect()
    })
  }
})

onBeforeUnmount(() => {
  wavesurfer.value?.destroy()
})
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Loading Skeleton with Progress -->
    <div v-if="isLoading && !isReady" class="w-full bg-muted/20 rounded-lg p-8">
      <div class="text-center space-y-4">
        <UIcon name="i-lucide-loader-circle" class="size-8 text-primary animate-spin mx-auto" />
        <div class="space-y-2">
          <p class="text-sm text-muted">Loading waveform... {{ loadingProgress }}%</p>
          <p class="text-xs text-muted">Audio playback available while loading</p>
        </div>
      </div>
    </div>

    <!-- Waveform Container -->
    <div class="relative w-full">
      <div ref="waveformRef" class="w-full bg-muted/20 rounded-lg cursor-pointer" :class="{ 'hidden': !isReady }" @click="handleWaveformClick" />
      <!-- Key Moments Overlay Canvas -->
      <canvas
        v-if="keyMoments && keyMoments.length > 0 && isReady"
        ref="keyMomentsCanvasRef"
        class="absolute top-0 left-0 w-full h-full pointer-events-none"
        :class="{ 'hidden': !isReady }"
      />
    </div>

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
            :disabled="!isAudioReady"
            @click="skip(-10)"
          />
        </UTooltip>

        <!-- Play/Pause -->
        <UButton
          :icon="isPlaying ? 'i-lucide-pause' : 'i-lucide-play'"
          color="primary"
          size="lg"
          :disabled="!isAudioReady"
          @click="togglePlayPause"
        />

        <!-- Skip Forward -->
        <UTooltip text="Skip Forward 10s">
          <UButton
            icon="i-lucide-skip-forward"
            color="neutral"
            variant="ghost"
            size="sm"
            :disabled="!isAudioReady"
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

    <!-- Segment Timeline (Canvas-based for better performance) -->
    <canvas
      v-if="segments && segments.length > 0"
      ref="timelineCanvasRef"
      class="w-full h-2 bg-muted/20 rounded-full cursor-pointer"
      @click="handleTimelineClick"
    />
  </div>
</template>
