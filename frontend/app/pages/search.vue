<script setup lang="ts">
definePageMeta({
  layout: 'default'
})

const api = useApi()
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const isLoading = ref(false)
const showSettings = ref(false)

// Search settings
const searchMode = ref<'hybrid' | 'semantic' | 'keyword'>('hybrid')
const searchSettings = ref({
  use_bm25: true,
  use_dense: true,
  fusion_method: 'rrf' as 'rrf' | 'weighted' | 'max',
  top_k: 20
})

// Watch search mode and update settings
watch(searchMode, (mode) => {
  if (mode === 'hybrid') {
    searchSettings.value.use_bm25 = true
    searchSettings.value.use_dense = true
  } else if (mode === 'semantic') {
    searchSettings.value.use_bm25 = false
    searchSettings.value.use_dense = true
  } else if (mode === 'keyword') {
    searchSettings.value.use_bm25 = true
    searchSettings.value.use_dense = false
  }
})

// Perform search with proper debouncing
const performSearch = async () => {
  if (!searchQuery.value.trim()) {
    searchResults.value = []
    return
  }

  isLoading.value = true
  try {
    // Use hybrid endpoint by default
    const response = await api.search.hybrid({
      query: searchQuery.value,
      ...searchSettings.value
    })

    // Transform backend response to frontend format
    searchResults.value = (response.results || []).map((result: any) => ({
      id: result.id,
      title: extractTitle(result),
      excerpt: formatExcerpt(result),
      documentType: result.metadata?.chunk_type || result.vector_type || 'document',
      date: result.metadata?.created_at || new Date().toISOString(),
      jurisdiction: 'N/A',
      relevanceScore: result.score,
      entities: [], // TODO: Extract from metadata
      caseNumber: result.metadata?.case_id ? `Case #${result.metadata.case_id}` : 'N/A',
      metadata: result.metadata,
      highlights: result.highlights
    }))
  } catch (error) {
    console.error('Search error:', error)
    searchResults.value = []
  } finally {
    isLoading.value = false
  }
}

// Extract title from result
function extractTitle(result: any): string {
  // Try to extract a meaningful title from the text
  const text = result.text || ''
  const lines = text.split('\n').filter((l: string) => l.trim())

  // Look for common title patterns
  if (lines.length > 0) {
    const firstLine = lines[0].trim()
    // If first line is short and in caps or has common document keywords, use it
    if (firstLine.length < 100 && (
      firstLine === firstLine.toUpperCase() ||
      /^(AGREEMENT|CONTRACT|NOTICE|LETTER|MEMORANDUM|REPORT)/i.test(firstLine)
    )) {
      return firstLine
    }
  }

  // Fallback to metadata or generic title
  return result.metadata?.title ||
         result.metadata?.filename ||
         `Document ${result.metadata?.document_id || result.id}`
}

// Format excerpt with highlights
function formatExcerpt(result: any): string {
  if (result.highlights && result.highlights.length > 0) {
    // Join highlights with ellipsis and add HTML marks
    return result.highlights
      .slice(0, 2)
      .map((h: string) => highlightText(h, searchQuery.value))
      .join(' ... ')
  }

  // Fallback to text snippet
  const text = result.text || ''
  const snippet = text.substring(0, 300).trim()
  return snippet ? highlightText(snippet, searchQuery.value) : 'No preview available'
}

// Highlight search terms in text
function highlightText(text: string, query: string): string {
  if (!query) return text

  const terms = query.toLowerCase().split(/\s+/)
  let highlighted = text

  terms.forEach(term => {
    if (term.length > 2) { // Only highlight terms longer than 2 chars
      const regex = new RegExp(`(${term})`, 'gi')
      highlighted = highlighted.replace(regex, '<mark class="bg-primary/20 text-primary font-medium">$1</mark>')
    }
  })

  return highlighted
}

// Debounced search
const debouncedSearch = useDebounceFn(performSearch, 300)

// Watch search query
watch(searchQuery, debouncedSearch)

// Keyboard shortcuts
const searchInput = useTemplateRef('searchInput')

