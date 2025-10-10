<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { TranscriptSegment, Speaker } from '~/composables/useTranscription'

const props = defineProps<{
  segments: TranscriptSegment[]
  speakers: Speaker[]
  currentTime: number
  selectedSegment?: TranscriptSegment | null
  searchQuery?: string
}>()

const emit = defineEmits<{
  'seek-to-segment': [segment: TranscriptSegment]
  'toggle-key-moment': [segmentId: string]
  'edit-segment': [segmentId: string, text: string]
  'assign-speaker': [segmentId: string, speakerId: string]
}>()

const editingSegmentId = ref<string | null>(null)
const editText = ref('')

// Auto-scroll to current segment
const segmentRefs = ref<Record<string, HTMLElement>>({})

// Watch current time and scroll to active segment
watch(() => props.currentTime, () => {
  const activeSegment = props.segments.find(s =>
    props.currentTime >= s.start && props.currentTime <= s.end
  )
  if (activeSegment && segmentRefs.value[activeSegment.id]) {
    segmentRefs.value[activeSegment.id].scrollIntoView({
      behavior: 'smooth',
      block: 'nearest'
    })
  }
})

// Get speaker for segment
function getSpeaker(speakerId?: string): Speaker | undefined {
  return props.speakers.find(s => s.id === speakerId)
}

// Check if segment is currently playing
function isActiveSegment(segment: TranscriptSegment): boolean {
  return props.currentTime >= segment.start && props.currentTime <= segment.end
}

// Format time
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

// Start editing segment
function startEdit(segment: TranscriptSegment) {
  editingSegmentId.value = segment.id
  editText.value = segment.text
}

// Save edit
function saveEdit(segmentId: string) {
  emit('edit-segment', segmentId, editText.value)
  editingSegmentId.value = null
}

// Cancel edit
function cancelEdit() {
  editingSegmentId.value = null
  editText.value = ''
}

// Highlight search query in text
function highlightText(text: string): string {
  if (!props.searchQuery) return text

  const regex = new RegExp(`(${props.searchQuery})`, 'gi')
  return text.replace(regex, '<mark class="bg-yellow-200 dark:bg-yellow-800">$1</mark>')
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="p-4 border-b border-default bg-default">
      <h3 class="font-semibold text-highlighted">Transcript</h3>
      <p class="text-sm text-muted">{{ segments.length }} segments</p>
    </div>

    <!-- Segments -->
    <div class="flex-1 overflow-y-auto p-4 space-y-3">
      <div
        v-for="segment in segments"
        :key="segment.id"
        :ref="(el) => { if (el) segmentRefs[segment.id] = el as HTMLElement }"
        class="p-4 rounded-lg transition-all cursor-pointer"
        :class="[
          isActiveSegment(segment)
            ? 'bg-primary/10 ring-2 ring-primary shadow-sm'
            : selectedSegment?.id === segment.id
              ? 'bg-muted/30 ring-1 ring-default'
              : 'bg-muted/10 hover:bg-muted/20'
        ]"
        @click="emit('seek-to-segment', segment)"
      >
        <!-- Header -->
        <div class="flex items-start justify-between gap-2 mb-2">
          <div class="flex items-center gap-2 flex-1">
            <!-- Speaker -->
            <div
              v-if="getSpeaker(segment.speaker)"
              class="px-2 py-1 rounded text-xs font-medium"
              :style="{
                backgroundColor: getSpeaker(segment.speaker)!.color + '20',
                color: getSpeaker(segment.speaker)!.color
              }"
            >
              {{ getSpeaker(segment.speaker)!.name }}
            </div>
            <UBadge v-else label="Unknown Speaker" color="neutral" size="xs" variant="soft" />

            <!-- Time -->
            <span class="text-xs text-muted">
              {{ formatTime(segment.start) }}
            </span>

            <!-- Key Moment Badge -->
            <UBadge v-if="segment.isKeyMoment" label="Key Moment" color="warning" size="xs" />

            <!-- Confidence -->
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
            <!-- Toggle Key Moment -->
            <UTooltip :text="segment.isKeyMoment ? 'Remove Key Moment' : 'Mark as Key Moment'">
              <UButton
                :icon="segment.isKeyMoment ? 'i-lucide-star' : 'i-lucide-star'"
                :color="segment.isKeyMoment ? 'warning' : 'neutral'"
                variant="ghost"
                size="xs"
                @click.stop="emit('toggle-key-moment', segment.id)"
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

            <!-- More Options -->
            <UDropdownMenu
              :items="[
                [
                  { label: 'Copy Text', icon: 'i-lucide-copy' },
                  { label: 'Add Tag', icon: 'i-lucide-tag' },
                  { label: 'Add Note', icon: 'i-lucide-sticky-note' }
                ],
                [
                  { label: 'Delete Segment', icon: 'i-lucide-trash', color: 'error' }
                ]
              ]"
            >
              <UButton
                icon="i-lucide-more-horizontal"
                color="neutral"
                variant="ghost"
                size="xs"
                @click.stop
              />
            </UDropdownMenu>
          </div>
        </div>

        <!-- Text Content -->
        <div class="mt-2">
          <div v-if="editingSegmentId === segment.id" class="space-y-2">
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
            class="text-default leading-relaxed"
            v-html="highlightText(segment.text)"
          />
        </div>

        <!-- Tags -->
        <div v-if="segment.tags && segment.tags.length > 0" class="flex flex-wrap gap-1 mt-2">
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
      <div v-if="segments.length === 0" class="text-center py-12">
        <UIcon name="i-lucide-file-text" class="size-12 text-muted mx-auto mb-4 opacity-30" />
        <p class="text-muted">No transcript segments found</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
:deep(mark) {
  @apply bg-yellow-200 dark:bg-yellow-800 rounded px-1;
}
</style>
