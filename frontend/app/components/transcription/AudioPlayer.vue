<template>
  <div class="bg-gray-50 rounded-lg p-4">
    <!-- Audio Element (hidden) -->
    <audio
      ref="audioRef"
      :src="url"
      @timeupdate="onTimeUpdate"
      @loadedmetadata="onLoadedMetadata"
      @play="onPlay"
      @pause="onPause"
      @ended="onEnded"
      preload="metadata"
    />

    <!-- Player Controls -->
    <div class="flex items-center space-x-4">
      <!-- Play/Pause Button -->
      <UButton
        variant="outline"
        size="sm"
        @click="togglePlay"
        :disabled="!url"
      >
        <UIcon
          :name="isPlaying ? 'i-heroicons-pause-20-solid' : 'i-heroicons-play-20-solid'"
          class="w-5 h-5"
        />
      </UButton>

      <!-- Current Time -->
      <span class="text-sm font-mono text-gray-600 min-w-[60px]">
        {{ formatTime(currentTime) }}
      </span>

      <!-- Progress Bar -->
      <div class="flex-1 relative">
        <div
          class="h-2 bg-gray-200 rounded-full cursor-pointer"
          @click="seekToPosition"
          @mousemove="onProgressMouseMove"
          @mouseleave="onProgressMouseLeave"
        >
          <div
            class="h-2 bg-blue-600 rounded-full transition-all duration-100"
            :style="{ width: progressPercent + '%' }"
          />
        </div>

        <!-- Time Tooltip (on hover) -->
        <div
          v-if="showTimeTooltip"
          class="absolute -top-8 px-2 py-1 bg-gray-800 text-white text-xs rounded transform -translate-x-1/2"
          :style="{ left: tooltipPosition + '%' }"
        >
          {{ formatTime(tooltipTime) }}
        </div>
      </div>

      <!-- Duration -->
      <span class="text-sm font-mono text-gray-600 min-w-[60px]">
        {{ formatTime(duration) }}
      </span>

      <!-- Volume Control -->
      <div class="flex items-center space-x-2">
        <UButton
          variant="ghost"
          size="sm"
          @click="toggleMute"
        >
          <UIcon
            :name="isMuted ? 'i-heroicons-speaker-x-mark-20-solid' : 'i-heroicons-speaker-wave-20-solid'"
            class="w-4 h-4"
          />
        </UButton>

        <div class="w-20 relative">
          <div
            class="h-1 bg-gray-200 rounded-full cursor-pointer"
            @click="setVolume"
          >
            <div
              class="h-1 bg-gray-400 rounded-full transition-all duration-100"
              :style="{ width: volumePercent + '%' }"
            />
          </div>
        </div>
      </div>

      <!-- Playback Speed -->
      <USelectMenu
        v-model="playbackRate"
        :options="speedOptions"
        size="sm"
        class="w-20"
        @update:model-value="setPlaybackRate"
      />

      <!-- Fullscreen Toggle (if applicable) -->
      <UButton
        variant="ghost"
        size="sm"
        @click="toggleFullscreen"
        v-if="false" <!-- Disabled for now -->
      >
        <UIcon name="i-heroicons-arrows-pointing-out-20-solid" class="w-4 h-4" />
      </UButton>
    </div>

    <!-- Additional Info -->
    <div class="mt-2 flex items-center justify-between text-xs text-gray-500">
      <span v-if="url">
        {{ getFileName(url) }}
      </span>
      <span v-if="isPlaying">
        Playing • {{ formatTime(remainingTime) }} remaining
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

interface Props {
  url?: string
  duration?: number
  currentTime?: number
  autoplay?: boolean
}

interface Emits {
  'time-update': [time: number]
  'play': []
  'pause': []
  'ended': []
  'seek': [time: number]
  'loaded': [duration: number]
}

const props = withDefaults(defineProps<Props>(), {
  autoplay: false
})

const emit = defineEmits<Emits>()

// Refs
const audioRef = ref<HTMLAudioElement>()

// Reactive state
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(1)
const isMuted = ref(false)
const playbackRate = ref(1)
const showTimeTooltip = ref(false)
const tooltipTime = ref(0)
const tooltipPosition = ref(0)

