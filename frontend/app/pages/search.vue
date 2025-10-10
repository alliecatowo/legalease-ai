<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Search Header -->
    <div class="bg-white border-b border-gray-200">
      <div class="container mx-auto px-4 py-4">
        <div class="flex items-center justify-between">
          <div class="flex-1 max-w-2xl">
            <div class="relative">
              <UInput
                v-model="searchQuery"
                placeholder="Search legal documents..."
                size="lg"
                class="w-full"
                @input="debouncedSearch"
              >
                <template #leading>
                  <UIcon name="i-heroicons-magnifying-glass-20-solid" class="w-5 h-5 text-gray-400" />
                </template>
                <template #trailing>
                  <UButton
                    v-if="searchQuery"
                    variant="link"
                    size="sm"
                    @click="clearSearch"
                  >
                    <UIcon name="i-heroicons-x-mark-20-solid" class="w-4 h-4" />
                  </UButton>
                </template>
              </UInput>
            </div>
          </div>

          <!-- Search Filters -->
          <div class="flex items-center space-x-4 ml-6">
            <USelectMenu
              v-model="selectedCase"
              :options="caseOptions"
              placeholder="All Cases"
              class="w-48"
            />
            <USelectMenu
              v-model="selectedType"
              :options="typeOptions"
              placeholder="All Types"
              class="w-40"
            />
            <UButton
              variant="outline"
              @click="showAdvancedFilters = !showAdvancedFilters"
            >
              <UIcon name="i-heroicons-adjustments-horizontal-20-solid" class="w-4 h-4 mr-2" />
              Filters
            </UButton>
          </div>
        </div>

        <!-- Advanced Filters -->
        <div v-if="showAdvancedFilters" class="mt-4 pt-4 border-t border-gray-200">
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <USelectMenu
              v-model="selectedEntity"
              :options="entityOptions"
              placeholder="Filter by Entity"
              multiple
            />
            <USelectMenu
              v-model="selectedTag"
              :options="tagOptions"
              placeholder="Filter by Tag"
              multiple
            />
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Date Range</label>
              <div class="flex space-x-2">
                <UInput
                  v-model="dateFrom"
                  type="date"
                  size="sm"
                />
                <UInput
                  v-model="dateTo"
                  type="date"
                  size="sm"
                />
              </div>
            </div>
            <div class="flex items-end">
              <UButton
                variant="outline"
                size="sm"
                @click="clearFilters"
              >
                Clear Filters
              </UButton>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Search Results -->
    <div class="container mx-auto px-4 py-6">
      <!-- Results Header -->
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center space-x-4">
          <h2 class="text-xl font-semibold text-gray-900">
            Search Results
          </h2>
          <USBadge
            :color="results.length > 0 ? 'green' : 'gray'"
            variant="subtle"
          >
            {{ results.length }} results
          </USBadge>
          <span v-if="searchTime" class="text-sm text-gray-500">
            ({{ searchTime }}ms)
          </span>
        </div>

        <div class="flex items-center space-x-2">
          <USelectMenu
            v-model="sortBy"
            :options="sortOptions"
            size="sm"
            class="w-40"
          />
        </div>
      </div>

      <!-- Results Grid -->
      <div class="grid grid-cols-1 gap-4">
        <!-- Loading State -->
        <div v-if="loading" class="text-center py-12">
          <UIcon name="i-heroicons-arrow-path-20-solid" class="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
          <p class="text-gray-600">Searching...</p>
        </div>

        <!-- No Results -->
        <div v-else-if="!loading && results.length === 0 && searchQuery" class="text-center py-12">
          <UIcon name="i-heroicons-magnifying-glass-20-solid" class="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 class="text-lg font-medium text-gray-900 mb-2">No results found</h3>
          <p class="text-gray-500 mb-4">
            Try adjusting your search terms or filters
          </p>
          <div class="space-y-2">
            <p class="text-sm text-gray-600">Suggestions:</p>
            <div class="flex flex-wrap justify-center gap-2">
              <UBadge
                v-for="suggestion in searchSuggestions"
                :key="suggestion"
                variant="outline"
                class="cursor-pointer hover:bg-blue-50"
                @click="applySuggestion(suggestion)"
              >
                {{ suggestion }}
              </UBadge>
            </div>
          </div>
        </div>

        <!-- Results -->
        <div
          v-else-if="results.length > 0"
          class="space-y-4"
        >
          <SearchResultCard
            v-for="result in results"
            :key="result.id"
            :result="result"
            @click="openDocument(result)"
          />
        </div>

        <!-- Empty State -->
        <div v-else class="text-center py-12">
          <UIcon name="i-heroicons-document-text-20-solid" class="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 class="text-lg font-medium text-gray-900 mb-2">Start searching</h3>
          <p class="text-gray-500">
            Enter a search query to find legal documents
          </p>
        </div>
      </div>

      <!-- Load More -->
      <div v-if="hasMoreResults" class="text-center mt-8">
        <UButton
          variant="outline"
          :loading="loadingMore"
          @click="loadMore"
        >
          Load More Results
        </UButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { debounce } from '@vueuse/core'

