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

// Fetch discovery items
async function fetchItems() {
  loading.value = true
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

    const response = await $fetch(`/api/discovery/items?${params.toString()}`)

    items.value = response.items
    totalItems.value = response.total

    // Filter by categories client-side if needed
    if (filters.categories.length > 0) {
      items.value = items.value.filter(item =>
        item.categories?.some(cat => filters.categories.includes(cat.id))
      )
    }

    // Filter by meme status if needed
    if (filters.memeFilter !== null) {
      items.value = items.value.filter(item =>
        item.visual_content?.some(vc => vc.is_meme === filters.memeFilter)
      )
    }
  } catch (error) {
    console.error('Error fetching discovery items:', error)
    toast.add({
      title: 'Error',
      description: 'Failed to load discovery items',
      color: 'red'
    })
  } finally {
    loading.value = false
  }
}

// Fetch stats
async function fetchStats() {
  try {
    const response = await $fetch('/api/discovery/stats')
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

  // Poll for processing updates every 5 seconds
  const interval = setInterval(() => {
    fetchStats()
    // Refresh items if any are processing
    if (items.value.some(item => !item.processed)) {
      fetchItems()
    }
  }, 5000)

  onUnmounted(() => clearInterval(interval))
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

// Bulk actions
async function bulkDelete() {
  if (!confirm(`Delete ${selectedItems.value.size} items?`)) return

  try {
    await $fetch('/api/discovery/bulk-delete', {
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
    await $fetch('/api/discovery/bulk-categorize', {
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
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Discovery">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>

        <template #trailing>
          <div class="flex items-center gap-2">
            <!-- View mode toggle -->
            <UButtonGroup>
              <UButton
                :color="viewMode === 'grid' ? 'primary' : 'neutral'"
                :variant="viewMode === 'grid' ? 'solid' : 'ghost'"
                icon="i-lucide-grid-3x3"
                @click="viewMode = 'grid'"
              />
              <UButton
                :color="viewMode === 'list' ? 'primary' : 'neutral'"
                :variant="viewMode === 'list' ? 'solid' : 'ghost'"
                icon="i-lucide-list"
                @click="viewMode = 'list'"
              />
              <UButton
                :color="viewMode === 'timeline' ? 'primary' : 'neutral'"
                :variant="viewMode === 'timeline' ? 'solid' : 'ghost'"
                icon="i-lucide-clock"
                @click="viewMode = 'timeline'"
              />
            </UButtonGroup>

            <!-- Upload button -->
            <UButton
              label="Upload"
              icon="i-lucide-upload"
              color="primary"
              @click="uploadModalOpen = true"
            />

            <!-- Batch import button -->
            <UButton
              label="Batch Import"
              icon="i-lucide-folder-up"
              color="neutral"
              variant="outline"
              :to="'/discovery/import'"
            />
          </div>
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <!-- Stats Cards -->
      <div class="p-6 border-b border-default bg-elevated">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Total Items -->
        <UCard class="bg-gradient-to-br from-blue-500/10 to-blue-600/10">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-dimmed">Total Items</p>
              <p class="text-3xl font-bold">{{ stats.total.toLocaleString() }}</p>
            </div>
            <UIcon name="i-lucide-image" class="size-12 text-blue-500 opacity-50" />
          </div>
        </UCard>

        <!-- High Importance -->
        <UCard class="bg-gradient-to-br from-amber-500/10 to-amber-600/10">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-dimmed">High Importance</p>
              <p class="text-3xl font-bold">{{ stats.highImportance.toLocaleString() }}</p>
            </div>
            <UIcon name="i-lucide-star" class="size-12 text-amber-500 opacity-50" />
          </div>
        </UCard>

        <!-- Processing -->
        <UCard class="bg-gradient-to-br from-purple-500/10 to-purple-600/10">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-dimmed">Processing</p>
              <p class="text-3xl font-bold">{{ stats.processing.toLocaleString() }}</p>
            </div>
            <UIcon name="i-lucide-loader-2" class="size-12 text-purple-500 opacity-50 animate-spin" />
          </div>
        </UCard>

        <!-- Storage Used -->
        <UCard class="bg-gradient-to-br from-green-500/10 to-green-600/10">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-dimmed">Storage Used</p>
              <p class="text-3xl font-bold">{{ (stats.storageUsed / 1024 / 1024 / 1024).toFixed(2) }} GB</p>
            </div>
            <UIcon name="i-lucide-hard-drive" class="size-12 text-green-500 opacity-50" />
          </div>
        </UCard>
        </div>
      </div>

      <!-- Filters & Content -->
      <div class="flex min-h-0 flex-1">
        <!-- Filter Sidebar - Hidden on mobile, visible on large screens -->
        <div class="hidden lg:block w-80 border-r border-default bg-elevated/50 flex-shrink-0">
          <DiscoveryFilterSidebar
            v-model:filters="filters"
            :has-active-filters="hasActiveFilters"
            @clear="clearFilters"
          />
        </div>

        <!-- Main Content -->
        <div class="flex-1 overflow-y-auto p-4 lg:p-6">
        <!-- Bulk action bar -->
        <div
          v-if="selectedItems.size > 0"
          class="mb-4 p-4 bg-primary/10 border border-primary rounded-lg flex items-center justify-between"
        >
          <div class="flex items-center gap-4">
            <span class="font-semibold">{{ selectedItems.size }} items selected</span>
            <UButton
              label="Select All"
              size="sm"
              variant="ghost"
              @click="selectAll"
            />
            <UButton
              label="Clear Selection"
              size="sm"
              variant="ghost"
              @click="clearSelection"
            />
          </div>
          <div class="flex items-center gap-2">
            <UButton
              label="Add Category"
              icon="i-lucide-tag"
              size="sm"
              @click="bulkActionOpen = true"
            />
            <UButton
              label="Delete"
              icon="i-lucide-trash"
              size="sm"
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
          class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
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
        <div v-else-if="viewMode === 'list'" class="space-y-2">
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
