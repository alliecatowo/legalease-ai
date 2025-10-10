<template>
  <UCard>
    <template #header>
      <h3 class="text-lg font-semibold">Audio Player</h3>
    </template>

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
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <!-- Play/Pause Button -->
        <UButton
          variant="outline"
          size="lg"
          @click="togglePlay"
          :disabled="!url"
          :color="isPlaying ? 'primary' : 'gray'"
        >
          <UIcon
            :name="isPlaying ? 'i-heroicons-pause-20-solid' : 'i-heroicons-play-20-solid'"
            class="w-6 h-6"
          />
        </UButton>

        <!-- Time Display -->
        <div class="flex items-center space-x-2">
          <UBadge variant="outline" size="sm">
            {{ formatTime(currentTime) }}
          </UBadge>
          <span class="text-muted">/</span>
          <UBadge variant="outline" size="sm">
            {{ formatTime(duration) }}
          </UBadge>
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="space-y-2">
        <USlider
          v-model="currentTime"
          :min="0"
          :max="duration"
          :step="0.1"
          size="sm"
          @update:model-value="seekToTime"
          tooltip
        />

      </div>

      <!-- Volume & Speed Controls -->
      <div class="flex items-center justify-between">
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

          <USlider
            v-model="volume"
            :min="0"
            :max="1"
            :step="0.1"
            size="xs"
            class="w-16"
            @update:model-value="setVolume"
          />
        </div>

        <USelectMenu
          v-model="playbackRate"
          :options="speedOptions"
          size="sm"
          class="w-24"
          @update:model-value="setPlaybackRate"
        />
      </div>
    </div>

    <!-- Additional Info -->
    <template #footer>
      <div class="flex items-center justify-between text-xs text-muted">
        <span v-if="url">
          {{ getFileName(url) }}
        </span>
        <span v-if="isPlaying">
          Playing • {{ formatTime(remainingTime) }} remaining
        </span>
      </div>
    </template>
  </UCard>
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