<script setup lang="ts">
import type { DiscoveryItem, DiscoveryItemType, DiscoveryItemSource, DiscoveryItemFormFactor } from '~/types/discovery'

definePageMeta({
  title: 'Discovery',
  layout: 'default'
})

const route = useRoute()
const router = useRouter()
const toast = useToast()

// View mode state
const viewMode = ref<'grid' | 'list' | 'timeline'>('grid')

// Filter state
const filters = reactive({
  search: '',
  type: null as DiscoveryItemType | null,
  source: null as DiscoveryItemSource | null,
  formFactor: null as DiscoveryItemFormFactor | null,
  minImportance: null as number | null,
  maxImportance: null as number | null,
  startDate: null as string | null,
  endDate: null as string | null,
  categories: [] as number[],
  processedOnly: false,
  memeFilter: null as boolean | null
})

// Pagination
const page = ref(1)
const limit = ref(50)

// Data state
const items = ref<DiscoveryItem[]>([])
const totalItems = ref(0)
const loading = ref(false)
const stats = ref({
  total: 0,
  highImportance: 0,
  processing: 0,
  storageUsed: 0
})

// Selection state
const selectedItems = ref<Set<number>>(new Set())
const bulkActionOpen = ref(false)

const POLL_INTERVAL = 15000
let pollTimer: ReturnType<typeof setInterval> | null = null

// Fetch discovery items
async function fetchItems(options: { silent?: boolean } = {}) {
  const { silent = false } = options

  if (!silent) {
    loading.value = true
  }

  try {
    const params = new URLSearchParams()

    if (filters.search) params.append('search', filters.search)
    if (filters.type) params.append('type', filters.type)
    if (filters.source) params.append('source', filters.source)
    if (filters.formFactor) params.append('form_factor', filters.formFactor)
    if (filters.minImportance !== null) params.append('min_importance', filters.minImportance.toString())
    if (filters.maxImportance !== null) params.append('max_importance', filters.maxImportance.toString())
    if (filters.startDate) params.append('start_date', filters.startDate)
    if (filters.endDate) params.append('end_date', filters.endDate)
    if (filters.processedOnly) params.append('processed', 'true')

    params.append('skip', ((page.value - 1) * limit.value).toString())
    params.append('limit', limit.value.toString())

    const response = await $fetch(`/api/v1/discovery/items?${params.toString()}`)

    const filteredItems = response.items
      .filter(item => {
        if (filters.categories.length > 0) {
          return item.categories?.some(cat => filters.categories.includes(cat.id))
        }
        return true
      })
      .filter(item => {
        if (filters.memeFilter === null) return true
        return item.visual_content?.some(vc => vc.is_meme === filters.memeFilter)
      })

    items.value = filteredItems
    totalItems.value = response.total
  } catch (error) {
    console.error('Error fetching discovery items:', error)
    toast.add({
      title: 'Error',
      description: 'Failed to load discovery items',
      color: 'red'
    })
  } finally {
    if (!silent) {
      loading.value = false
    }
  }
}

// Fetch stats
async function fetchStats() {
  try {
    const response = await $fetch('/api/v1/discovery/stats')
    stats.value = response
  } catch (error) {
    console.error('Error fetching stats:', error)
  }
}

// Watch filters and refetch
watch([filters, page], () => {
  fetchItems()
}, { deep: true })

// Initial load
onMounted(() => {
  fetchItems()
  fetchStats()

  pollTimer = setInterval(async () => {
    await fetchStats()
    if (!loading.value && items.value.some(item => !item.processed)) {
      await fetchItems({ silent: true })
    }
  }, POLL_INTERVAL)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})

// Bulk selection
function toggleSelection(itemId: number) {
  if (selectedItems.value.has(itemId)) {
    selectedItems.value.delete(itemId)
  } else {
    selectedItems.value.add(itemId)
  }
}

function selectAll() {
  items.value.forEach(item => selectedItems.value.add(item.id))
}

function clearSelection() {
  selectedItems.value.clear()
  bulkActionOpen.value = false
}

function extractFilenameFromDisposition(disposition: string | null | undefined, fallback: string) {
  if (!disposition) return fallback

  const encodedMatch = disposition.match(/filename\*=(?:UTF-8'')?"?([^";]+)/i)
  if (encodedMatch?.[1]) {
    try {
      return decodeURIComponent(encodedMatch[1].replace(/"/g, ''))
    } catch (error) {
      console.warn('Failed to decode filename from header:', error)
    }
  }

  const simpleMatch = disposition.match(/filename="?([^";]+)/i)
  if (simpleMatch?.[1]) {
    return simpleMatch[1].replace(/"/g, '')
  }

  return fallback
}

