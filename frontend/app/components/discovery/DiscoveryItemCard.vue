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
    return `/api/v1/discovery/items/${props.item.id}/thumbnail`
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

function titleCase(value: string) {
  return value
    .toLowerCase()
    .split('_')
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

const typeLabel = computed(() => titleCase(props.item.type))
const sourceLabel = computed(() => titleCase(props.item.source))

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
  if (props.item.call_log) {
    const caller = props.item.call_log.caller || 'Unknown caller'
    const recipient = props.item.call_log.recipient || 'Unknown recipient'
    return `Call between ${caller} and ${recipient}`
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

function formatDuration(seconds: number) {
  const total = Math.floor(seconds)
  const hours = Math.floor(total / 3600)
  const mins = Math.floor((total % 3600) / 60)
  const secs = Math.floor(total % 60)

  if (hours > 0) {
    return `${hours}h ${mins}m`
  }
  if (mins > 0) {
    return `${mins}m ${secs}s`
  }
  return `${secs}s`
}

const detailChips = computed(() => {
  const chips: Array<{ icon: string; text: string }> = []
  const { item } = props

  if (item.email_message) {
    if (item.email_message.sender) {
      chips.push({ icon: 'i-lucide-user', text: `From ${item.email_message.sender}` })
    }
    if (item.email_message.recipients?.length) {
      const to = item.email_message.recipients[0]
      const extra = item.email_message.recipients.length > 1 ? ` +${item.email_message.recipients.length - 1}` : ''
      chips.push({ icon: 'i-lucide-users', text: `To ${to}${extra}` })
    }
    if (item.email_message.sent_date) {
      chips.push({ icon: 'i-lucide-calendar', text: new Date(item.email_message.sent_date).toLocaleDateString() })
    }
  } else if (item.call_log) {
    if (item.call_log.caller) {
      chips.push({ icon: 'i-lucide-phone-incoming', text: `From ${item.call_log.caller}` })
    }
    if (item.call_log.recipient) {
      chips.push({ icon: 'i-lucide-phone-outgoing', text: `To ${item.call_log.recipient}` })
    }
    if (item.call_log.duration_seconds) {
      chips.push({ icon: 'i-lucide-timer', text: formatDuration(item.call_log.duration_seconds) })
    }
  } else if (item.social_media_post) {
    if (item.social_media_post.author) {
      chips.push({ icon: 'i-lucide-at-sign', text: `@${item.social_media_post.author}` })
    }
    if (item.social_media_post.platform) {
      chips.push({ icon: 'i-lucide-share-2', text: item.social_media_post.platform })
    }
    if (item.social_media_post.post_date) {
      chips.push({ icon: 'i-lucide-calendar', text: new Date(item.social_media_post.post_date).toLocaleDateString() })
    }
  }

  if (!item.email_message && !item.call_log && !item.social_media_post) {
    if (typeof item.item_metadata?.duration === 'number' && item.item_metadata.duration > 0) {
      chips.push({ icon: 'i-lucide-timer', text: formatDuration(item.item_metadata.duration) })
    }
    if (typeof item.item_metadata?.pages === 'number' && item.item_metadata.pages > 0) {
      chips.push({ icon: 'i-lucide-file-text', text: `${item.item_metadata.pages} pages` })
    }
    if (typeof item.item_metadata?.total_calls === 'number' && item.item_metadata.total_calls > 0) {
      chips.push({ icon: 'i-lucide-phone', text: `${item.item_metadata.total_calls} calls` })
    }
  }

  if (!item.processed) {
    chips.unshift({ icon: 'i-lucide-loader-2', text: 'Processing' })
  }

  return chips.slice(0, 3)
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
      'group relative h-full cursor-pointer border border-default/60 bg-surface transition-all hover:border-primary/50 hover:shadow-lg',
      selected ? 'ring-2 ring-primary' : ''
    ]"
    @click="handleClick"
  >
    <div v-if="viewMode !== 'list'" class="flex flex-col gap-4">
      <div class="relative aspect-video overflow-hidden rounded-xl bg-default/60">
        <div class="checkbox-area absolute left-3 top-3 z-20 rounded-md bg-surface/80 p-1 backdrop-blur">
          <UCheckbox
            :model-value="selected"
            @update:model-value="handleSelect"
          />
        </div>

        <img
          v-if="thumbnailUrl"
          :src="thumbnailUrl"
          :alt="item.original_filename"
          class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
        />
        <div v-else class="flex h-full w-full flex-col items-center justify-center gap-2 text-dimmed">
          <div class="flex h-16 w-16 items-center justify-center rounded-full bg-default/80">
            <UIcon :name="typeIcon" class="size-7" />
          </div>
          <span class="text-xs font-medium uppercase tracking-wide">{{ typeLabel }}</span>
        </div>

        <div class="absolute right-3 top-3 flex items-center gap-2">
          <UBadge :color="sourceColor" size="xs" variant="soft">
            {{ sourceLabel }}
          </UBadge>
        </div>

        <div
          v-if="isMeme"
          class="absolute bottom-3 left-3"
        >
          <UBadge color="pink" variant="solid" size="xs">
            <UIcon name="i-lucide-smile" class="mr-1 size-3" />
            Meme
          </UBadge>
        </div>

        <div
          v-if="item.type === 'VIDEO' && typeof item.item_metadata?.duration === 'number'"
          class="absolute bottom-3 right-3"
        >
          <UBadge color="neutral" variant="soft" size="xs">
            {{ formatDuration(item.item_metadata.duration) }}
          </UBadge>
        </div>

        <div
          v-if="!item.processed"
          class="absolute inset-0 flex items-center justify-center bg-surface/70 backdrop-blur"
        >
          <UIcon name="i-lucide-loader-2" class="mr-2 size-5 animate-spin text-primary" />
          <span class="text-sm font-semibold text-primary">Processing</span>
        </div>
      </div>

      <div class="flex flex-col gap-3">
        <div class="flex items-start justify-between gap-4">
          <div class="space-y-1">
            <div class="flex items-center gap-2 text-xs uppercase text-dimmed tracking-wide">
              <UIcon :name="typeIcon" class="size-3" />
              <span>{{ typeLabel }}</span>
              <span class="text-dimmed">•</span>
              <span>{{ formFactorBadge.label }}</span>
            </div>
            <h3 class="line-clamp-2 font-semibold leading-tight" :title="item.original_filename">
              {{ item.original_filename }}
            </h3>
          </div>

          <div class="flex flex-col items-end gap-2">
            <DiscoveryImportanceIndicator
              v-if="item.importance_score !== null"
              :score="item.importance_score"
              size="sm"
            />
          </div>
        </div>

        <p v-if="truncatedCaption" class="text-sm text-dimmed leading-relaxed">
          {{ truncatedCaption }}
        </p>

        <div v-if="detailChips.length > 0" class="flex flex-wrap gap-2">
          <span
            v-for="detail in detailChips"
            :key="detail.text"
            class="inline-flex items-center gap-1 rounded-full bg-default px-3 py-1 text-xs font-medium text-highlighted"
          >
            <UIcon :name="detail.icon" class="size-3 text-dimmed" />
            <span>{{ detail.text }}</span>
          </span>
        </div>

        <div v-if="item.categories && item.categories.length > 0" class="flex flex-wrap gap-1">
          <UBadge
            v-for="cat in item.categories.slice(0, 3)"
            :key="cat.id"
            :style="cat.color ? { backgroundColor: cat.color } : undefined"
            size="xs"
            variant="solid"
          >
            <UIcon v-if="cat.icon" :name="cat.icon" class="mr-1 size-3" />
            {{ cat.name }}
          </UBadge>
          <UBadge
            v-if="item.categories.length > 3"
            color="neutral"
            variant="soft"
            size="xs"
          >
            +{{ item.categories.length - 3 }}
          </UBadge>
        </div>

        <div class="flex items-center justify-between text-xs text-dimmed">
          <span>Added {{ formatDate(item.created_at) }}</span>
          <span class="flex items-center gap-2">
            <UBadge :color="sourceColor" size="xs" variant="subtle">
              {{ sourceLabel }}
            </UBadge>
            <UBadge :color="formFactorBadge.color" size="xs" variant="subtle">
              {{ formFactorBadge.label }}
            </UBadge>
          </span>
        </div>
      </div>
    </div>

    <div v-else class="flex w-full items-start gap-4">
      <div class="relative h-20 w-32 overflow-hidden rounded-lg bg-default/60">
        <div class="checkbox-area absolute left-2 top-2 z-20 rounded-md bg-surface/80 p-1 backdrop-blur">
          <UCheckbox
            :model-value="selected"
            @update:model-value="handleSelect"
          />
        </div>

        <img
          v-if="thumbnailUrl"
          :src="thumbnailUrl"
          :alt="item.original_filename"
          class="h-full w-full object-cover"
          loading="lazy"
        />
        <div v-else class="flex h-full w-full flex-col items-center justify-center gap-1 text-dimmed">
          <UIcon :name="typeIcon" class="size-6" />
          <span class="text-[10px] font-medium uppercase tracking-wide">{{ typeLabel }}</span>
        </div>

        <div
          v-if="!item.processed"
          class="absolute inset-0 flex items-center justify-center bg-surface/70 backdrop-blur"
        >
          <UIcon name="i-lucide-loader-2" class="mr-1 size-4 animate-spin text-primary" />
          <span class="text-xs font-semibold text-primary">Processing</span>
        </div>

        <div v-if="isMeme" class="absolute bottom-2 left-2">
            <UBadge color="pink" variant="solid" size="xs">
            Meme
          </UBadge>
        </div>
      </div>

      <div class="flex min-w-0 flex-1 flex-col gap-3">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 space-y-1">
            <div class="flex items-center gap-2 text-xs uppercase text-dimmed tracking-wide">
              <UIcon :name="typeIcon" class="size-3" />
              <span>{{ typeLabel }}</span>
              <span class="text-dimmed">•</span>
              <span>{{ formFactorBadge.label }}</span>
            </div>
            <h3 class="truncate font-semibold" :title="item.original_filename">
              {{ item.original_filename }}
            </h3>
          </div>

          <DiscoveryImportanceIndicator
            v-if="item.importance_score !== null"
            :score="item.importance_score"
            size="sm"
          />
        </div>

        <p v-if="caption" class="truncate text-sm text-dimmed">
          {{ caption }}
        </p>

        <div v-if="detailChips.length > 0" class="flex flex-wrap gap-2 text-xs text-highlighted">
          <span
            v-for="detail in detailChips"
            :key="detail.text"
            class="inline-flex items-center gap-1 rounded-full bg-default px-2 py-1"
          >
            <UIcon :name="detail.icon" class="size-3 text-dimmed" />
            <span>{{ detail.text }}</span>
          </span>
        </div>

        <div class="flex flex-wrap items-center gap-2 text-xs text-dimmed">
          <UBadge :color="sourceColor" size="xs" variant="subtle">
            {{ sourceLabel }}
          </UBadge>
          <UBadge :color="formFactorBadge.color" size="xs" variant="subtle">
            {{ formFactorBadge.label }}
          </UBadge>
          <span>Added {{ formatDate(item.created_at) }}</span>
        </div>
      </div>
    </div>
  </UCard>
</template>