// Options
const speedOptions = [
  { label: '0.5x', value: 0.5 },
  { label: '0.75x', value: 0.75 },
  { label: '1x', value: 1 },
  { label: '1.25x', value: 1.25 },
  { label: '1.5x', value: 1.5 },
  { label: '2x', value: 2 }
]

// Computed
const progressPercent = computed(() => {
  return duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0
})

const volumePercent = computed(() => {
  return (isMuted.value ? 0 : volume.value) * 100
})

const remainingTime = computed(() => {
  return Math.max(0, duration.value - currentTime.value)
})

// Methods
function togglePlay() {
  if (!audioRef.value) return

  if (isPlaying.value) {
    audioRef.value.pause()
  } else {
    audioRef.value.play()
  }
}

function toggleMute() {
  if (!audioRef.value) return

  isMuted.value = !isMuted.value
  audioRef.value.muted = isMuted.value
}

function setVolume(event: MouseEvent) {
  if (!audioRef.value) return

  const rect = (event.target as HTMLElement).getBoundingClientRect()
  const percent = (event.clientX - rect.left) / rect.width
  volume.value = Math.max(0, Math.min(1, percent))

  audioRef.value.volume = volume.value
  if (volume.value > 0) {
    isMuted.value = false
    audioRef.value.muted = false
  }
}

function setPlaybackRate(rate: number) {
  if (!audioRef.value) return

  audioRef.value.playbackRate = rate
}

function seekToPosition(event: MouseEvent) {
  if (!audioRef.value || duration.value === 0) return

  const rect = (event.target as HTMLElement).getBoundingClientRect()
  const percent = (event.clientX - rect.left) / rect.width
  const time = percent * duration.value

  audioRef.value.currentTime = time
  currentTime.value = time
  emit('seek', time)
}

function onTimeUpdate() {
  if (!audioRef.value) return

  currentTime.value = audioRef.value.currentTime
  emit('time-update', currentTime.value)
}

function onLoadedMetadata() {
  if (!audioRef.value) return

  duration.value = audioRef.value.duration
  emit('loaded', duration.value)
}

function onPlay() {
  isPlaying.value = true
  emit('play')
}

function onPause() {
  isPlaying.value = false
  emit('pause')
}

function onEnded() {
  isPlaying.value = false
  emit('ended')
}

function formatTime(seconds: number): string {
  if (!isFinite(seconds)) return '0:00'

  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function getFileName(url: string): string {
  return url.split('/').pop() || 'Audio File'
}

function toggleFullscreen() {
  // Could implement fullscreen for video files
  console.log('Fullscreen toggle')
}

// Mouse events for tooltip
function onProgressMouseMove(event: MouseEvent) {
  if (!duration.value) return

  const rect = (event.target as HTMLElement).getBoundingClientRect()
  const percent = (event.clientX - rect.left) / rect.width
  tooltipPosition.value = percent * 100
  tooltipTime.value = percent * duration.value
  showTimeTooltip.value = true
}

function onProgressMouseLeave() {
  showTimeTooltip.value = false
}

// Keyboard shortcuts
function handleKeydown(event: KeyboardEvent) {
  if (!audioRef.value) return

  switch (event.code) {
    case 'Space':
      event.preventDefault()
      togglePlay()
      break
    case 'ArrowLeft':
      event.preventDefault()
      audioRef.value.currentTime = Math.max(0, currentTime.value - 10)
      break
    case 'ArrowRight':
      event.preventDefault()
      audioRef.value.currentTime = Math.min(duration.value, currentTime.value + 10)
      break
  }
}

// Lifecycle
onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

// Watch for prop changes
watch(() => props.currentTime, (newTime) => {
  if (audioRef.value && newTime !== undefined && Math.abs(audioRef.value.currentTime - newTime) > 0.5) {
    audioRef.value.currentTime = newTime
  }
})

watch(() => props.url, () => {
  // Reset state when URL changes
  currentTime.value = 0
  duration.value = 0
  isPlaying.value = false
})
</script>

<style scoped>
/* Custom styles for the progress bar */
.h-2 {
  height: 8px;
}
</style>