async function bulkDownload() {
  if (selectedItems.value.size === 0) return
  if (typeof window === 'undefined') return

  const ids = Array.from(selectedItems.value)

  toast.add({
    title: 'Preparing downloads',
    description: `Starting download for ${ids.length} item${ids.length === 1 ? '' : 's'}`,
    color: 'primary'
  })

  for (const id of ids) {
    const fallbackName = items.value.find(item => item.id === id)?.original_filename || `discovery-item-${id}`

    try {
      const response = await fetch(`/api/v1/discovery/items/${id}/download`)
      if (!response.ok) {
        throw new Error(`Download request failed with status ${response.status}`)
      }

      const blob = await response.blob()
      const filename = extractFilenameFromDisposition(response.headers.get('Content-Disposition'), fallbackName)

      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Bulk download error:', error)
      toast.add({
        title: 'Download failed',
        description: `Unable to download ${fallbackName}`,
        color: 'red'
      })
      return
    }
  }

  toast.add({
    title: 'Downloads started',
    description: 'Files are downloading in your browser',
    color: 'green'
  })
}

// Bulk actions
async function bulkDelete() {
  if (!confirm(`Delete ${selectedItems.value.size} items?`)) return

  try {
    await $fetch('/api/v1/discovery/bulk-delete', {
      method: 'POST',
      body: { item_ids: Array.from(selectedItems.value) }
    })

    toast.add({
      title: 'Success',
      description: `Deleted ${selectedItems.value.size} items`,
      color: 'green'
    })

    clearSelection()
    fetchItems()
    fetchStats()
  } catch (error) {
    toast.add({
      title: 'Error',
      description: 'Failed to delete items',
      color: 'red'
    })
  }
}

async function bulkAddCategory(categoryId: number) {
  try {
    await $fetch('/api/v1/discovery/bulk-categorize', {
      method: 'POST',
      body: {
        item_ids: Array.from(selectedItems.value),
        category_id: categoryId
      }
    })

    toast.add({
      title: 'Success',
      description: `Added category to ${selectedItems.value.size} items`,
      color: 'green'
    })

    fetchItems()
  } catch (error) {
    toast.add({
      title: 'Error',
      description: 'Failed to add category',
      color: 'red'
    })
  }
}

// Upload handler
const uploadModalOpen = ref(false)

function handleUploadSuccess() {
  uploadModalOpen.value = false
  fetchItems()
  fetchStats()
  toast.add({
    title: 'Success',
    description: 'Item uploaded successfully',
    color: 'green'
  })
}

// Navigation to detail view
function viewItem(itemId: number) {
  router.push(`/discovery/${itemId}`)
}

// Clear filters
function clearFilters() {
  Object.assign(filters, {
    search: '',
    type: null,
    source: null,
    formFactor: null,
    minImportance: null,
    maxImportance: null,
    startDate: null,
    endDate: null,
    categories: [],
    processedOnly: false,
    memeFilter: null
  })
  page.value = 1
}

// Computed
const totalPages = computed(() => Math.ceil(totalItems.value / limit.value))
const hasActiveFilters = computed(() => {
  return filters.search || filters.type || filters.source ||
         filters.formFactor || filters.minImportance !== null ||
         filters.maxImportance !== null || filters.startDate ||
         filters.endDate || filters.categories.length > 0 ||
         filters.processedOnly || filters.memeFilter !== null
})

const storageDisplay = computed(() => formatStorage(stats.value.storageUsed))
const processingCount = computed(() => items.value.filter(item => !item.processed).length)
const isHighImportanceActive = computed(() => filters.minImportance === 0.7 && filters.maxImportance === 1.0)
const isMemeOnlyActive = computed(() => filters.memeFilter === true)
const isProcessedOnlyActive = computed(() => filters.processedOnly)
const highImportancePercent = computed(() => {
  if (!stats.value.total) return 0
  return Math.round((stats.value.highImportance / stats.value.total) * 100)
})

function formatStorage(bytes: number) {
  if (!bytes || bytes <= 0) return '0 GB'
  const gb = bytes / (1024 ** 3)
  if (gb >= 1) return `${gb.toFixed(1)} GB`
  const mb = bytes / (1024 ** 2)
  return `${mb.toFixed(1)} MB`
}

function toggleHighImportance() {
  if (isHighImportanceActive.value) {
    filters.minImportance = null
    filters.maxImportance = null
  } else {
    filters.minImportance = 0.7
    filters.maxImportance = 1.0
  }
  page.value = 1
}

function toggleMemeOnly() {
  filters.memeFilter = isMemeOnlyActive.value ? null : true
  page.value = 1
}

