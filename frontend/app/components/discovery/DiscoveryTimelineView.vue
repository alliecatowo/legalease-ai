<script setup lang="ts">
import type { DiscoveryItem } from '~/types/discovery'

const props = defineProps<{
  items: DiscoveryItem[]
}>()

const emit = defineEmits<{
  viewItem: [itemId: number]
}>()

// Group items by date
const groupedItems = computed(() => {
  const groups: Record<string, DiscoveryItem[]> = {}

  props.items.forEach(item => {
    const date = new Date(item.created_at).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })

    if (!groups[date]) {
      groups[date] = []
    }
    groups[date].push(item)
  })

  return groups
})

// Get sorted dates
const sortedDates = computed(() => {
  return Object.keys(groupedItems.value).sort((a, b) => {
    return new Date(b).getTime() - new Date(a).getTime()
  })
})

// Get icon for item type
function getTypeIcon(type: string): string {
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
  return icons[type] || 'i-lucide-file'
}

// Get caption
function getCaption(item: DiscoveryItem): string | null {
  if (item.visual_content && item.visual_content.length > 0) {
    return item.visual_content[0].vlm_caption
  }
  if (item.video_summary) {
    return item.video_summary.comprehensive_summary
  }
  if (item.social_media_post) {
    return item.social_media_post.content
  }
  if (item.email_message) {
    return item.email_message.subject || item.email_message.body
  }
  return null
}

function formatTime(dateString: string): string {
  return new Date(dateString).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<template>
  <div class="space-y-8">
    <!-- Timeline -->
    <div
      v-for="date in sortedDates"
      :key="date"
      class="relative"
    >
      <!-- Date header -->
      <div class="sticky top-0 z-10 bg-background py-4 mb-6">
        <div class="flex items-center gap-4">
          <div class="h-px flex-1 bg-default" />
          <h2 class="text-lg font-semibold px-4 bg-elevated rounded-full border border-default">
            {{ date }}
          </h2>
          <div class="h-px flex-1 bg-default" />
        </div>
      </div>

      <!-- Items for this date -->
      <div class="space-y-4 relative">
        <!-- Vertical timeline line -->
        <div class="absolute left-8 top-0 bottom-0 w-0.5 bg-default" />

        <!-- Timeline items -->
        <div
          v-for="(item, index) in groupedItems[date]"
          :key="item.id"
          class="relative pl-20"
        >
          <!-- Timeline dot -->
          <div
            class="absolute left-6 w-5 h-5 rounded-full border-4 border-background z-10"
            :class="[
              item.importance_score && item.importance_score >= 0.8 ? 'bg-red-500' :
              item.importance_score && item.importance_score >= 0.6 ? 'bg-amber-500' :
              item.importance_score && item.importance_score >= 0.4 ? 'bg-blue-500' :
              'bg-green-500'
            ]"
          />

          <!-- Time -->
          <div class="absolute left-0 top-1 text-xs text-dimmed font-mono">
            {{ formatTime(item.created_at) }}
          </div>

          <!-- Content card -->
          <UCard
            class="cursor-pointer hover:shadow-lg transition-all"
            @click="emit('viewItem', item.id)"
          >
            <div class="flex gap-4">
              <!-- Thumbnail/Icon -->
              <div class="w-32 h-24 bg-elevated rounded overflow-hidden flex-shrink-0">
                <img
                  v-if="item.type === 'PHOTO' || item.type === 'VIDEO'"
                  :src="`/api/discovery/items/${item.id}/thumbnail`"
                  :alt="item.original_filename"
                  class="w-full h-full object-cover"
                />
                <div v-else class="w-full h-full flex items-center justify-center">
                  <UIcon :name="getTypeIcon(item.type)" class="size-12 text-dimmed" />
                </div>

                <!-- Processing overlay -->
                <div
                  v-if="!item.processed"
                  class="absolute inset-0 bg-black/50 flex items-center justify-center"
                >
                  <UIcon name="i-lucide-loader-2" class="size-6 text-white animate-spin" />
                </div>
              </div>

              <!-- Content -->
              <div class="flex-1 min-w-0">
                <div class="flex items-start justify-between gap-4 mb-2">
                  <div class="flex-1 min-w-0">
                    <h3 class="font-semibold truncate">{{ item.original_filename }}</h3>
                    <div class="flex items-center gap-2 mt-1">
                      <UBadge size="xs" variant="subtle">
                        {{ item.type.replace(/_/g, ' ') }}
                      </UBadge>
                      <UBadge size="xs" variant="subtle" color="blue">
                        {{ item.source.replace(/_/g, ' ') }}
                      </UBadge>
                    </div>
                  </div>

                  <!-- Importance indicator -->
                  <DiscoveryImportanceIndicator
                    v-if="item.importance_score !== null"
                    :score="item.importance_score"
                    size="sm"
                  />
                </div>

                <!-- Caption -->
                <p v-if="getCaption(item)" class="text-sm text-dimmed line-clamp-2 mt-2">
                  {{ getCaption(item) }}
                </p>

                <!-- Categories -->
                <div
                  v-if="item.categories && item.categories.length > 0"
                  class="flex items-center gap-1 mt-2 flex-wrap"
                >
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

                <!-- Key moments for videos -->
                <div
                  v-if="item.video_summary?.key_moments && item.video_summary.key_moments.length > 0"
                  class="mt-3 space-y-1"
                >
                  <p class="text-xs font-semibold text-dimmed uppercase">Key Moments:</p>
                  <div class="space-y-1">
                    <div
                      v-for="(moment, i) in item.video_summary.key_moments.slice(0, 2)"
                      :key="i"
                      class="text-xs flex gap-2"
                    >
                      <span class="font-mono text-dimmed">
                        {{ Math.floor(moment.timestamp / 60) }}:{{ String(Math.floor(moment.timestamp % 60)).padStart(2, '0') }}
                      </span>
                      <span class="flex-1">{{ moment.description }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </UCard>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-if="sortedDates.length === 0"
      class="text-center py-16"
    >
      <UIcon name="i-lucide-clock" class="size-16 text-dimmed mb-4" />
      <h3 class="text-xl font-semibold mb-2">No timeline data</h3>
      <p class="text-dimmed">Upload some items to see them on the timeline</p>
    </div>
  </div>
</template>
