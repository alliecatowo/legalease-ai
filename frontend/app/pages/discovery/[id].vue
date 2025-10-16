<script setup lang="ts">
import type { DiscoveryItem, DiscoveryItemPreview } from '~/types/discovery'

definePageMeta({
  title: 'Discovery Item',
  layout: 'default'
})

const route = useRoute()
const router = useRouter()
const toast = useToast()

const itemId = computed(() => parseInt(route.params.id as string))

// State
const item = ref<DiscoveryItem | null>(null)
const loading = ref(false)
const showCategoryModal = ref(false)
const showEditModal = ref(false)
const preview = ref<DiscoveryItemPreview | null>(null)
const previewLoading = ref(false)
const previewError = ref<string | null>(null)

const downloadUrl = computed(() => item.value ? `/api/v1/discovery/items/${item.value.id}/download` : null)

// Fetch item details
async function fetchItem() {
  loading.value = true
  try {
    const response = await $fetch(`/api/v1/discovery/items/${itemId.value}`)
    item.value = response
    await fetchPreview()
  } catch (error) {
    console.error('Error fetching item:', error)
    toast.add({
      title: 'Error',
      description: 'Failed to load item details',
      color: 'red'
    })
  } finally {
    loading.value = false
  }
}

async function fetchPreview() {
  if (!item.value) return

  previewLoading.value = true
  previewError.value = null
  preview.value = null

  try {
    const response = await $fetch<DiscoveryItemPreview>(`/api/v1/discovery/items/${itemId.value}/preview`)
    preview.value = response
  } catch (error) {
    console.error('Error fetching item preview:', error)
    previewError.value = 'Preview is not available yet for this file.'
  } finally {
    previewLoading.value = false
  }
}

// Delete item
async function deleteItem() {
  if (!confirm('Are you sure you want to delete this item?')) return

  try {
    await $fetch(`/api/v1/discovery/items/${itemId.value}`, {
      method: 'DELETE'
    })

    toast.add({
      title: 'Success',
      description: 'Item deleted successfully',
      color: 'green'
    })

    router.push('/discovery')
  } catch (error) {
    toast.add({
      title: 'Error',
      description: 'Failed to delete item',
      color: 'red'
    })
  }
}

// Add category
async function addCategory(categoryId: number) {
  try {
    await $fetch(`/api/v1/discovery/items/${itemId.value}/categories/${categoryId}`, {
      method: 'POST'
    })

    toast.add({
      title: 'Success',
      description: 'Category added',
      color: 'green'
    })

    fetchItem()
    showCategoryModal.value = false
  } catch (error) {
    toast.add({
      title: 'Error',
      description: 'Failed to add category',
      color: 'red'
    })
  }
}

// Remove category
async function removeCategory(categoryId: number) {
  try {
    await $fetch(`/api/v1/discovery/items/${itemId.value}/categories/${categoryId}`, {
      method: 'DELETE'
    })

    toast.add({
      title: 'Success',
      description: 'Category removed',
      color: 'green'
    })

    fetchItem()
  } catch (error) {
    toast.add({
      title: 'Error',
      description: 'Failed to remove category',
      color: 'red'
    })
  }
}

