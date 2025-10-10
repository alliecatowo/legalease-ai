<script setup lang="ts">
import { useDebounceFn } from '@vueuse/core'

definePageMeta({
  layout: 'default'
})

const api = useApi()
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const isLoading = ref(false)
const showFilters = ref(false)
const showSavedSearches = ref(false)
const isSearching = computed(() => searchQuery.value.trim().length > 0)

// Filters
const filters = ref({
  documentTypes: [],
  jurisdictions: [],
  dateRange: [null, null],
  parties: [],
  tags: [],
  sortBy: 'relevance'
})

// Mock data for demonstration - TODO: Replace with real API data
const mockResults = [
  {
    id: '1',
    title: 'Master Services Agreement between Acme Corp and Global Tech Inc',
    excerpt: 'This Master Services Agreement ("Agreement") is entered into as of <mark>January 15, 2024</mark>, by and between <mark>Acme Corporation</mark>, a Delaware corporation, and <mark>Global Tech Inc</mark>, a California corporation...',
    documentType: 'contract',
    date: '2024-01-15',
    jurisdiction: 'Delaware',
    parties: ['Acme Corporation', 'Global Tech Inc'],
    citations: 5,
    relevanceScore: 0.95,
    entities: [
      { type: 'ORGANIZATION', text: 'Acme Corporation' },
      { type: 'ORGANIZATION', text: 'Global Tech Inc' },
      { type: 'DATE', text: 'January 15, 2024' },
      { type: 'MONEY', text: '$2.5M' }
    ],
    caseNumber: '2024-CV-1234'
  },
  {
    id: '2',
    title: 'Smith v. Johnson - Motion for Summary Judgment',
    excerpt: 'Defendant respectfully moves this Court for <mark>summary judgment</mark> pursuant to Federal Rule of Civil Procedure 56. There is no genuine dispute as to any material fact...',
    documentType: 'court_filing',
    date: '2024-02-01',
    jurisdiction: 'California',
    court: 'Superior Court of California',
    citations: 12,
    relevanceScore: 0.88,
    entities: [
      { type: 'PERSON', text: 'Smith' },
      { type: 'PERSON', text: 'Johnson' },
      { type: 'COURT', text: 'Superior Court' },
      { type: 'CITATION', text: 'FRCP 56' }
    ],
    caseNumber: 'CV-2023-5678'
  },
  {
    id: '3',
    title: 'Deposition Transcript - Jane Doe',
    excerpt: 'Q: Can you describe the events of <mark>March 3rd, 2024</mark>? A: Yes, I was at the office when I received a call from <mark>Mr. Anderson</mark> regarding the contract dispute...',
    documentType: 'transcript',
    date: '2024-03-10',
    jurisdiction: 'Federal',
    parties: ['Jane Doe', 'Anderson'],
    relevanceScore: 0.82,
    entities: [
      { type: 'PERSON', text: 'Jane Doe' },
      { type: 'PERSON', text: 'Mr. Anderson' },
      { type: 'DATE', text: 'March 3rd, 2024' }
    ]
  }
]

const performSearch = useDebounceFn(async () => {
  if (!searchQuery.value.trim()) {
    searchResults.value = []
    return
  }

  isLoading.value = true
  try {
    // TODO: Connect to real search API
    // const results = await api.search.query({
    //   q: searchQuery.value,
    //   filters: filters.value
    // })

    // Mock delay for demonstration
    await new Promise(resolve => setTimeout(resolve, 500))
    searchResults.value = mockResults
  } catch (error) {
    console.error('Search error:', error)
    searchResults.value = []
  } finally {
    isLoading.value = false
  }
}, 300)

watch(searchQuery, performSearch)
watch(filters, performSearch, { deep: true })

function applySavedSearch(search: any) {
  searchQuery.value = search.query
  filters.value = search.filters
  showSavedSearches.value = false
}

function saveCurrentSearch(name: string) {
  // TODO: Save search to backend
  console.log('Saving search:', name, searchQuery.value, filters.value)
}