// Composables
const { apiFetch } = useApi()

// Reactive state
const searchQuery = ref('')
const selectedCase = ref('')
const selectedType = ref('')
const selectedEntity = ref([])
const selectedTag = ref([])
const dateFrom = ref('')
const dateTo = ref('')
const sortBy = ref('relevance')
const showAdvancedFilters = ref(false)

const results = ref([])
const loading = ref(false)
const loadingMore = ref(false)
const searchTime = ref(0)
const hasMoreResults = ref(false)
const currentPage = ref(0)

// Options
const caseOptions = ref([])
const typeOptions = ref([
  { label: 'Contract', value: 'contract' },
  { label: 'Lawsuit', value: 'lawsuit' },
  { label: 'Court Order', value: 'court_order' },
  { label: 'Statute', value: 'statute' },
  { label: 'Evidence', value: 'evidence' },
  { label: 'Correspondence', value: 'correspondence' }
])
const entityOptions = ref([])
const tagOptions = ref([])
const sortOptions = ref([
  { label: 'Relevance', value: 'relevance' },
  { label: 'Date (Newest)', value: 'date_desc' },
  { label: 'Date (Oldest)', value: 'date_asc' },
  { label: 'File Size', value: 'size' }
])

// Computed
const searchSuggestions = computed(() => {
  if (!searchQuery.value) return []
  return [
    `"${searchQuery.value}"`,
    `${searchQuery.value} contract`,
    `${searchQuery.value} agreement`,
    `${searchQuery.value} lawsuit`
  ].slice(0, 4)
})

// Debounced search
const debouncedSearch = debounce(async () => {
  await performSearch()
}, 300)

// Methods
async function performSearch(resetPage = true) {
  if (resetPage) {
    currentPage.value = 0
  }

  if (!searchQuery.value.trim()) {
    results.value = []
    return
  }

  loading.value = true
  const startTime = Date.now()

  try {
    const params = {
      q: searchQuery.value,
      case_id: selectedCase.value || undefined,
      doc_type: selectedType.value || undefined,
      entities: selectedEntity.value.length ? selectedEntity.value : undefined,
      tags: selectedTag.value.length ? selectedTag.value : undefined,
      date_from: dateFrom.value || undefined,
      date_to: dateTo.value || undefined,
      sort: sortBy.value,
      page: currentPage.value,
      limit: 20
    }

    const response = await apiFetch('/search', {
      method: 'GET',
      params
    })

    if (resetPage) {
      results.value = response.results || []
    } else {
      results.value.push(...(response.results || []))
    }

    hasMoreResults.value = response.has_more || false
    searchTime.value = Date.now() - startTime

  } catch (error) {
    console.error('Search failed:', error)
    results.value = []
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  if (!hasMoreResults.value || loadingMore.value) return

  loadingMore.value = true
  currentPage.value++
  await performSearch(false)
  loadingMore.value = false
}

function clearSearch() {
  searchQuery.value = ''
  results.value = []
  searchTime.value = 0
}

function clearFilters() {
  selectedCase.value = ''
  selectedType.value = ''
  selectedEntity.value = []
  selectedTag.value = []
  dateFrom.value = ''
  dateTo.value = ''
}

function applySuggestion(suggestion: string) {
  searchQuery.value = suggestion
  performSearch()
}

function openDocument(result: any) {
  navigateTo(`/documents/${result.id}`)
}

// Load initial data
onMounted(async () => {
  try {
    // Load cases
    const casesResponse = await apiFetch('/cases')
    caseOptions.value = casesResponse.cases?.map((c: any) => ({
      label: c.name,
      value: c.id
    })) || []

    // Load entities and tags for filters
    const [entitiesResponse, tagsResponse] = await Promise.all([
      apiFetch('/entities/stats'),
      apiFetch('/tags/stats')
    ])

    entityOptions.value = entitiesResponse.entities?.map((e: any) => ({
      label: e.text,
      value: e.text
    })) || []

    tagOptions.value = tagsResponse.tags?.map((t: any) => ({
      label: t.name,
      value: t.name
    })) || []

  } catch (error) {
    console.error('Failed to load filter options:', error)
  }
})

// Watch for filter changes
watch([selectedCase, selectedType, selectedEntity, selectedTag, dateFrom, dateTo, sortBy], () => {
  if (searchQuery.value) {
    performSearch()
  }
})
</script>