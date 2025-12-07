<script setup lang="ts">
import type { SearchResult } from '~/composables/useAI'

definePageMeta({ layout: 'default' })

const { searchDocuments } = useAI()
const { cases, listCases } = useCases()
const router = useRouter()

await listCases()

// Search state
const searchQuery = ref('')
const isSearching = ref(false)
const results = ref<SearchResult[]>([])
const error = ref<string | null>(null)
const totalFound = ref(0)
const searchTime = ref<number | null>(null)
const embeddingTime = ref<number | null>(null)

// Filters
const selectedCaseId = ref<string | null>(null)
const selectedDocumentType = ref<string | null>(null)

// UI state
const heroSearchInput = useTemplateRef('heroSearchInput')
const compactSearchInput = useTemplateRef('compactSearchInput')
const hasSearched = ref(false)

const caseOptions = computed(() => [
  { label: 'All Cases', value: null },
  ...(cases.value || []).map(c => ({ label: c.name, value: c.id }))
])

const documentTypeOptions = [
  { label: 'All Types', value: null },
  { label: 'Contract', value: 'contract' },
  { label: 'Agreement', value: 'agreement' },
  { label: 'Court Filing', value: 'court_filing' },
  { label: 'Transcript', value: 'transcript' },
  { label: 'General', value: 'general' }
]

// Perform search
async function performSearch() {
  if (!searchQuery.value.trim()) {
    results.value = []
    totalFound.value = 0
    hasSearched.value = false
    return
  }

  isSearching.value = true
  error.value = null
  hasSearched.value = true

  try {
    const response = await searchDocuments({
      query: searchQuery.value,
      caseId: selectedCaseId.value || undefined,
      documentType: selectedDocumentType.value || undefined,
      limit: 20
    })

    results.value = response.results
    totalFound.value = response.totalFound
    searchTime.value = response.searchTime || null
    embeddingTime.value = response.queryEmbeddingTime || null
  } catch (err: any) {
    error.value = err?.message || 'Search failed. Please check your Qdrant configuration.'
    results.value = []
  } finally {
    isSearching.value = false
  }
}

// Debounced search
const debouncedSearch = useDebounceFn(performSearch, 300)

// Track if we need to refocus after view switch
const needsRefocus = ref(false)

// Watch for search changes
watch([searchQuery, selectedCaseId, selectedDocumentType], () => {
  if (searchQuery.value.trim()) {
    isSearching.value = true
    // Mark that we'll need to refocus after switching to compact view
    if (!hasSearched.value) {
      needsRefocus.value = true
    }
  }
  debouncedSearch()
})

// Refocus compact input when switching from hero to results view
watch(hasSearched, async (newVal) => {
  if (newVal && needsRefocus.value) {
    needsRefocus.value = false
    await nextTick()
    compactSearchInput.value?.inputRef?.focus()
  }
})

function clearSearch() {
  searchQuery.value = ''
  results.value = []
  error.value = null
  hasSearched.value = false
}

function getCaseName(caseId: string | undefined) {
  if (!caseId) return null
  const c = cases.value?.find(c => c.id === caseId)
  return c?.name
}

function navigateToResult(result: SearchResult) {
  // Try to navigate to the document
  if (result.documentId) {
    router.push(`/documents/${result.documentId}`)
  }
}