// Keyboard shortcuts
defineShortcuts({
  '/': {
    handler: () => {
      document.querySelector('input[type="text"]')?.focus()
    }
  },
  'meta_k': {
    usingInput: true,
    handler: () => {
      showFilters.value = !showFilters.value
    }
  },
  'meta_s': {
    usingInput: true,
    handler: () => {
      showSavedSearches.value = !showSavedSearches.value
    }
  }
})
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar :title="isSearching ? `Search Results (${searchResults.length})` : 'Search'">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #trailing>
          <UButtonGroup>
            <UTooltip text="Saved Searches (⌘S)">
              <UButton
                icon="i-lucide-bookmark"
                color="neutral"
                :variant="showSavedSearches ? 'soft' : 'ghost'"
                @click="showSavedSearches = !showSavedSearches"
              />
            </UTooltip>
            <UTooltip text="Filters (⌘K)">
              <UButton
                icon="i-lucide-filter"
                color="neutral"
                :variant="showFilters ? 'soft' : 'ghost'"
                @click="showFilters = !showFilters"
              >
                <template v-if="filters.documentTypes.length + filters.jurisdictions.length + filters.tags.length" #trailing>
                  <UBadge
                    :label="String(filters.documentTypes.length + filters.jurisdictions.length + filters.tags.length)"
                    size="xs"
                    color="primary"
                  />
                </template>
              </UButton>
            </UTooltip>
          </UButtonGroup>
        </template>
      </UDashboardNavbar>
    </template>

    <div class="flex h-[calc(100vh-64px)]">
      <!-- Main Content Area -->
      <div class="flex-1 overflow-y-auto">
        <!-- Hero Search (when not searching) -->
        <div
          v-if="!isSearching"
          class="flex flex-col items-center justify-center min-h-full px-6 py-12"
        >
          <div class="text-center space-y-6 max-w-4xl mx-auto">
            <!-- Logo/Icon -->
            <div class="flex items-center justify-center gap-4 mb-8">
              <UIcon name="i-lucide-scale" class="size-16 text-primary" />
              <h1 class="text-6xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                LegalSearch AI
              </h1>
            </div>

            <p class="text-xl text-muted max-w-2xl">
              Intelligent semantic search across your legal documents, contracts, and case files
            </p>

            <!-- Hero Search Bar -->
            <div class="w-full max-w-3xl mx-auto">
              <UInput
                v-model="searchQuery"
                icon="i-lucide-search"
                placeholder="Search for legal terms, clauses, concepts, or natural language queries..."
                size="xl"
                :loading="isLoading"
                autofocus
                class="shadow-lg"
              >
                <template #trailing>
                  <UKbd value="/" />
                </template>
              </UInput>
            </div>

            <!-- Quick Examples -->
            <div class="flex flex-wrap justify-center gap-2 mt-6">
              <UButton
                v-for="example in ['indemnification clauses', 'force majeure', 'non-compete agreements', 'intellectual property rights']"
                :key="example"
                :label="example"
                color="neutral"
                variant="outline"
                size="xs"
                @click="searchQuery = example"
              />
            </div>

            <!-- Feature Cards -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16">
              <UCard :ui="{ body: 'space-y-3' }">
                <UIcon name="i-lucide-zap" class="size-8 text-primary" />
                <h3 class="font-semibold text-lg">Semantic Search</h3>
                <p class="text-sm text-muted">
                  Find documents by meaning and context, not just exact keywords
                </p>
              </UCard>
              <UCard :ui="{ body: 'space-y-3' }">
                <UIcon name="i-lucide-target" class="size-8 text-primary" />
                <h3 class="font-semibold text-lg">Entity Recognition</h3>
                <p class="text-sm text-muted">
                  Automatic identification of parties, dates, amounts, and legal citations
                </p>
              </UCard>
              <UCard :ui="{ body: 'space-y-3' }">
                <UIcon name="i-lucide-sparkles" class="size-8 text-primary" />
                <h3 class="font-semibold text-lg">AI-Powered</h3>
                <p class="text-sm text-muted">
                  Advanced language models trained on legal corpus for accuracy
                </p>
              </UCard>
            </div>
          </div>
        </div>

        <!-- Compact Search Header (when searching) -->
        <div v-else class="sticky top-0 z-10 bg-default border-b border-default shadow-sm">
          <UContainer>
            <div class="py-3">
              <div class="flex items-center gap-4">
                <div class="flex items-center gap-2 shrink-0">
                  <UIcon name="i-lucide-scale" class="size-5 text-primary" />
                  <span class="text-sm font-bold hidden sm:block">LegalSearch</span>
                </div>
                <div class="flex-1 max-w-2xl">
                  <UInput
                    v-model="searchQuery"
                    icon="i-lucide-search"
                    placeholder="Search..."
                    size="md"
                    :loading="isLoading"
                  >
                    <template #trailing>
                      <UButton
                        v-if="searchQuery"
                        icon="i-lucide-x"
                        color="neutral"
                        variant="ghost"
                        size="xs"
                        @click="searchQuery = ''"
                      />
                    </template>
                  </UInput>
                </div>
              </div>
            </div>
          </UContainer>
        </div>

        <!-- Search Results -->
        <div v-if="isSearching" class="p-6">
          <UContainer>
            <!-- Results Header -->
            <div v-if="searchResults.length > 0" class="mb-6 flex items-center justify-between">
              <p class="text-sm text-muted">
                About <span class="font-semibold text-highlighted">{{ searchResults.length }}</span> results
                <span v-if="filters.documentTypes.length || filters.jurisdictions.length || filters.tags.length">
                  with active filters
                </span>
              </p>
              <div class="flex items-center gap-2">
                <UButton
                  label="Search within results"
                  icon="i-lucide-search"
                  color="neutral"
                  variant="outline"
                  size="xs"
                />
                <UButton
                  label="Export results"
                  icon="i-lucide-download"
                  color="neutral"
                  variant="outline"
                  size="xs"
                />
              </div>
            </div>

            <!-- Search Results List -->
            <div class="space-y-4 max-w-5xl">
              <SearchResultCard
                v-for="result in searchResults"
                :key="result.id"
                :result="result"
              />
            </div>

            <!-- No Results -->
            <div v-if="searchResults.length === 0 && !isLoading" class="text-center py-20">
              <UIcon name="i-lucide-search-x" class="size-20 text-muted mx-auto mb-6 opacity-30" />
              <h3 class="text-2xl font-semibold mb-3 text-highlighted">No results found</h3>
              <p class="text-muted mb-6 max-w-md mx-auto">
                We couldn't find any documents matching "{{ searchQuery }}".
                Try different keywords or adjust your filters.
              </p>
              <div class="flex flex-wrap justify-center gap-2">
                <UButton
                  label="Clear filters"
                  icon="i-lucide-x"
                  color="neutral"
                  variant="outline"
                  @click="filters = { documentTypes: [], jurisdictions: [], dateRange: [null, null], parties: [], tags: [], sortBy: 'relevance' }"
                />
                <UButton
                  label="View all documents"
                  icon="i-lucide-folder"
                  color="neutral"
                  to="/documents"
                />
              </div>
            </div>

            <!-- Loading State -->
            <div v-if="isLoading" class="flex flex-col items-center justify-center py-20">
              <UIcon name="i-lucide-loader" class="size-12 text-primary animate-spin mb-4" />
              <p class="text-muted">Searching through documents...</p>
              <p class="text-sm text-dimmed mt-2">Using AI-powered semantic search</p>
            </div>
          </UContainer>
        </div>
      </div>

      <!-- Filters Sidebar -->
      <div
        v-if="showFilters"
        class="w-80 border-l border-default bg-default overflow-hidden flex flex-col"
      >
        <FacetedSidebar v-model="filters" />
      </div>

      <!-- Saved Searches Sidebar -->
      <div
        v-if="showSavedSearches"
        class="w-80 border-l border-default bg-default overflow-hidden p-4"
      >
        <SavedSearchManager
          @apply="applySavedSearch"
          @save="saveCurrentSearch"
        />
      </div>
    </div>
  </UDashboardPanel>
</template>
