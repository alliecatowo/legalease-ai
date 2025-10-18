<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount, computed, nextTick } from 'vue'
import WaveSurfer from 'wavesurfer.js'
import type { TranscriptSegment } from '~/composables/useTranscription'
import { useThrottleFn } from '@vueuse/core'

const props = withDefaults(defineProps<{
  mediaUrl: string
  mediaType?: 'video' | 'audio' // Explicitly specify media type
  transcriptionId?: string  // Optional transcription GID for fetching pre-computed waveform
  isPlaying?: boolean // External control of play/pause state
  segments?: TranscriptSegment[]
  selectedSegmentId?: string | null
  keyMoments?: TranscriptSegment[]
  size?: 'small' | 'theater' | 'fullscreen' // Video size mode (controlled by parent)
  hideControls?: boolean // Hide the built-in controls (when parent provides them)
}>(), {
  size: 'theater',
  hideControls: false
})

const emit = defineEmits<{
  'update:currentTime': [time: number]
  'update:isPlaying': [playing: boolean]
  'ready': [duration: number]
  'segment-click': [segment: TranscriptSegment]
  'waveform-click': [time: number]
}>()

const waveformRef = ref<HTMLDivElement | null>(null)
const videoRef = ref<HTMLVideoElement | null>(null)
const wavesurfer = ref<WaveSurfer | null>(null)
const isReady = ref(false)
const isMediaReady = ref(false) // Media can play before waveform is drawn
const isLoading = ref(false)
const loadingProgress = ref(0)
const duration = ref(0)
const currentTime = ref(0) // Track current playback time internally
const isPlaying = ref(false)
const volume = ref(1)
const playbackRate = ref(1)
const timelineCanvasRef = ref<HTMLCanvasElement | null>(null)
const keyMomentsCanvasRef = ref<HTMLCanvasElement | null>(null)
// Computed: determine if this is a video or audio-only player
const isVideo = computed(() => props.mediaType === 'video')

// Playback rate options
const playbackRates = [0.5, 0.75, 1, 1.25, 1.5, 2]

// Video size classes (controlled by parent via size prop)
const videoContainerClass = computed(() => {
  if (!isVideo.value) return ''

  switch (props.size) {
    case 'small':
      return 'w-full max-w-xl mx-auto' // Full width up to 576px, centered
    case 'theater':
      return 'w-full' // Full width of container
    case 'fullscreen':
      return 'w-full' // Full width
    default:
      return 'w-full'
  }
})

// Fetch pre-computed waveform data from API
async function fetchWaveformData(): Promise<{ peaks: number[], duration: number } | null> {
  if (!props.transcriptionId) return null

  try {
    const response = await fetch(`/api/v1/transcriptions/${encodeURIComponent(props.transcriptionId)}/waveform`)
    if (response.ok) {
      const data = await response.json()
      return { peaks: data.peaks, duration: data.duration }
    }
    return null
  } catch (error) {
    return null
  }
}

