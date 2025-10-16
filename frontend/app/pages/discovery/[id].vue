<script setup lang="ts">
import type { DiscoveryItem } from '~/types/discovery'

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

// Fetch item details
async function fetchItem() {
  loading.value = true
  try {
    const response = await $fetch(`/api/v1/discovery/items/${itemId.value}`)
    item.value = response
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

onMounted(() => {
  fetchItem()
})
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
                  <p class="font-semibold">{{ item.type }}</p>
                </div>
                <div>
                  <p class="text-dimmed">Source</p>
                  <p class="font-semibold">{{ item.source }}</p>
                </div>
                <div>
                  <p class="text-dimmed">Form Factor</p>
                  <p class="font-semibold">{{ item.form_factor }}</p>
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
                  v-if="item.importance_score"
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

        <!-- Visual Content -->
        <UCard v-if="item.visual_content && item.visual_content.length > 0">
          <template #header>
            <h3 class="font-semibold">Visual Analysis</h3>
          </template>

          <div class="space-y-4">
            <div
              v-for="visual in item.visual_content"
              :key="visual.id"
              class="p-4 rounded-lg border border-default"
            >
              <!-- Caption -->
              <div v-if="visual.caption" class="mb-3">
                <p class="text-sm font-semibold text-dimmed mb-1">Caption</p>
                <p>{{ visual.caption }}</p>
              </div>

              <!-- Objects -->
              <div v-if="visual.objects_detected && visual.objects_detected.length > 0" class="mb-3">
                <p class="text-sm font-semibold text-dimmed mb-2">Objects Detected</p>
                <div class="flex flex-wrap gap-2">
                  <UBadge
                    v-for="(obj, idx) in visual.objects_detected"
                    :key="idx"
                    :label="obj"
                    color="neutral"
                    size="xs"
                  />
                </div>
              </div>

              <!-- OCR Text -->
              <div v-if="visual.ocr_text" class="mb-3">
                <p class="text-sm font-semibold text-dimmed mb-1">Text (OCR)</p>
                <p class="text-sm">{{ visual.ocr_text }}</p>
              </div>

              <!-- Flags -->
              <div class="flex gap-2">
                <UBadge
                  v-if="visual.is_meme"
                  label="Meme"
                  color="purple"
                  size="xs"
                />
                <UBadge
                  v-if="visual.contains_people"
                  label="Contains People"
                  color="blue"
                  size="xs"
                />
                <UBadge
                  v-if="visual.contains_faces"
                  label="Contains Faces"
                  color="blue"
                  size="xs"
                />
              </div>
            </div>
          </div>
        </UCard>

        <!-- Email Content -->
        <UCard v-if="item.email">
          <template #header>
            <h3 class="font-semibold">Email Details</h3>
          </template>

          <div class="space-y-3">
            <div>
              <p class="text-sm font-semibold text-dimmed">From</p>
              <p>{{ item.email.from_address }}</p>
            </div>
            <div>
              <p class="text-sm font-semibold text-dimmed">To</p>
              <p>{{ item.email.to_addresses }}</p>
            </div>
            <div v-if="item.email.cc_addresses">
              <p class="text-sm font-semibold text-dimmed">CC</p>
              <p>{{ item.email.cc_addresses }}</p>
            </div>
            <div>
              <p class="text-sm font-semibold text-dimmed">Subject</p>
              <p>{{ item.email.subject }}</p>
            </div>
            <div v-if="item.email.body">
              <p class="text-sm font-semibold text-dimmed">Body</p>
              <div class="p-3 rounded bg-elevated">
                <pre class="text-sm whitespace-pre-wrap">{{ item.email.body }}</pre>
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
              <p class="text-sm font-semibold text-dimmed">Phone Number</p>
              <p>{{ item.call_log.phone_number }}</p>
            </div>
            <div v-if="item.call_log.contact_name">
              <p class="text-sm font-semibold text-dimmed">Contact Name</p>
              <p>{{ item.call_log.contact_name }}</p>
            </div>
            <div>
              <p class="text-sm font-semibold text-dimmed">Direction</p>
              <UBadge
                :label="item.call_log.direction"
                :color="item.call_log.direction === 'INCOMING' ? 'blue' : 'green'"
                size="sm"
              />
            </div>
            <div>
              <p class="text-sm font-semibold text-dimmed">Duration</p>
              <p>{{ Math.floor(item.call_log.duration / 60) }}m {{ item.call_log.duration % 60 }}s</p>
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
