<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Search Header -->
    <UPageSection class="bg-white border-b border-gray-200">
      <div class="flex flex-col lg:flex-row items-start lg:items-center gap-6">
        <div class="flex-1 max-w-2xl w-full">
          <UFormField>
            <UInput
              v-model="searchQuery"
              placeholder="Search legal documents..."
              size="lg"
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
          </UFormField>
        </div>

        <!-- Quick Filters -->
        <div class="flex items-center space-x-3">
          <USelectMenu
            v-model="selectedCase"
            :options="caseOptions"
            placeholder="All Cases"
            class="w-40"
          />
          <USelectMenu
            v-model="selectedType"
            :options="typeOptions"
            placeholder="All Types"
            class="w-36"
          />
          <UButton
            variant="outline"
            @click="showAdvancedFilters = !showAdvancedFilters"
            :color="showAdvancedFilters ? 'primary' : 'gray'"
          >
            <UIcon name="i-heroicons-adjustments-horizontal-20-solid" class="w-4 h-4 mr-2" />
            Filters
          </UButton>
        </div>
      </div>

      <!-- Advanced Filters -->
      <div v-if="showAdvancedFilters" class="mt-6 pt-6 border-t border-gray-200">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
          <UFormField label="Entities">
            <USelectMenu
              v-model="selectedEntity"
              :options="entityOptions"
              placeholder="Filter by Entity"
              multiple
            />
          </UFormField>
          <UFormField label="Tags">
            <USelectMenu
              v-model="selectedTag"
              :options="tagOptions"
              placeholder="Filter by Tag"
              multiple
            />
          </UFormField>
          <UFormField label="Date Range">
            <div class="flex space-x-2">
              <UInput
                v-model="dateFrom"
                type="date"
                size="sm"
                placeholder="From"
              />
              <UInput
                v-model="dateTo"
                type="date"
                size="sm"
                placeholder="To"
              />
            </div>
          </UFormField>
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
    </UPageSection>

    <!-- Search Results -->
    <UPageSection>
      <!-- Results Header -->
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div class="flex items-center space-x-4">
          <h2 class="text-2xl font-bold text-gray-900">
            Search Results
          </h2>
          <UBadge
            :color="results.length > 0 ? 'success' : 'neutral'"
            variant="soft"
            size="lg"
          >
            {{ results.length }} results
          </UBadge>
          <span v-if="searchTime" class="text-sm text-gray-500">
            ({{ searchTime }}ms)
          </span>
        </div>

        <UFormField label="Sort by">
          <USelectMenu
            v-model="sortBy"
            :options="sortOptions"
            size="sm"
            class="w-48"
          />
        </UFormField>
      </div>

      <!-- Results Content -->
      <div class="space-y-6">
        <!-- Loading State -->
        <UCard v-if="loading" class="text-center py-12">
          <UIcon name="i-heroicons-arrow-path-20-solid" class="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <h3 class="text-lg font-medium text-gray-900 mb-2">Searching...</h3>
          <p class="text-gray-500">Finding relevant legal documents</p>
        </UCard>

        <!-- No Results -->
        <UCard v-else-if="!loading && results.length === 0 && searchQuery" class="text-center py-12">
          <template #header>
            <UIcon name="i-heroicons-magnifying-glass-20-solid" class="w-16 h-16 text-gray-300 mx-auto" />
          </template>
          <h3 class="text-lg font-medium text-gray-900 mb-2">No results found</h3>
          <p class="text-gray-500 mb-6">
            Try adjusting your search terms or filters
          </p>
          <div class="space-y-4">
            <p class="text-sm font-medium text-gray-700">Suggestions:</p>
            <div class="flex flex-wrap justify-center gap-2">
              <UBadge
                v-for="suggestion in searchSuggestions"
                :key="suggestion"
                variant="outline"
                class="cursor-pointer hover:bg-primary/5 transition-colors"
                @click="applySuggestion(suggestion)"
              >
                {{ suggestion }}
              </UBadge>
            </div>
          </div>
        </UCard>

        <!-- Results -->
        <UPageGrid v-else-if="results.length > 0">
          <SearchResultCard
            v-for="result in results"
            :key="result.id"
            :result="result"
          />
        </UPageGrid>

        <!-- Empty State -->
        <UCard v-else class="text-center py-12">
          <template #header>
            <UIcon name="i-heroicons-document-text-20-solid" class="w-16 h-16 text-gray-300 mx-auto" />
          </template>
          <h3 class="text-lg font-medium text-gray-900 mb-2">Start searching</h3>
          <p class="text-gray-500">
            Enter a search query to find legal documents
          </p>
        </UCard>
      </div>

      <!-- Load More -->
      <div v-if="hasMoreResults" class="text-center mt-12">
        <UButton
          variant="outline"
          size="lg"
          :loading="loadingMore"
          @click="loadMore"
        >
          <UIcon name="i-heroicons-arrow-down-20-solid" class="w-4 h-4 mr-2" />
          Load More Results
        </UButton>
      </div>
    </UPageSection>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useDebounceFn } from '@vueuse/core'

// Composables
const { apiFetch } = useApi()

// Types
interface SearchResult {
  id: string
  filename: string
  case_name: string
  content: string
  score: number
  highlights: string[]
  created_at: string
}

interface SearchResponse {
  results: SearchResult[]
  has_more: boolean
  total: number
}

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

const results = ref<SearchResult[]>([])
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
const debouncedSearch = useDebounceFn(async () => {
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
    }) as any

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


// Load initial data
onMounted(async () => {
  try {
    // Load cases
    const casesResponse = await apiFetch('/cases') as any
    caseOptions.value = casesResponse.cases?.map((c: any) => ({
      label: c.name,
      value: c.id
    })) || []

    // Load entities and tags for filters
    const [entitiesResponse, tagsResponse] = await Promise.all([
      apiFetch('/entities/stats'),
      apiFetch('/tags/stats')
    ])

    entityOptions.value = (entitiesResponse as any).entities?.map((e: any) => ({
      label: e.text,
      value: e.text
    })) || []

    tagOptions.value = (tagsResponse as any).tags?.map((t: any) => ({
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