// Initialize WaveSurfer
async function initializeWaveSurfer() {
  if (!waveformRef.value) return

  isLoading.value = true
  loadingProgress.value = 0

  // Create appropriate media element
  let mediaElement: HTMLMediaElement
  if (isVideo.value) {
    if (!videoRef.value) {
      isLoading.value = false
      return
    }
    mediaElement = videoRef.value
  } else {
    const audio = document.createElement('audio')
    audio.preload = 'metadata'
    audio.crossOrigin = 'anonymous'
    mediaElement = audio
  }

  wavesurfer.value = WaveSurfer.create({
    container: waveformRef.value,
    waveColor: '#94A3B8',
    progressColor: '#3B82F6',
    cursorColor: '#3B82F6',
    barWidth: 3,
    barGap: 1,
    barRadius: 2,
    height: isVideo.value ? 40 : 80,
    normalize: true,
    backend: 'MediaElement',
    mediaControls: false,
    interact: true,
    media: mediaElement
  })

  // Enable controls after short delay
  setTimeout(() => { isMediaReady.value = true }, 100)

  // Loading progress
  wavesurfer.value.on('loading', (percent: number) => {
    if (isFinite(percent) && percent >= 0 && percent <= 100) {
      loadingProgress.value = percent
    }
  })

  // Ready - waveform loaded
  wavesurfer.value.on('ready', () => {
    isReady.value = true
    isLoading.value = false
    loadingProgress.value = 100
    duration.value = wavesurfer.value!.getDuration()
    emit('ready', duration.value)

    nextTick(() => {
      drawKeyMomentsOverlay()
      drawSegmentTimeline()
    })
  })

  // Update time during playback (throttled)
  const throttledAudioProcess = useThrottleFn((time: number) => {
    currentTime.value = time
    emit('update:currentTime', time)
  }, 100)

  wavesurfer.value.on('audioprocess', throttledAudioProcess)

  wavesurfer.value.on('seek', (progress) => {
    const time = progress * duration.value
    currentTime.value = time
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

  wavesurfer.value.on('error', () => {
    isLoading.value = false
    isReady.value = false
  })

  // Load waveform (pre-computed if available, otherwise generate)
  const waveformData = await fetchWaveformData()

  if (waveformData?.peaks && waveformData?.duration) {
    const peaksArray = [waveformData.peaks]
    wavesurfer.value.load(props.mediaUrl, peaksArray, waveformData.duration).catch(() => {
      isLoading.value = false
      isMediaReady.value = false
    })
  } else {
    wavesurfer.value.load(props.mediaUrl).catch(() => {
      isLoading.value = false
      isMediaReady.value = false
    })
  }
}

// Draw key moments overlay on waveform
function drawKeyMomentsOverlay() {
  if (!keyMomentsCanvasRef.value || !props.keyMoments || !duration.value) return

  const canvas = keyMomentsCanvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const waveformContainer = waveformRef.value
  if (!waveformContainer) return

  const rect = waveformContainer.getBoundingClientRect()
  canvas.width = rect.width * window.devicePixelRatio
  canvas.height = rect.height * window.devicePixelRatio
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

  ctx.clearRect(0, 0, rect.width, rect.height)

  props.keyMoments.forEach((moment) => {
    const x = (moment.start / duration.value) * rect.width

    // Draw dotted vertical line
    ctx.strokeStyle = '#F59E0B'
    ctx.lineWidth = 2
    ctx.globalAlpha = 0.8
    ctx.setLineDash([4, 4])
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, rect.height)
    ctx.stroke()

    // Draw star marker
    ctx.globalAlpha = 1.0
    ctx.fillStyle = '#F59E0B'
    ctx.setLineDash([])
    const starSize = 6
    const starY = 8
    ctx.beginPath()
    ctx.moveTo(x, starY)
    ctx.lineTo(x - starSize / 2, starY + starSize)
    ctx.lineTo(x + starSize / 2, starY + starSize)
    ctx.closePath()
    ctx.fill()
  })

  ctx.globalAlpha = 1.0
}

// Handle waveform click
function handleWaveformClick(event: MouseEvent) {
  if (!waveformRef.value || !duration.value) return

  const rect = waveformRef.value.getBoundingClientRect()
  const clickX = event.clientX - rect.left
  const clickTime = (clickX / rect.width) * duration.value

  emit('waveform-click', clickTime)
  seekTo(clickTime)
}

// Draw segment timeline
function drawSegmentTimeline() {
  if (!timelineCanvasRef.value || !props.segments || !duration.value) return

  const canvas = timelineCanvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const displayHeight = isVideo.value ? 12 : canvas.getBoundingClientRect().height
  const rect = canvas.getBoundingClientRect()

  if (rect.width < 100) return

  canvas.width = rect.width * window.devicePixelRatio
  canvas.height = displayHeight * window.devicePixelRatio
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

  ctx.clearRect(0, 0, rect.width, displayHeight)

  props.segments.forEach((segment) => {
    const left = (segment.start / duration.value) * rect.width
    const width = ((segment.end - segment.start) / duration.value) * rect.width
    const isSelected = segment.id === props.selectedSegmentId
    const baseColor = segment.isKeyMoment ? '#F59E0B' : '#3B82F6'

    ctx.fillStyle = baseColor
    ctx.globalAlpha = isSelected ? 1.0 : 0.7
    ctx.fillRect(left, 0, width, displayHeight)
  })

  ctx.globalAlpha = 1.0
}

function togglePlayPause() {
  wavesurfer.value?.playPause()
}

function seekTo(time: number) {
  wavesurfer.value?.setTime(time)
}

function skip(seconds: number) {
  if (!wavesurfer.value) return
  const currentTime = wavesurfer.value.getCurrentTime()
  seekTo(currentTime + seconds)
}

function setVolume(vol: number) {
  if (!wavesurfer.value) return
  volume.value = vol
  wavesurfer.value.setVolume(vol)
}

function setPlaybackRate(rate: number) {
  if (!wavesurfer.value) return
  playbackRate.value = rate
  wavesurfer.value.setPlaybackRate(rate)
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

// Sync external isPlaying prop with wavesurfer
watch(() => props.isPlaying, (shouldPlay) => {
  if (shouldPlay !== undefined && wavesurfer.value && isReady.value && shouldPlay !== isPlaying.value) {
    shouldPlay ? wavesurfer.value.play() : wavesurfer.value.pause()
  }
})

watch([() => props.segments, () => props.selectedSegmentId, duration], drawSegmentTimeline, { deep: true })
watch([() => props.keyMoments, duration], drawKeyMomentsOverlay, { deep: true })

function handleTimelineClick(event: MouseEvent) {
  if (!timelineCanvasRef.value || !duration.value) return

  const rect = timelineCanvasRef.value.getBoundingClientRect()
  const clickX = event.clientX - rect.left
  const clickTime = (clickX / rect.width) * duration.value

  seekTo(clickTime)
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

let resizeObserver: ResizeObserver | null = null
let timelineObserver: ResizeObserver | null = null

onMounted(async () => {
  if (isVideo.value) {
    await nextTick()
    let attempts = 0
    while (!videoRef.value && attempts < 10) {
      await new Promise(resolve => setTimeout(resolve, 50))
      attempts++
    }
    if (!videoRef.value) {
      isLoading.value = false
      return
    }
  }

  initializeWaveSurfer()

  await nextTick()
  if (waveformRef.value) {
    resizeObserver = new ResizeObserver(() => {
      drawSegmentTimeline()
      drawKeyMomentsOverlay()
    })
    resizeObserver.observe(waveformRef.value)
  }

  if (timelineCanvasRef.value) {
    timelineObserver = new ResizeObserver(drawSegmentTimeline)
    timelineObserver.observe(timelineCanvasRef.value)
  }
})

onBeforeUnmount(() => {
  wavesurfer.value?.destroy()
  resizeObserver?.disconnect()
  timelineObserver?.disconnect()
})
</script>

<template>
  <div class="w-full flex flex-col gap-4">
    <!-- Loading Skeleton with Progress -->
    <div v-if="isLoading || !isReady" class="w-full bg-muted/20 rounded-lg p-8">
      <div class="text-center space-y-4">
        <UIcon name="i-lucide-loader-circle" class="size-8 text-primary animate-spin mx-auto" />
        <div class="space-y-2">
          <p class="text-sm text-muted">Loading {{ isVideo ? 'video' : 'audio' }}...</p>
        </div>
      </div>
    </div>

    <!-- Video Player Container (for video files) -->
    <div v-if="isVideo" :class="videoContainerClass" class="group">
      <div class="relative w-full bg-black rounded-lg overflow-hidden">
        <!-- Video Element -->
        <video
          ref="videoRef"
          class="w-full h-auto"
          preload="metadata"
          crossorigin="anonymous"
          @loadedmetadata="isMediaReady = true"
        />

        <!-- Center Play/Pause Button (on hover) -->
        <div
          class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-30"
        >
          <UButton
            :icon="isPlaying ? 'i-lucide-pause' : 'i-lucide-play'"
            color="white"
            size="xl"
            class="pointer-events-auto"
            :disabled="!isMediaReady"
            @click="togglePlayPause"
          />
        </div>

        <!-- Waveform Overlay (on hover) -->
        <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent py-2 pb-3 z-20 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
          <div class="relative w-full h-10 pointer-events-auto px-3">
            <div ref="waveformRef" class="w-full h-full cursor-pointer" @click="handleWaveformClick" />

            <!-- Key Moments Overlay Canvas (higher z-index to be on top) -->
            <canvas
              v-if="keyMoments && keyMoments.length > 0"
              ref="keyMomentsCanvasRef"
              class="absolute top-0 left-0 w-full h-full pointer-events-none z-10"
            />
          </div>
        </div>
      </div>

      <!-- Segment Timeline - Always Visible below video -->
      <canvas
        v-if="segments && segments.length > 0"
        ref="timelineCanvasRef"
        class="w-full cursor-pointer mt-1"
        style="height: 12px;"
        @click="handleTimelineClick"
      />

      <!-- Video Controls Bar -->
      <div v-if="!hideControls" class="flex items-center justify-between gap-3 px-1">
        <!-- Left: Playback Controls -->
        <div class="flex items-center gap-1">
          <UTooltip text="Skip Back 10s">
            <UButton
              icon="i-lucide-skip-back"
              color="neutral"
              variant="ghost"
              size="sm"
              :disabled="!isMediaReady"
              @click="skip(-10)"
            />
          </UTooltip>

          <UButton
            :icon="isPlaying ? 'i-lucide-pause' : 'i-lucide-play'"
            color="primary"
            size="md"
            :disabled="!isMediaReady"
            @click="togglePlayPause"
          />

          <UTooltip text="Skip Forward 10s">
            <UButton
              icon="i-lucide-skip-forward"
              color="neutral"
              variant="ghost"
              size="sm"
              :disabled="!isMediaReady"
              @click="skip(10)"
            />
          </UTooltip>

          <div class="text-xs text-muted ml-1">
            {{ formatTime(currentTime || 0) }} / {{ formatTime(duration) }}
          </div>
        </div>

        <!-- Right: Size, Speed, Volume -->
        <div class="flex items-center gap-1">
          <!-- Playback Speed -->
          <USelectMenu
            :model-value="playbackRate"
            :items="playbackRates.map(rate => ({ label: `${rate}x`, value: rate }))"
            @update:model-value="setPlaybackRate"
            size="sm"
          >
            <template #label>
              <div class="flex items-center gap-1.5">
                <UIcon name="i-lucide-gauge" class="size-3.5" />
                <span class="text-xs">{{ playbackRate }}x</span>
              </div>
            </template>
          </USelectMenu>

          <!-- Volume -->
          <div class="flex items-center gap-1.5">
            <UIcon
              :name="volume === 0 ? 'i-lucide-volume-x' : volume < 0.5 ? 'i-lucide-volume-1' : 'i-lucide-volume-2'"
              class="size-3.5 text-muted"
            />
            <input
              :value="volume"
              type="range"
              min="0"
              max="1"
              step="0.1"
              class="w-16 h-1 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
              @input="(e) => setVolume(parseFloat((e.target as HTMLInputElement).value))"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Audio-Only Waveform (for audio files) -->
    <div v-else class="relative w-full">
      <div ref="waveformRef" class="w-full bg-muted/20 rounded-lg cursor-pointer" :class="{ 'hidden': !isReady }" @click="handleWaveformClick" />
      <!-- Key Moments Overlay Canvas -->
      <canvas
        v-if="keyMoments && keyMoments.length > 0 && isReady"
        ref="keyMomentsCanvasRef"
        class="absolute top-0 left-0 w-full h-full pointer-events-none"
        :class="{ 'hidden': !isReady }"
      />
    </div>

    <!-- Controls below player (audio only) -->
    <div v-if="!isVideo" class="flex items-center justify-between gap-4">
      <!-- Playback Controls -->
      <div class="flex items-center gap-2">
        <!-- Skip Backward -->
        <UTooltip text="Skip Back 10s">
          <UButton
            icon="i-lucide-skip-back"
            color="neutral"
            variant="ghost"
            size="sm"
            :disabled="!isMediaReady"
            @click="skip(-10)"
          />
        </UTooltip>

        <!-- Play/Pause -->
        <UButton
          :icon="isPlaying ? 'i-lucide-pause' : 'i-lucide-play'"
          color="primary"
          size="lg"
          :disabled="!isMediaReady"
          @click="togglePlayPause"
        />

        <!-- Skip Forward -->
        <UTooltip text="Skip Forward 10s">
          <UButton
            icon="i-lucide-skip-forward"
            color="neutral"
            variant="ghost"
            size="sm"
            :disabled="!isMediaReady"
            @click="skip(10)"
          />
        </UTooltip>

        <!-- Time Display -->
        <div class="text-sm text-muted ml-2">
          {{ formatTime(currentTime || 0) }} / {{ formatTime(duration) }}
        </div>
      </div>

      <!-- Audio controls -->
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

    <!-- Segment Timeline for Audio (only show for audio files) -->
    <canvas
      v-if="!isVideo && segments && segments.length > 0"
      ref="timelineCanvasRef"
      class="w-full h-2 bg-muted/20 rounded-full cursor-pointer"
      @click="handleTimelineClick"
    />
  </div>
</template>
