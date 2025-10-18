<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount, computed, nextTick } from 'vue'
import WaveSurfer from 'wavesurfer.js'
import type { TranscriptSegment } from '~/composables/useTranscription'
import { useThrottleFn } from '@vueuse/core'

const props = withDefaults(defineProps<{
  mediaUrl: string
  mediaType?: 'video' | 'audio' // Explicitly specify media type
  transcriptionId?: string  // Optional transcription GID for fetching pre-computed waveform
  currentTime?: number
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
const isPlaying = ref(false)
const volume = ref(1)
const playbackRate = ref(1)
const timelineCanvasRef = ref<HTMLCanvasElement | null>(null)
const keyMomentsCanvasRef = ref<HTMLCanvasElement | null>(null)
const isExternalSeek = ref(false) // Track when we're seeking from external prop change

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
  if (!props.transcriptionId) {
    return null
  }

  try {
    const response = await fetch(`/api/v1/transcriptions/${encodeURIComponent(props.transcriptionId)}/waveform`)
    if (response.ok) {
      const data = await response.json()
      console.log('Fetched pre-computed waveform data:', data.peaks.length, 'peaks')
      return { peaks: data.peaks, duration: data.duration }
    } else {
      console.warn('Pre-computed waveform not available, will load media file')
      return null
    }
  } catch (error) {
    console.warn('Failed to fetch waveform data:', error)
    return null
  }
}

// Initialize WaveSurfer with video element
async function initializeWaveSurfer() {
  if (!waveformRef.value) {
    console.error('VideoPlayer: waveformRef is not available')
    return
  }

  isLoading.value = true
  loadingProgress.value = 0

  // For video, use the video element; for audio, create an audio element
  let mediaElement: HTMLMediaElement

  if (isVideo.value) {
    if (!videoRef.value) {
      console.error('VideoPlayer: videoRef is not available for video file')
      isLoading.value = false
      return
    }
    // Use existing video element
    console.log('VideoPlayer: Using video element for media')
    mediaElement = videoRef.value
  } else {
    // Create audio element for audio-only files
    console.log('VideoPlayer: Creating audio element for media')
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
    height: isVideo.value ? 40 : 80, // Compact waveform for video overlay
    normalize: true,
    backend: 'MediaElement',
    mediaControls: false,
    interact: true,
    media: mediaElement
  })

  // Enable play button immediately - browser will buffer on play
  setTimeout(() => {
    isMediaReady.value = true
  }, 100)

  // Loading progress
  wavesurfer.value.on('loading', (percent: number) => {
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
    // Only emit if this wasn't an external seek from parent
    if (!isExternalSeek.value) {
      const time = progress * duration.value
      emit('update:currentTime', time)
    } else {
      isExternalSeek.value = false
    }
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

  // Try to fetch pre-computed waveform data first
  const waveformData = await fetchWaveformData()

  if (waveformData && waveformData.peaks && waveformData.duration) {
    // Use pre-computed waveform data for instant rendering
    console.log('Using pre-computed waveform data - instant rendering!')

    // WaveSurfer v7 expects an array of channels (even for mono)
    const peaksArray = [waveformData.peaks]

    // Load media URL for playback and set the peaks manually
    wavesurfer.value.load(props.mediaUrl, peaksArray, waveformData.duration).catch((error) => {
      console.error('Failed to load media with pre-computed waveform:', error)
      isLoading.value = false
      isMediaReady.value = false
    })
  } else {
    // Fallback: Load media and generate waveform on client
    console.log('Falling back to client-side waveform generation')
    wavesurfer.value.load(props.mediaUrl).catch((error) => {
      console.error('Failed to load media:', error)
      isLoading.value = false
      isMediaReady.value = false
    })
  }
}

// Draw segment markers on waveform
function drawSegmentMarkers() {
  if (!wavesurfer.value || !props.segments) return
  // Segment markers are now handled by the timeline canvas below
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

  // For video, use a fixed height; for audio, use the element's height
  const displayHeight = isVideo.value ? 12 : canvas.getBoundingClientRect().height
  const rect = canvas.getBoundingClientRect()

  canvas.width = rect.width * window.devicePixelRatio
  canvas.height = displayHeight * window.devicePixelRatio
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

  // Clear canvas
  ctx.clearRect(0, 0, rect.width, displayHeight)

  // Draw each segment
  props.segments.forEach((segment) => {
    const left = (segment.start / duration.value) * rect.width
    const width = ((segment.end - segment.start) / duration.value) * rect.width

    // Set color based on segment type and selection
    const isSelected = segment.id === props.selectedSegmentId
    const baseColor = segment.isKeyMoment ? '#F59E0B' : '#3B82F6'
    const opacity = isSelected ? 1.0 : 0.7

    ctx.fillStyle = baseColor
    ctx.globalAlpha = opacity
    ctx.fillRect(left, 0, width, displayHeight)
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
  if (newTime !== undefined && wavesurfer.value && duration.value > 0) {
    const currentWavesurferTime = wavesurfer.value.getCurrentTime()
    const timeDiff = Math.abs(newTime - currentWavesurferTime)
    // Only seek if the difference is significant (0.5s threshold to avoid jitter)
    if (timeDiff > 0.5) {
      isExternalSeek.value = true
      const progress = newTime / duration.value
      wavesurfer.value.seekTo(progress)
    }
  }
})

// Watch for external isPlaying updates
watch(() => props.isPlaying, (shouldPlay) => {
  if (shouldPlay !== undefined && wavesurfer.value && isReady.value) {
    const currentlyPlaying = isPlaying.value
    // Only change state if different to avoid feedback loops
    if (shouldPlay !== currentlyPlaying) {
      if (shouldPlay) {
        wavesurfer.value.play()
      } else {
        wavesurfer.value.pause()
      }
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

onMounted(async () => {
  // For video files, wait for video element to be in DOM
  if (isVideo.value) {
    // Wait for next tick to ensure video element is rendered
    await nextTick()

    // Give Vue time to render the video element (short polling)
    let attempts = 0
    const maxAttempts = 10

    while (!videoRef.value && attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 50))
      attempts++
    }

    if (!videoRef.value) {
      console.error('VideoPlayer: Failed to get video element reference after', attempts, 'attempts')
      isLoading.value = false
      return
    }

    console.log('VideoPlayer: Video element is ready, initializing WaveSurfer')
    initializeWaveSurfer()
  } else {
    // For audio, initialize immediately
    initializeWaveSurfer()
  }

  // Add resize observer to redraw canvases on window resize
  await nextTick()
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
    <div v-if="isVideo" :class="videoContainerClass">
      <div class="relative w-full bg-black rounded-lg overflow-hidden group">
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
          class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
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

        <!-- Segment Timeline - Always Visible (bigger bar at bottom) -->
        <canvas
          v-if="segments && segments.length > 0"
          ref="timelineCanvasRef"
          class="absolute bottom-0 left-0 right-0 cursor-pointer z-10"
          style="height: 12px;"
          @click="handleTimelineClick"
        />

        <!-- Waveform Overlay (on hover) -->
        <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent px-3 py-2 pb-3 z-20 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
          <div class="relative w-full h-10 pointer-events-auto">
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