function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`
}

function getScoreColor(score: number): string {
  if (score > 0.8) return 'success'
  if (score > 0.6) return 'warning'
  return 'neutral'
}

// Focus helper
function focusSearch() {
  if (hasSearched.value || isSearching.value) {
    compactSearchInput.value?.inputRef?.focus()
  } else {
    heroSearchInput.value?.inputRef?.focus()
  }
}

// Keyboard shortcuts
defineShortcuts({
  '/': {
    usingInput: false,
    handler: focusSearch
  },
  'escape': {
    handler: clearSearch
  }
})
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar :title="hasSearched ? `Search Results (${totalFound})` : 'Search'">
        <template #trailing>
          <div v-if="searchTime || embeddingTime" class="flex items-center gap-3 text-sm text-muted">
            <span v-if="embeddingTime">Embed: {{ embeddingTime }}ms</span>
            <span v-if="searchTime">Search: {{ searchTime }}ms</span>
          </div>
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <div class="h-full overflow-y-auto">
        <!-- Hero Search (when not searched yet) -->
        <div
          v-if="!hasSearched && !isSearching"
          class="flex items-center justify-center min-h-full px-6 py-12"
        >
          <div class="w-full max-w-4xl mx-auto text-center space-y-8">
            <!-- Logo -->
            <div class="flex items-center justify-center gap-4">
              <UIcon name="i-lucide-scale" class="size-16 text-primary" />
              <h1 class="text-5xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                LegalEase AI
              </h1>
            </div>

            <p class="text-lg text-muted max-w-xl mx-auto">
              AI-powered semantic search across your legal documents
            </p>

            <!-- Hero Search Bar -->
            <div class="space-y-4">
              <UInput
                ref="heroSearchInput"
                v-model="searchQuery"
                icon="i-lucide-search"
                placeholder="Search for legal terms, clauses, or concepts..."
                size="xl"
                :loading="isSearching"
                autofocus
                class="shadow-lg"
                @keyup.enter="performSearch"
              >
                <template #trailing>
                  <UKbd value="/" class="hidden sm:block" />
                </template>
              </UInput>

              <!-- Filters -->
              <div class="flex flex-wrap justify-center gap-3">
                <USelectMenu
                  v-model="selectedCaseId"
                  :items="caseOptions"
                  placeholder="Filter by case"
                  value-key="value"
                  class="w-48"
                />
                <USelectMenu
                  v-model="selectedDocumentType"
                  :items="documentTypeOptions"
                  placeholder="Document type"
                  value-key="value"
                  class="w-48"
                />
              </div>
            </div>

            <!-- Quick Examples -->
            <div class="pt-4">
              <p class="text-sm text-muted mb-3">
                Try searching for:
              </p>
              <div class="flex flex-wrap justify-center gap-2">
                <UButton
                  v-for="example in ['indemnification', 'force majeure', 'non-compete', 'intellectual property']"
                  :key="example"
                  :label="example"
                  color="neutral"
                  variant="outline"
                  size="xs"
                  @click="searchQuery = example; performSearch()"
                />
              </div>
            </div>

            <!-- Feature Cards -->
            <div class="grid grid-cols-3 gap-4 pt-8 max-w-lg mx-auto">
              <UCard :ui="{ body: 'p-4' }">
                <UIcon name="i-lucide-zap" class="size-6 text-primary mb-2" />
                <p class="text-sm font-medium">
                  Semantic
                </p>
                <p class="text-xs text-muted">
                  Find by meaning
                </p>
              </UCard>
              <UCard :ui="{ body: 'p-4' }">
                <UIcon name="i-lucide-layers" class="size-6 text-primary mb-2" />
                <p class="text-sm font-medium">
                  Vector
                </p>
                <p class="text-xs text-muted">
                  AI embeddings
                </p>
              </UCard>
              <UCard :ui="{ body: 'p-4' }">
                <UIcon name="i-lucide-filter" class="size-6 text-primary mb-2" />
                <p class="text-sm font-medium">
                  Filtered
                </p>
                <p class="text-xs text-muted">
                  By case & type
                </p>
              </UCard>
            </div>
          </div>
        </div>

        <!-- Results View -->
        <div v-else class="max-w-5xl mx-auto p-6 space-y-4">
          <!-- Compact Search Bar -->
          <div class="flex gap-3 items-center">
            <UInput
              ref="compactSearchInput"
              v-model="searchQuery"
              icon="i-lucide-search"
              placeholder="Search..."
              :loading="isSearching"
              class="flex-1"
              @keyup.enter="performSearch"
            >
              <template #trailing>
                <UButton
                  v-if="searchQuery"
                  icon="i-lucide-x"
                  color="neutral"
                  variant="ghost"
                  size="xs"
                  @click="clearSearch"
                />
              </template>
            </UInput>
            <USelectMenu
              v-model="selectedCaseId"
              :items="caseOptions"
              placeholder="Case"
              value-key="value"
              class="w-40"
            />
            <USelectMenu
              v-model="selectedDocumentType"
              :items="documentTypeOptions"
              placeholder="Type"
              value-key="value"
              class="w-36"
            />
          </div>

          <!-- Error -->
          <UAlert
            v-if="error"
            color="error"
            variant="subtle"
            icon="i-lucide-alert-circle"
          >
            <template #description>
              {{ error }}
              <span class="block mt-2 text-sm">Make sure Qdrant is configured and documents are indexed.</span>
            </template>
          </UAlert>

          <!-- Loading -->
          <div v-if="isSearching" class="flex items-center justify-center py-12">
            <div class="text-center space-y-4">
              <UIcon name="i-lucide-loader-circle" class="size-10 text-primary animate-spin mx-auto" />
              <p class="text-muted">
                Searching...
              </p>
            </div>
          </div>

          <!-- Results -->
          <div v-else-if="results.length > 0" class="space-y-3">
            <p class="text-sm text-muted">
              {{ totalFound }} results found
            </p>

            <UCard
              v-for="result in results"
              :key="result.id"
              class="cursor-pointer hover:shadow-md transition-all hover:border-primary/30"
              @click="navigateToResult(result)"
            >
              <div class="space-y-3">
                <div class="flex items-start justify-between gap-4">
                  <div class="flex items-center gap-2 min-w-0">
                    <UIcon
                      :name="result.metadata?.documentType === 'transcript' ? 'i-lucide-mic' : 'i-lucide-file-text'"
                      class="size-5 text-muted shrink-0"
                    />
                    <span class="font-medium truncate">{{ result.metadata?.filename || 'Document' }}</span>
                  </div>
                  <UBadge
                    :label="formatScore(result.score)"
                    :color="getScoreColor(result.score)"
                    variant="soft"
                    size="sm"
                  />
                </div>

                <p class="text-sm text-muted line-clamp-3">
                  {{ result.text }}
                </p>

                <div class="flex items-center gap-3 text-xs text-muted">
                  <span v-if="result.metadata?.pageNumber" class="flex items-center gap-1">
                    <UIcon name="i-lucide-file" class="size-3" />
                    Page {{ result.metadata.pageNumber }}
                  </span>
                  <span v-if="getCaseName(result.metadata?.caseId)" class="flex items-center gap-1">
                    <UIcon name="i-lucide-folder" class="size-3" />
                    {{ getCaseName(result.metadata?.caseId) }}
                  </span>
                  <UBadge
                    v-if="result.metadata?.documentType"
                    :label="result.metadata.documentType"
                    variant="outline"
                    size="xs"
                  />
                </div>
              </div>
            </UCard>
          </div>

          <!-- Empty State -->
          <div v-else-if="hasSearched" class="text-center py-16">
            <UIcon name="i-lucide-search-x" class="size-16 text-muted mx-auto mb-4 opacity-30" />
            <h3 class="text-xl font-semibold mb-2">
              No results found
            </h3>
            <p class="text-muted mb-4">
              Try adjusting your search terms or filters
            </p>
            <UButton label="Clear Search" variant="outline" @click="clearSearch" />
          </div>
        </div>
      </div>
    </template>
  </UDashboardPanel>
</template>