function toggleProcessedOnly() {
  filters.processedOnly = !filters.processedOnly
  page.value = 1
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Discovery">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>

        <template #trailing>
          <div class="flex items-center gap-3">
            <UInput
              v-model="filters.search"
              placeholder="Search discovery..."
              icon="i-lucide-search"
              class="hidden w-64 lg:flex"
              clearable
            />

            <!-- View mode toggle -->
            <UFieldGroup class="hidden md:flex">
              <UButton
                :color="viewMode === 'grid' ? 'primary' : 'neutral'"
                :variant="viewMode === 'grid' ? 'solid' : 'soft'"
                icon="i-lucide-grid-3x3"
                square
                size="sm"
                @click="viewMode = 'grid'"
              />
              <UButton
                :color="viewMode === 'list' ? 'primary' : 'neutral'"
                :variant="viewMode === 'list' ? 'solid' : 'soft'"
                icon="i-lucide-list"
                square
                size="sm"
                @click="viewMode = 'list'"
              />
              <UButton
                :color="viewMode === 'timeline' ? 'primary' : 'neutral'"
                :variant="viewMode === 'timeline' ? 'solid' : 'soft'"
                icon="i-lucide-clock"
                square
                size="sm"
                @click="viewMode = 'timeline'"
              />
            </UFieldGroup>

            <UButton
              color="neutral"
              variant="ghost"
              icon="i-lucide-folder-up"
              :to="'/discovery/import'"
              aria-label="Batch import"
            />

            <UButton
              label="Upload"
              icon="i-lucide-upload"
              color="primary"
              @click="uploadModalOpen = true"
            />
          </div>
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <div class="border-b border-default bg-surface/70">
        <div class="grid grid-cols-1 gap-4 px-6 py-5 sm:grid-cols-2 xl:grid-cols-4">
          <div class="rounded-xl border border-default/70 bg-surface px-5 py-4">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-xs font-semibold uppercase tracking-wide text-dimmed">Total items</p>
                <p class="mt-1 text-3xl font-semibold">{{ stats.total.toLocaleString() }}</p>
                <p class="text-xs text-dimmed opacity-80">{{ processingCount }} still processing</p>
              </div>
              <div class="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                <UIcon name="i-lucide-layers" class="size-5" />
              </div>
            </div>
          </div>

          <div class="rounded-xl border border-default/70 bg-surface px-5 py-4">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-xs font-semibold uppercase tracking-wide text-dimmed">High importance</p>
                <p class="mt-1 text-3xl font-semibold">{{ stats.highImportance.toLocaleString() }}</p>
                <p class="text-xs text-dimmed opacity-80">{{ highImportancePercent }}% of collection</p>
              </div>
              <div class="flex h-10 w-10 items-center justify-center rounded-full bg-amber-500/10 text-amber-500">
                <UIcon name="i-lucide-star" class="size-5" />
              </div>
            </div>
          </div>

          <div class="rounded-xl border border-default/70 bg-surface px-5 py-4">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-xs font-semibold uppercase tracking-wide text-dimmed">Processing queue</p>
                <p class="mt-1 text-3xl font-semibold">{{ stats.processing.toLocaleString() }}</p>
                <p class="text-xs text-dimmed opacity-80">{{ processingCount }} visible in this view</p>
              </div>
              <div class="flex h-10 w-10 items-center justify-center rounded-full bg-purple-500/10 text-purple-500">
                <UIcon name="i-lucide-loader-2" class="size-5 animate-spin" />
              </div>
            </div>
          </div>

          <div class="rounded-xl border border-default/70 bg-surface px-5 py-4">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-xs font-semibold uppercase tracking-wide text-dimmed">Storage used</p>
                <p class="mt-1 text-3xl font-semibold">{{ storageDisplay }}</p>
                <p class="text-xs text-dimmed opacity-80">Across all discovery assets</p>
              </div>
              <div class="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500">
                <UIcon name="i-lucide-hard-drive" class="size-5" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Filters & Content -->
      <div class="flex min-h-0 flex-1">
        <!-- Filter Sidebar - Hidden on mobile, visible on large screens -->
        <div class="hidden lg:block w-80 flex-shrink-0 border-r border-default bg-surface/60">
          <DiscoveryFilterSidebar
            v-model:filters="filters"
            :has-active-filters="hasActiveFilters"
            @clear="clearFilters"
          />
        </div>

        <!-- Main Content -->
        <div class="flex-1 overflow-y-auto p-4 lg:p-6">
        <!-- Mobile search -->
        <div class="mb-4 md:hidden">
          <UInput
            v-model="filters.search"
            placeholder="Search discovery..."
            icon="i-lucide-search"
            clearable
          />
        </div>

        <!-- Quick filters -->
        <div class="mb-6 flex flex-wrap items-center gap-2">
          <span class="text-xs font-semibold uppercase tracking-wide text-dimmed">Quick filters</span>
          <UButton
            size="xs"
            :color="isHighImportanceActive ? 'amber' : 'neutral'"
            :variant="isHighImportanceActive ? 'solid' : 'soft'"
            icon="i-lucide-star"
            label="High importance"
            @click="toggleHighImportance"
          />
          <UButton
            size="xs"
            :color="isMemeOnlyActive ? 'pink' : 'neutral'"
            :variant="isMemeOnlyActive ? 'solid' : 'soft'"
            icon="i-lucide-smile"
            label="Memes only"
            @click="toggleMemeOnly"
          />
          <UButton
            size="xs"
            :color="isProcessedOnlyActive ? 'primary' : 'neutral'"
            :variant="isProcessedOnlyActive ? 'solid' : 'soft'"
            icon="i-lucide-badge-check"
            label="Processed only"
            @click="toggleProcessedOnly"
          />
          <UButton
            v-if="hasActiveFilters"
            size="xs"
            color="neutral"
            variant="ghost"
            icon="i-lucide-rotate-ccw"
            label="Reset"
            @click="clearFilters"
          />
        </div>

        <!-- Bulk action bar -->
        <div
          v-if="selectedItems.size > 0"
          class="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/40 bg-primary/5 px-4 py-3"
        >
          <div class="flex items-center gap-3 text-sm">
            <UIcon name="i-lucide-check-square" class="size-4 text-primary" />
            <span class="font-semibold text-primary">{{ selectedItems.size }} items selected</span>
            <UButton
              label="Select All"
              size="xs"
              variant="ghost"
              @click="selectAll"
            />
            <UButton
              label="Clear Selection"
              size="xs"
              variant="ghost"
              @click="clearSelection"
            />
          </div>
          <div class="flex items-center gap-2">
            <UButton
              label="Download"
              icon="i-lucide-download"
              size="xs"
              variant="soft"
              color="primary"
              @click="bulkDownload"
            />
            <UButton
              label="Add Category"
              icon="i-lucide-tag"
              size="xs"
              @click="bulkActionOpen = true"
            />
            <UButton
              label="Delete"
              icon="i-lucide-trash"
              size="xs"
              color="red"
              @click="bulkDelete"
            />
          </div>
        </div>

        <!-- Loading state -->
        <div v-if="loading" class="flex items-center justify-center h-64">
          <UIcon name="i-lucide-loader-2" class="size-8 animate-spin text-primary" />
        </div>

        <!-- Empty state -->
        <div
          v-else-if="items.length === 0"
          class="flex flex-col items-center justify-center h-64 text-center"
        >
          <UIcon name="i-lucide-image-off" class="size-16 text-dimmed mb-4" />
          <h3 class="text-xl font-semibold mb-2">No items found</h3>
          <p class="text-dimmed mb-4">
            {{ hasActiveFilters ? 'Try adjusting your filters' : 'Upload your first discovery item to get started' }}
          </p>
          <UButton
            v-if="hasActiveFilters"
            label="Clear Filters"
            @click="clearFilters"
          />
          <UButton
            v-else
            label="Upload Item"
            icon="i-lucide-upload"
            color="primary"
            @click="uploadModalOpen = true"
          />
        </div>

        <!-- Grid View -->
        <div
          v-else-if="viewMode === 'grid'"
          class="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4"
        >
          <DiscoveryItemCard
            v-for="item in items"
            :key="item.id"
            :item="item"
            :selected="selectedItems.has(item.id)"
            @click="viewItem(item.id)"
            @select="toggleSelection(item.id)"
          />
        </div>

        <!-- List View -->
        <div v-else-if="viewMode === 'list'" class="space-y-3">
          <DiscoveryItemCard
            v-for="item in items"
            :key="item.id"
            :item="item"
            :selected="selectedItems.has(item.id)"
            view-mode="list"
            @click="viewItem(item.id)"
            @select="toggleSelection(item.id)"
          />
        </div>

        <!-- Timeline View -->
        <DiscoveryTimelineView
          v-else
          :items="items"
          @view-item="viewItem"
        />

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="mt-6 flex justify-center">
          <UPagination
            v-model="page"
            :total="totalItems"
            :per-page="limit"
            show-first
            show-last
          />
        </div>
        </div>
      </div>
    </template>
  </UDashboardPanel>

  <!-- Upload Modal -->
  <DiscoveryUploadModal
    v-model:open="uploadModalOpen"
    @success="handleUploadSuccess"
  />

  <!-- Bulk Category Modal -->
  <UModal v-model:open="bulkActionOpen" title="Add Category to Selected Items">
    <template #body>
      <DiscoveryCategorySelector @select="bulkAddCategory" />
    </template>
  </UModal>
</template>
