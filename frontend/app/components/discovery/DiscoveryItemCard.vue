<script setup lang="ts">
import type { DiscoveryItem } from '~/types/discovery'

const props = defineProps<{
  item: DiscoveryItem
  selected?: boolean
  viewMode?: 'grid' | 'list'
}>()

const emit = defineEmits<{
  click: []
  select: []
}>()

// Get thumbnail or icon based on type
const thumbnailUrl = computed(() => {
  if (props.item.type === 'PHOTO' || props.item.type === 'VIDEO') {
    // Use presigned URL from backend
    return `/api/discovery/items/${props.item.id}/thumbnail`
  }
  return null
})

const typeIcon = computed(() => {
  const icons: Record<string, string> = {
    PHOTO: 'i-lucide-image',
    VIDEO: 'i-lucide-video',
    AUDIO: 'i-lucide-mic',
    SOCIAL_MEDIA_POST: 'i-lucide-share-2',
    EMAIL: 'i-lucide-mail',
    CALL_LOG: 'i-lucide-phone',
    SMS: 'i-lucide-message-square',
    DOCUMENT: 'i-lucide-file-text'
  }
  return icons[props.item.type] || 'i-lucide-file'
})

const sourceColor = computed(() => {
  const colors: Record<string, string> = {
    CELLEBRITE: 'blue',
    PROSECUTOR: 'purple',
    EVIDENCE: 'amber',
    SURVEILLANCE: 'green',
    BODY_CAM: 'cyan',
    SOCIAL_MEDIA: 'pink',
    EMAIL_EXPORT: 'indigo',
    PHONE_RECORDS: 'orange',
    OTHER: 'neutral'
  }
  return colors[props.item.source] || 'neutral'
})

const formFactorBadge = computed(() => {
  const badges: Record<string, { label: string; color: string }> = {
    SHORT_FORM: { label: 'Short', color: 'blue' },
    LONG_FORM: { label: 'Long', color: 'purple' },
    SINGLE_ITEM: { label: 'Single', color: 'green' },
    BATCH_DUMP: { label: 'Batch', color: 'amber' }
  }
  return badges[props.item.form_factor] || { label: 'Unknown', color: 'neutral' }
})

// Get primary caption from visual content
const caption = computed(() => {
  if (props.item.visual_content && props.item.visual_content.length > 0) {
    return props.item.visual_content[0].vlm_caption
  }
  if (props.item.video_summary) {
    return props.item.video_summary.comprehensive_summary
  }
  if (props.item.social_media_post) {
    return props.item.social_media_post.content
  }
  if (props.item.email_message) {
    return props.item.email_message.subject || props.item.email_message.body
  }
  return null
})

const truncatedCaption = computed(() => {
  if (!caption.value) return null
  return caption.value.length > 120
    ? caption.value.substring(0, 120) + '...'
    : caption.value
})

// Check if item is a meme
const isMeme = computed(() => {
  return props.item.visual_content?.some(vc => vc.is_meme) || false
})