// Get type icon
function getTypeIcon(type: string) {
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

// Format file size
function formatFileSize(bytes: number) {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

watch(itemId, () => {
  fetchItem()
}, { immediate: true })

function formatCallDuration(duration?: number | null) {
  if (!duration) return 'Unknown'
  const hours = Math.floor(duration / 3600)
  const minutes = Math.floor((duration % 3600) / 60)
  const seconds = Math.floor(duration % 60)
  const parts: string[] = []

  if (hours > 0) parts.push(`${hours}h`)
  if (minutes > 0) parts.push(`${minutes}m`)
  parts.push(`${seconds}s`)

  return parts.join(' ')
}

function formatTimestamp(seconds: number) {
  if (!Number.isFinite(seconds)) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function formatLabel(value?: string | null) {
  if (!value) return 'Unknown'
  return value
    .toLowerCase()
    .split('_')
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar :title="item?.original_filename || 'Loading...'">
        <template #leading>
          <UButton
            icon="i-lucide-arrow-left"
            color="neutral"
            variant="ghost"
            square
            @click="router.push('/discovery')"
          />
        </template>

        <template #trailing>
          <div class="flex items-center gap-2">
            <UButton
              v-if="downloadUrl"
              label="Download"
              icon="i-lucide-download"
              color="primary"
              :href="downloadUrl"
              download
            />
            <UButton
              label="Add Category"
              icon="i-lucide-tag"
              color="neutral"
              variant="outline"
              @click="showCategoryModal = true"
            />
            <UButton
              label="Delete"
              icon="i-lucide-trash"
              color="red"
              variant="outline"
              @click="deleteItem"
            />
          </div>
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <!-- Loading state -->
      <div v-if="loading" class="flex items-center justify-center h-64">
        <UIcon name="i-lucide-loader-2" class="size-8 animate-spin text-primary" />
      </div>

      <!-- Content -->
      <div v-else-if="item" class="p-6 space-y-6">
        <!-- Item Overview -->
        <UCard>
          <div class="flex items-start gap-6">
            <!-- Icon -->
            <div class="flex-shrink-0">
              <div class="w-20 h-20 rounded-lg bg-primary/10 flex items-center justify-center">
                <UIcon :name="getTypeIcon(item.type)" class="size-10 text-primary" />
              </div>
            </div>

            <!-- Details -->
            <div class="flex-1 min-w-0">
              <h2 class="text-2xl font-bold mb-2">{{ item.original_filename }}</h2>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p class="text-dimmed">Type</p>
                  <p class="font-semibold">{{ formatLabel(item.type) }}</p>
                </div>
                <div>
                  <p class="text-dimmed">Source</p>
                  <p class="font-semibold">{{ formatLabel(item.source) }}</p>
                </div>
                <div>
                  <p class="text-dimmed">Form Factor</p>
                  <p class="font-semibold">{{ formatLabel(item.form_factor) }}</p>
                </div>
                <div>
                  <p class="text-dimmed">Status</p>
                  <UBadge
                    :label="item.processed ? 'Processed' : 'Processing'"
                    :color="item.processed ? 'green' : 'amber'"
                    size="sm"
                  />
                </div>
              </div>

              <!-- Importance -->
              <div class="mt-4">
                <p class="text-sm text-dimmed mb-1">Importance Score</p>
                <DiscoveryImportanceIndicator
                  v-if="item.importance_score !== null"
                  :score="item.importance_score"
                />
              </div>

              <!-- Categories -->
              <div class="mt-4">
                <p class="text-sm text-dimmed mb-2">Categories</p>
                <div v-if="item.categories && item.categories.length > 0" class="flex flex-wrap gap-2">
                  <UBadge
                    v-for="category in item.categories"
                    :key="category.id"
                    :label="category.name"
                    color="primary"
                    variant="subtle"
                    size="sm"
                  >
                    <template #trailing>
                      <UIcon
                        name="i-lucide-x"
                        class="size-3 cursor-pointer"
                        @click="removeCategory(category.id)"
                      />
                    </template>
                  </UBadge>
                </div>
                <p v-else class="text-sm text-dimmed">No categories assigned</p>
              </div>
            </div>
          </div>
        </UCard>

        <DiscoveryItemViewer
          :item="item"
          :preview="preview"
          :loading="previewLoading"
          :error="previewError"
          :download-url="downloadUrl || null"
        />

        <!-- Visual Content -->
        <UCard v-if="item.visual_content && item.visual_content.length > 0">
          <template #header>
            <h3 class="font-semibold">Visual Analysis</h3>
          </template>

          <div class="space-y-4">
            <div
              v-for="visual in item.visual_content"
              :key="visual.id"
              class="space-y-4 rounded-lg border border-default p-4"
            >
              <div class="flex flex-wrap items-center gap-3 text-xs text-dimmed">
                <span v-if="visual.timestamp_in_video != null">Timestamp: {{ Number(visual.timestamp_in_video).toFixed(1) }}s</span>
                <span v-if="visual.frame_number != null">Frame #{{ visual.frame_number }}</span>
                <UBadge
                  v-if="visual.is_meme"
                  label="Meme detected"
                  color="pink"
                  size="xs"
                />
              </div>

              <div v-if="visual.vlm_caption" class="space-y-1">
                <p class="text-sm font-semibold text-dimmed">Caption</p>
                <p class="text-sm leading-relaxed text-highlighted">{{ visual.vlm_caption }}</p>
              </div>

              <div v-if="visual.detected_objects && visual.detected_objects.length > 0" class="space-y-2">
                <p class="text-sm font-semibold text-dimmed">Objects Detected</p>
                <div class="flex flex-wrap gap-2">
                  <UBadge
                    v-for="(obj, idx) in visual.detected_objects"
                    :key="idx"
                    :label="obj"
                    color="neutral"
                    size="xs"
                  />
                </div>
              </div>

              <div v-if="visual.detected_scenes && visual.detected_scenes.length > 0" class="space-y-2">
                <p class="text-sm font-semibold text-dimmed">Scenes</p>
                <div class="flex flex-wrap gap-2">
                  <UBadge
                    v-for="(scene, idx) in visual.detected_scenes"
                    :key="idx"
                    :label="scene"
                    color="blue"
                    size="xs"
                    variant="subtle"
                  />
                </div>
              </div>

              <div v-if="visual.detected_activities && visual.detected_activities.length > 0" class="space-y-2">
                <p class="text-sm font-semibold text-dimmed">Activities</p>
                <div class="flex flex-wrap gap-2">
                  <UBadge
                    v-for="(activity, idx) in visual.detected_activities"
                    :key="idx"
                    :label="activity"
                    color="emerald"
                    size="xs"
                    variant="subtle"
                  />
                </div>
              </div>

              <div v-if="visual.sensitive_flags && Object.keys(visual.sensitive_flags).length > 0" class="space-y-2">
                <p class="text-sm font-semibold text-dimmed">Sensitive Flags</p>
                <div class="flex flex-wrap gap-2">
                  <UBadge
                    v-for="(value, key) in visual.sensitive_flags"
                    :key="key"
                    :label="`${key}: ${value ? 'Yes' : 'No'}`"
                    color="amber"
                    size="xs"
                  />
                </div>
              </div>
            </div>
          </div>
        </UCard>

        <!-- Video Summary -->
        <UCard v-if="item.video_summary">
          <template #header>
            <h3 class="font-semibold">Video Summary</h3>
          </template>

          <div class="space-y-4">
            <div v-if="item.video_summary.comprehensive_summary" class="space-y-2">
              <p class="text-sm font-semibold text-dimmed">Overview</p>
              <p class="text-sm leading-relaxed text-highlighted">
                {{ item.video_summary.comprehensive_summary }}
              </p>
            </div>

            <div v-if="item.video_summary.key_moments && item.video_summary.key_moments.length > 0" class="space-y-2">
              <p class="text-sm font-semibold text-dimmed">Key Moments</p>
              <div class="space-y-2">
                <div
                  v-for="(moment, index) in item.video_summary.key_moments"
                  :key="index"
                  class="flex items-start gap-3 rounded-lg border border-default/70 bg-default/40 p-3"
                >
                  <UBadge color="neutral" size="xs" variant="soft">
                    {{ formatTimestamp(moment.timestamp) }}
                  </UBadge>
                  <div class="space-y-1">
                    <p class="text-sm font-medium text-highlighted">{{ moment.description }}</p>
                    <p class="text-xs text-dimmed">Importance {{ ((moment.importance ?? 0) * 100).toFixed(0) }}%</p>
                  </div>
                </div>
              </div>
            </div>

            <div class="grid gap-3 md:grid-cols-2">
              <div v-if="item.video_summary.visual_summary" class="space-y-2">
                <p class="text-sm font-semibold text-dimmed">Visual Summary</p>
                <p class="text-sm text-highlighted leading-relaxed">
                  {{ item.video_summary.visual_summary }}
                </p>
              </div>
              <div v-if="item.video_summary.audio_summary" class="space-y-2">
                <p class="text-sm font-semibold text-dimmed">Audio Summary</p>
                <p class="text-sm text-highlighted leading-relaxed">
                  {{ item.video_summary.audio_summary }}
                </p>
              </div>
            </div>
          </div>
        </UCard>

        <!-- Email Content -->
        <UCard v-if="item.email_message">
          <template #header>
            <h3 class="font-semibold">Email Details</h3>
          </template>

          <div class="space-y-3">
            <div>
              <p class="text-sm font-semibold text-dimmed">From</p>
              <p>{{ item.email_message.sender || 'Unknown sender' }}</p>
            </div>
            <div>
              <p class="text-sm font-semibold text-dimmed">To</p>
              <p>{{ item.email_message.recipients?.join(', ') || 'No recipients listed' }}</p>
            </div>
            <div v-if="item.email_message.cc?.length">
              <p class="text-sm font-semibold text-dimmed">CC</p>
              <p>{{ item.email_message.cc.join(', ') }}</p>
            </div>
            <div>
              <p class="text-sm font-semibold text-dimmed">Subject</p>
              <p>{{ item.email_message.subject || 'No subject' }}</p>
            </div>
            <div v-if="item.email_message.body">
              <p class="text-sm font-semibold text-dimmed">Body</p>
              <div class="p-3 rounded bg-elevated">
                <pre class="text-sm whitespace-pre-wrap">{{ item.email_message.body }}</pre>
              </div>
            </div>
          </div>
        </UCard>

        <!-- Call Log -->
        <UCard v-if="item.call_log">
          <template #header>
            <h3 class="font-semibold">Call Log</h3>
          </template>

          <div class="space-y-3">
            <div>
              <p class="text-sm font-semibold text-dimmed">Call Type</p>
              <UBadge
                :label="item.call_log.call_type"
                color="neutral"
                size="sm"
                variant="subtle"
              />
            </div>
            <div v-if="item.call_log.caller">
              <p class="text-sm font-semibold text-dimmed">Caller</p>
              <p>{{ item.call_log.caller }}</p>
            </div>
            <div v-if="item.call_log.recipient">
              <p class="text-sm font-semibold text-dimmed">Recipient</p>
              <p>{{ item.call_log.recipient }}</p>
            </div>
            <div v-if="item.call_log.duration_seconds != null">
              <p class="text-sm font-semibold text-dimmed">Duration</p>
              <p>{{ formatCallDuration(item.call_log.duration_seconds) }}</p>
            </div>
            <div v-if="item.call_log.call_date">
              <p class="text-sm font-semibold text-dimmed">Call Date</p>
              <p>{{ new Date(item.call_log.call_date).toLocaleString() }}</p>
            </div>
            <div v-if="item.call_log.notes">
              <p class="text-sm font-semibold text-dimmed">Notes</p>
              <p class="whitespace-pre-wrap text-sm">{{ item.call_log.notes }}</p>
            </div>
          </div>
        </UCard>

        <!-- Social Media Post -->
        <UCard v-if="item.social_media_post">
          <template #header>
            <h3 class="font-semibold">Social Media Post</h3>
          </template>

          <div class="space-y-3">
            <div>
              <p class="text-sm font-semibold text-dimmed">Platform</p>
              <p>{{ item.social_media_post.platform }}</p>
            </div>
            <div v-if="item.social_media_post.author">
              <p class="text-sm font-semibold text-dimmed">Author</p>
              <p>{{ item.social_media_post.author }}</p>
            </div>
            <div v-if="item.social_media_post.content">
              <p class="text-sm font-semibold text-dimmed">Content</p>
              <div class="p-3 rounded bg-elevated">
                <p class="whitespace-pre-wrap">{{ item.social_media_post.content }}</p>
              </div>
            </div>
            <div v-if="item.social_media_post.engagement_metrics" class="grid grid-cols-3 gap-4">
              <div v-for="(value, key) in item.social_media_post.engagement_metrics" :key="key">
                <p class="text-sm font-semibold text-dimmed">{{ key }}</p>
                <p>{{ value }}</p>
              </div>
            </div>
          </div>
        </UCard>

        <!-- Metadata -->
        <UCard v-if="item.item_metadata && Object.keys(item.item_metadata).length > 0">
          <template #header>
            <h3 class="font-semibold">Additional Metadata</h3>
          </template>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div v-for="(value, key) in item.item_metadata" :key="key">
              <p class="text-sm font-semibold text-dimmed">{{ key }}</p>
              <p class="font-mono text-sm">{{ typeof value === 'object' ? JSON.stringify(value) : value }}</p>
            </div>
          </div>
        </UCard>

        <!-- Timestamps -->
        <UCard>
          <template #header>
            <h3 class="font-semibold">Timestamps</h3>
          </template>

          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p class="text-dimmed">Created</p>
              <p>{{ new Date(item.created_at).toLocaleString() }}</p>
            </div>
            <div>
              <p class="text-dimmed">Updated</p>
              <p>{{ new Date(item.updated_at).toLocaleString() }}</p>
            </div>
          </div>
        </UCard>
      </div>

      <!-- Error state -->
      <div v-else class="flex flex-col items-center justify-center h-64">
        <UIcon name="i-lucide-alert-circle" class="size-16 text-red-500 mb-4" />
        <h3 class="text-xl font-semibold mb-2">Item not found</h3>
        <UButton label="Go Back" @click="router.push('/discovery')" />
      </div>
    </template>
  </UDashboardPanel>

  <!-- Category Modal -->
  <UModal v-model:open="showCategoryModal" title="Add Category">
    <template #body>
      <DiscoveryCategorySelector @select="addCategory" />
    </template>
  </UModal>
</template>