defineShortcuts({
  '/': {
    handler: () => {
      searchInput.value?.inputRef?.focus()
    }
  },
  'meta_k': {
    usingInput: true,
    handler: () => {
      showSettings.value = !showSettings.value
    }
  }
})
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar :title="searchResults.length > 0 ? `Search Results (${searchResults.length})` : 'Search'">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #trailing>
          <div class="flex items-center gap-2">
            <UTooltip text="Search Settings (⌘K)">
              <UButton
                icon="i-lucide-settings"
                color="neutral"
                :variant="showSettings ? 'soft' : 'ghost'"
                @click="showSettings = !showSettings"
              />
            </UTooltip>
          </div>
        </template>
      </UDashboardNavbar>
    </template>

    <div class="flex h-[calc(100vh-64px)]">
      <!-- Main Content Area -->
      <div class="flex-1 overflow-y-auto">
        <!-- Hero Search (when not searching) -->
        <div
          v-if="searchResults.length === 0 && !searchQuery"
          class="flex items-center justify-center min-h-full px-6 py-12"
        >
          <div class="w-full max-w-4xl mx-auto text-center space-y-8">
            <!-- Logo/Icon -->
            <div class="flex items-center justify-center gap-4">
              <UIcon name="i-lucide-scale" class="size-16 text-primary" />
              <h1 class="text-6xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                LegalSearch AI
              </h1>
            </div>

            <p class="text-xl text-muted max-w-2xl mx-auto">
              Intelligent hybrid search across your legal documents, contracts, and case files
            </p>

            <!-- Hero Search Bar - Centered -->
            <div class="w-full max-w-3xl mx-auto">
              <UInput
                ref="searchInput"
                v-model="searchQuery"
                icon="i-lucide-search"
                placeholder="Search for legal terms, clauses, concepts, or natural language queries..."
                size="xl"
                :loading="isLoading"
                autofocus
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

        <!-- Search Results -->
        <div v-else class="p-6">
          <UContainer>
            <!-- Compact Search Bar -->
            <div class="mb-6">
              <UInput
                ref="searchInput"
                v-model="searchQuery"
                icon="i-lucide-search"
                placeholder="Search for legal terms, clauses, concepts..."
                size="lg"
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

            <!-- Results Header -->
            <div v-if="searchResults.length > 0" class="mb-6 flex items-center justify-between">
              <div class="flex items-center gap-3">
                <p class="text-sm text-muted">
                  About <span class="font-semibold text-highlighted">{{ searchResults.length }}</span> results
                </p>
                <UBadge :label="searchMode" color="primary" variant="soft" size="sm" />
                <UBadge v-if="searchSettings.fusion_method !== 'rrf'" :label="`Fusion: ${searchSettings.fusion_method}`" color="neutral" variant="outline" size="sm" />
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
            <div v-if="searchResults.length === 0 && !isLoading && searchQuery" class="text-center py-20">
              <UIcon name="i-lucide-search-x" class="size-20 text-muted mx-auto mb-6 opacity-30" />
              <h3 class="text-2xl font-semibold mb-3 text-highlighted">No results found</h3>
              <p class="text-muted mb-6 max-w-md mx-auto">
                We couldn't find any documents matching "{{ searchQuery }}".
                Try different keywords or switch search modes.
              </p>
              <div class="flex flex-wrap justify-center gap-2">
                <UButton
                  label="Try semantic search"
                  icon="i-lucide-sparkles"
                  color="neutral"
                  variant="outline"
                  @click="searchMode = 'semantic'"
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
              <UIcon name="i-lucide-loader-circle" class="size-12 text-primary animate-spin mb-4" />
              <p class="text-muted">Searching through documents...</p>
              <p class="text-sm text-dimmed mt-2">Using {{ searchMode }} search with {{ searchSettings.fusion_method.toUpperCase() }} fusion</p>
            </div>
          </UContainer>
        </div>
      </div>

      <!-- Settings Sidebar -->
      <div
        v-if="showSettings"
        class="w-80 border-l border-default bg-default overflow-y-auto p-6"
      >
        <div class="space-y-6">
          <div>
            <h3 class="font-semibold text-lg mb-1">Search Settings</h3>
            <p class="text-sm text-muted">Configure your search parameters</p>
          </div>

          <USeparator />

          <!-- Search Mode -->
          <UFormField label="Search Mode" help="Choose how to search your documents">
            <URadioGroup
              v-model="searchMode"
              :options="[
                { value: 'hybrid', label: 'Hybrid Search', description: 'BM25 + Semantic (Recommended)' },
                { value: 'semantic', label: 'Semantic Only', description: 'AI-powered meaning-based search' },
                { value: 'keyword', label: 'Keyword Only', description: 'Traditional BM25 keyword matching' }
              ]"
              :ui="{ fieldset: 'space-y-3' }"
            >
              <template #label="{ option }">
                <div>
                  <p class="font-medium">{{ option.label }}</p>
                  <p class="text-xs text-muted">{{ option.description }}</p>
                </div>
              </template>
            </URadioGroup>
          </UFormField>

          <USeparator />

          <!-- Fusion Method (only for hybrid) -->
          <UFormField
            v-if="searchMode === 'hybrid'"
            label="Fusion Method"
            help="How to combine BM25 and semantic results"
          >
            <USelectMenu
              v-model="searchSettings.fusion_method"
              :options="[
                { value: 'rrf', label: 'RRF (Reciprocal Rank Fusion)' },
                { value: 'weighted', label: 'Weighted Combination' },
                { value: 'max', label: 'Maximum Score' }
              ]"
              value-attribute="value"
            />
          </UFormField>

          <!-- Results Limit -->
          <UFormField label="Results Limit" help="Maximum number of results to return">
            <UInput
              v-model.number="searchSettings.top_k"
              type="number"
              min="5"
              max="100"
              step="5"
            />
          </UFormField>

          <USeparator />

          <!-- Info Card -->
          <UCard :ui="{ body: 'space-y-2' }">
            <div class="flex items-start gap-2">
              <UIcon name="i-lucide-info" class="size-5 text-primary shrink-0 mt-0.5" />
              <div class="text-sm">
                <p class="font-medium text-highlighted mb-1">Search Tips</p>
                <ul class="text-muted space-y-1 text-xs">
                  <li>• Use <strong>hybrid</strong> for best results</li>
                  <li>• Try <strong>semantic</strong> for concept searches</li>
                  <li>• Use <strong>keyword</strong> for exact terms</li>
                </ul>
              </div>
            </div>
          </UCard>
        </div>
      </div>
    </div>
  </UDashboardPanel>
</template>