// Format date
function formatDate(dateString: string) {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`
  if (days < 365) return `${Math.floor(days / 30)} months ago`
  return date.toLocaleDateString()
}

// Handle click
function handleClick(e: MouseEvent) {
  // Don't trigger click if clicking checkbox
  if ((e.target as HTMLElement).closest('.checkbox-area')) {
    return
  }
  emit('click')
}

function handleSelect(e: Event) {
  e.stopPropagation()
  emit('select')
}
</script>

<template>
  <UCard
    :class="[
      'cursor-pointer transition-all hover:shadow-lg',
      selected ? 'ring-2 ring-primary' : '',
      viewMode === 'list' ? 'flex-row' : ''
    ]"
    @click="handleClick"
  >
    <!-- Grid View -->
    <template v-if="viewMode !== 'list'">
      <!-- Thumbnail/Icon -->
      <div class="relative aspect-video bg-elevated rounded-lg overflow-hidden mb-3">
        <!-- Thumbnail image -->
        <img
          v-if="thumbnailUrl"
          :src="thumbnailUrl"
          :alt="item.original_filename"
          class="w-full h-full object-cover"
        />
        <!-- Fallback icon -->
        <div
          v-else
          class="w-full h-full flex items-center justify-center"
        >
          <UIcon :name="typeIcon" class="size-16 text-dimmed" />
        </div>

        <!-- Selection checkbox -->
        <div class="checkbox-area absolute top-2 left-2 z-10">
          <UCheckbox
            :model-value="selected"
            @update:model-value="handleSelect"
            class="bg-white dark:bg-gray-900 rounded shadow-lg"
          />
        </div>

        <!-- Processing overlay -->
        <div
          v-if="!item.processed"
          class="absolute inset-0 bg-black/50 flex items-center justify-center"
        >
          <div class="text-center">
            <UIcon name="i-lucide-loader-2" class="size-8 text-white animate-spin mb-2" />
            <p class="text-white text-sm font-semibold">Processing...</p>
          </div>
        </div>

        <!-- Importance indicator -->
        <div class="absolute top-2 right-2">
          <DiscoveryImportanceIndicator
            v-if="item.importance_score !== null"
            :score="item.importance_score"
            size="sm"
          />
        </div>

        <!-- Meme badge -->
        <div v-if="isMeme" class="absolute bottom-2 left-2">
          <UBadge color="pink" variant="solid" size="xs">
            <UIcon name="i-lucide-smile" class="size-3 mr-1" />
            Meme
          </UBadge>
        </div>

        <!-- Video duration -->
        <div
          v-if="item.type === 'VIDEO' && item.item_metadata?.duration"
          class="absolute bottom-2 right-2"
        >
          <UBadge color="neutral" variant="solid" size="xs">
            {{ Math.floor(item.item_metadata.duration / 60) }}:{{ String(Math.floor(item.item_metadata.duration % 60)).padStart(2, '0') }}
          </UBadge>
        </div>
      </div>

      <!-- Content -->
      <div class="space-y-2">
        <!-- Filename -->
        <h3 class="font-semibold truncate" :title="item.original_filename">
          {{ item.original_filename }}
        </h3>

        <!-- Caption -->
        <p v-if="truncatedCaption" class="text-sm text-dimmed line-clamp-2">
          {{ truncatedCaption }}
        </p>

        <!-- Metadata -->
        <div class="flex items-center gap-2 flex-wrap">
          <!-- Type -->
          <UBadge :color="sourceColor" variant="subtle" size="xs">
            {{ item.source.replace(/_/g, ' ') }}
          </UBadge>

          <!-- Form factor -->
          <UBadge :color="formFactorBadge.color" variant="subtle" size="xs">
            {{ formFactorBadge.label }}
          </UBadge>
        </div>

        <!-- Categories -->
        <div v-if="item.categories && item.categories.length > 0" class="flex items-center gap-1 flex-wrap">
          <UBadge
            v-for="cat in item.categories.slice(0, 3)"
            :key="cat.category_id"
            :style="{ backgroundColor: cat.category.color || undefined }"
            size="xs"
            variant="solid"
          >
            <UIcon v-if="cat.category.icon" :name="cat.category.icon" class="size-3 mr-1" />
            {{ cat.category.name }}
          </UBadge>
          <UBadge
            v-if="item.categories.length > 3"
            color="neutral"
            variant="subtle"
            size="xs"
          >
            +{{ item.categories.length - 3 }}
          </UBadge>
        </div>

        <!-- Date -->
        <p class="text-xs text-dimmed">
          {{ formatDate(item.created_at) }}
        </p>
      </div>
    </template>

    <!-- List View -->
    <template v-else>
      <div class="flex items-center gap-4 w-full">
        <!-- Selection checkbox -->
        <div class="checkbox-area flex-shrink-0">
          <UCheckbox
            :model-value="selected"
            @update:model-value="handleSelect"
          />
        </div>

        <!-- Thumbnail -->
        <div class="relative w-24 h-16 bg-elevated rounded overflow-hidden flex-shrink-0">
          <img
            v-if="thumbnailUrl"
            :src="thumbnailUrl"
            :alt="item.original_filename"
            class="w-full h-full object-cover"
          />
          <div v-else class="w-full h-full flex items-center justify-center">
            <UIcon :name="typeIcon" class="size-8 text-dimmed" />
          </div>

          <!-- Processing overlay -->
          <div
            v-if="!item.processed"
            class="absolute inset-0 bg-black/50 flex items-center justify-center"
          >
            <UIcon name="i-lucide-loader-2" class="size-4 text-white animate-spin" />
          </div>

          <!-- Meme badge -->
          <div v-if="isMeme" class="absolute top-1 left-1">
            <UBadge color="pink" variant="solid" size="xs">
              <UIcon name="i-lucide-smile" class="size-2" />
            </UBadge>
          </div>
        </div>

        <!-- Content -->
        <div class="flex-1 min-w-0">
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1 min-w-0">
              <h3 class="font-semibold truncate">{{ item.original_filename }}</h3>
              <p v-if="caption" class="text-sm text-dimmed truncate">{{ caption }}</p>
            </div>

            <DiscoveryImportanceIndicator
              v-if="item.importance_score !== null"
              :score="item.importance_score"
              size="sm"
            />
          </div>

          <div class="flex items-center gap-2 mt-2">
            <UBadge :color="sourceColor" variant="subtle" size="xs">
              {{ item.source.replace(/_/g, ' ') }}
            </UBadge>
            <UBadge :color="formFactorBadge.color" variant="subtle" size="xs">
              {{ formFactorBadge.label }}
            </UBadge>
            <span class="text-xs text-dimmed">{{ formatDate(item.created_at) }}</span>
          </div>
        </div>
      </div>
    </template>
  </UCard>
</template>
