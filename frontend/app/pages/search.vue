<script setup lang="ts">
definePageMeta({
  layout: 'default'
})

const api = useApi()
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const isLoading = ref(false)
const isSearching = ref(false) // Track if search is in progress
const showSettings = ref(false)

// Search settings
const searchMode = ref<'hybrid' | 'semantic' | 'keyword'>('hybrid')
const searchSettings = ref({
  use_bm25: true,
  use_dense: true,
  fusion_method: 'rrf' as 'rrf' | 'weighted' | 'max',
  top_k: 50, // Increased from 20 to fetch more results
  chunk_types: [] as string[], // Filter by chunk types
  document_ids: [] as number[], // Filter by document IDs
  case_ids: [] as number[] // Filter by case IDs
})

// Case filters - fetch available cases
const { data: casesData } = await useAsyncData('search-cases', () => api.cases.list(), {
  default: () => ({ cases: [], total: 0, page: 1, page_size: 50 })
})
const availableCases = computed(() =>
  (casesData.value?.cases || []).map((c: any) => ({
    id: Number(c.id),
    name: c.name,
    label: c.name,
    case_number: c.case_number
  }))
)

// Filter state
const selectedCases = ref<number[]>([])
const selectedDocumentTypes = ref<string[]>([])
const selectedSpeakers = ref<string[]>([])
const includeTranscripts = ref(true)

const documentTypeOptions = [
  { value: 'contract', label: 'Contracts', icon: 'i-lucide-file-text' },
  { value: 'court_filing', label: 'Court Filings', icon: 'i-lucide-gavel' },
  { value: 'transcript', label: 'Transcripts', icon: 'i-lucide-mic' },
  { value: 'brief', label: 'Briefs', icon: 'i-lucide-file-pen' },
  { value: 'motion', label: 'Motions', icon: 'i-lucide-file-check' },
  { value: 'correspondence', label: 'Correspondence', icon: 'i-lucide-mail' }
]

// Chunk type filters
const selectedChunkTypes = ref<string[]>([])
const chunkTypeOptions = [
  { value: 'summary', label: 'Summaries', description: 'Document overviews' },
  { value: 'section', label: 'Sections', description: 'Major document sections' },
  { value: 'microblock', label: 'Microblocks', description: 'Detailed paragraphs' },
  { value: 'paragraph', label: 'Paragraphs', description: 'Individual paragraphs' },
  { value: 'page', label: 'Pages', description: 'Full pages' }
]

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
    isSearching.value = false
    return
  }

  isLoading.value = true
  isSearching.value = true
  try {
    // Filter out null/undefined values and convert to integers
    const validCaseIds = selectedCases.value.filter(id => id != null).map(id => Number(id))

    // Build search request with filters
    const request = {
      query: searchQuery.value,
      use_bm25: searchSettings.value.use_bm25,
      use_dense: searchSettings.value.use_dense,
      fusion_method: searchSettings.value.fusion_method,
      top_k: searchSettings.value.top_k,
      chunk_types: selectedChunkTypes.value.length > 0 ? selectedChunkTypes.value : undefined,
      case_ids: validCaseIds.length > 0 ? validCaseIds : undefined,
      document_ids: searchSettings.value.document_ids.length > 0 ? searchSettings.value.document_ids : undefined
    }

    // DEBUG: Log search request details
    console.log('🔍 Search Request Debug:')
    console.log('  selectedCases.value:', selectedCases.value)
    console.log('  selectedChunkTypes.value:', selectedChunkTypes.value)
    console.log('  Full request object:', JSON.stringify(request, null, 2))

    // Use hybrid endpoint by default
    const response = await api.search.hybrid(request)

    // Transform backend response to frontend format
    let results = (response.results || []).map((result: any) => ({
      id: result.id,
      title: extractTitle(result),
      excerpt: formatExcerpt(result),
      documentType: determineDocumentType(result),
      date: result.metadata?.created_at || result.metadata?.uploaded_at || new Date().toISOString(),
      jurisdiction: result.metadata?.jurisdiction || null,
      relevanceScore: result.score,
      entities: extractEntities(result.metadata), // Extract from metadata
      caseNumber: result.metadata?.case_id ? `Case #${result.metadata.case_id}` : null,
      metadata: result.metadata,
      highlights: result.highlights,
      vectorType: result.vector_type, // Pass through for highlighting logic
      chunkType: result.metadata?.chunk_type,
      pageNumber: result.metadata?.page_number,
      filename: result.metadata?.filename
    }))

    // Client-side filter by document type if selected
    if (selectedDocumentTypes.value.length > 0) {
      results = results.filter(r => selectedDocumentTypes.value.includes(r.documentType))
    }

    // Filter transcripts if not included
    if (!includeTranscripts.value) {
      results = results.filter(r => r.documentType !== 'transcript' && r.chunkType !== 'transcript_segment')
    }

    searchResults.value = results
  } catch (error) {
    console.error('Search error:', error)
    searchResults.value = []
  } finally {
    isLoading.value = false
    isSearching.value = false
  }
}

// Determine document type from metadata
function determineDocumentType(result: any): string {
  // Priority: explicit document_type > inferred from filename > chunk_type > default
  if (result.metadata?.document_type) {
    return result.metadata.document_type
  }

  // Infer from filename
  const filename = (result.metadata?.filename || '').toLowerCase()
  if (filename.includes('contract') || filename.includes('agreement')) return 'contract'
  if (filename.includes('filing') || filename.includes('complaint')) return 'court_filing'
  if (filename.includes('transcript')) return 'transcript'
  if (filename.includes('brief')) return 'brief'
  if (filename.includes('motion')) return 'motion'
  if (filename.includes('email') || filename.includes('letter')) return 'correspondence'

  // Fallback to chunk type or generic
  return result.metadata?.chunk_type || 'document'
}

// Extract entities from metadata
function extractEntities(metadata: any): Array<{ type: string; text: string }> {
  if (!metadata) return []

  const entities: Array<{ type: string; text: string }> = []

  // Extract from various metadata fields
  if (metadata.entities && Array.isArray(metadata.entities)) {
    entities.push(...metadata.entities)
  }

  // Extract parties as PERSON entities
  if (metadata.parties && Array.isArray(metadata.parties)) {
    metadata.parties.forEach((party: string) => {
      entities.push({ type: 'PERSON', text: party })
    })
  }

  // Extract court as COURT entity
  if (metadata.court) {
    entities.push({ type: 'COURT', text: metadata.court })
  }

  // Extract dates
  if (metadata.filing_date) {
    entities.push({ type: 'DATE', text: new Date(metadata.filing_date).toLocaleDateString() })
  }

  return entities
}

// Extract title from result with enhanced logic
function extractTitle(result: any): string {
  const metadata = result.metadata || {}

  // Priority 1: Explicit title from metadata
  if (metadata.title && metadata.title.length > 3) {
    return metadata.title
  }

  // Priority 2: Filename without extension
  if (metadata.filename) {
    const filename = metadata.filename.replace(/\.(pdf|docx?|txt)$/i, '')
    // Clean up common patterns like underscores, dates
    const cleaned = filename
      .replace(/_/g, ' ')
      .replace(/\d{4}-\d{2}-\d{2}/g, '') // Remove ISO dates
      .replace(/\s+/g, ' ')
      .trim()

    if (cleaned.length > 3) {
      return cleaned
    }
  }

  // Priority 3: Extract from first line of text
  const text = result.text || ''
  const lines = text.split('\n').filter((l: string) => l.trim())

  if (lines.length > 0) {
    const firstLine = lines[0].trim()

    // Check for common legal document headers
    const legalHeaders = /^(AGREEMENT|CONTRACT|NOTICE|LETTER|MEMORANDUM|MEMO|REPORT|ORDER|MOTION|BRIEF|COMPLAINT|PETITION|AFFIDAVIT|DECLARATION|DEPOSITION|TRANSCRIPT)/i

    if (firstLine.length < 150) {
      // If it matches legal header pattern, use it
      if (legalHeaders.test(firstLine)) {
        return firstLine
      }

      // If it's all caps or title case and short, likely a header
      const isAllCaps = firstLine === firstLine.toUpperCase() && firstLine.length > 5
      const hasCapitalizedWords = /^[A-Z][a-z]+(?: [A-Z][a-z]+)*/.test(firstLine)

      if (isAllCaps || hasCapitalizedWords) {
        return firstLine
      }
    }

    // Look at second line if first is too generic
    if (lines.length > 1 && firstLine.length < 30) {
      const secondLine = lines[1].trim()
      if (secondLine.length > 10 && secondLine.length < 150) {
        return `${firstLine} - ${secondLine}`
      }
    }
  }

  // Priority 4: Use chunk type and document ID
  const chunkType = metadata.chunk_type || 'Section'
  const docId = metadata.document_id || result.id

  return `${chunkType.charAt(0).toUpperCase() + chunkType.slice(1)} from Document #${docId}`
}

// Format excerpt with highlights - dual color for keyword vs semantic
function formatExcerpt(result: any): string {
  const isKeywordMatch = result.vector_type === 'bm25' || searchMode.value === 'keyword'
  const isSemanticMatch = result.vector_type !== 'bm25' || searchMode.value === 'semantic'

  if (result.highlights && result.highlights.length > 0) {
    // Join highlights with ellipsis
    return result.highlights
      .slice(0, 3) // Show up to 3 highlights
      .map((h: string) => highlightText(h, searchQuery.value, isKeywordMatch, isSemanticMatch))
      .join(' <span class="text-dimmed">...</span> ')
  }

  // Fallback to text snippet
  const text = result.text || ''
  // Try to find a good snippet around keywords
  const snippet = findBestSnippet(text, searchQuery.value)
  return snippet ? highlightText(snippet, searchQuery.value, isKeywordMatch, isSemanticMatch) : '<span class="text-muted italic">No preview available</span>'
}

// Find best snippet containing search terms
function findBestSnippet(text: string, query: string, maxLength = 400): string {
  if (!text) return ''

  const terms = query.toLowerCase().split(/\s+/).filter(t => t.length > 2)
  if (terms.length === 0) {
    return text.substring(0, maxLength).trim() + (text.length > maxLength ? '...' : '')
  }

  // Find first occurrence of any term
  const lowerText = text.toLowerCase()
  let bestIndex = -1
  let bestTerm = ''

  for (const term of terms) {
    const index = lowerText.indexOf(term)
    if (index !== -1 && (bestIndex === -1 || index < bestIndex)) {
      bestIndex = index
      bestTerm = term
    }
  }

  if (bestIndex === -1) {
    // No terms found, return beginning
    return text.substring(0, maxLength).trim() + (text.length > maxLength ? '...' : '')
  }

  // Extract snippet around the term
  const snippetStart = Math.max(0, bestIndex - 100)
  const snippetEnd = Math.min(text.length, bestIndex + bestTerm.length + 300)
  let snippet = text.substring(snippetStart, snippetEnd).trim()

  // Add ellipsis if needed
  if (snippetStart > 0) snippet = '...' + snippet
  if (snippetEnd < text.length) snippet = snippet + '...'

  return snippet
}

// Advanced highlighting with dual colors: yellow for keywords, blue for semantic
function highlightText(text: string, query: string, isKeywordMatch: boolean, isSemanticMatch: boolean): string {
  if (!query) return text

  const terms = query.toLowerCase().split(/\s+/)
  let highlighted = text

  // Escape special regex characters in terms
  const escapeRegex = (str: string) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

  terms.forEach(term => {
    if (term.length > 2) { // Only highlight terms longer than 2 chars
      const escapedTerm = escapeRegex(term)
      const regex = new RegExp(`(${escapedTerm})`, 'gi')

      // Choose highlight color based on match type
      if (isKeywordMatch && !isSemanticMatch) {
        // Pure keyword match - yellow/amber
        highlighted = highlighted.replace(regex, '<mark class="bg-warning/30 text-warning-600 dark:text-warning-400 font-medium px-0.5 rounded">$1</mark>')
      } else if (isSemanticMatch && !isKeywordMatch) {
        // Pure semantic match - blue/primary
        highlighted = highlighted.replace(regex, '<mark class="bg-primary/20 text-primary-600 dark:text-primary-400 font-medium px-0.5 rounded">$1</mark>')
      } else {
        // Hybrid match - gradient or purple
        highlighted = highlighted.replace(regex, '<mark class="bg-gradient-to-r from-warning/30 to-primary/20 text-highlighted font-semibold px-0.5 rounded">$1</mark>')
      }
    }
  })

  return highlighted
}

// Debounced search - increased to 500ms for better UX
const debouncedSearch = useDebounceFn(performSearch, 500)

// Watch search query
watch(searchQuery, () => {
  // Set isSearching immediately when user types
  if (searchQuery.value.trim()) {
    isSearching.value = true
  }
  debouncedSearch()
})

// Keyboard shortcuts - manage two refs for hero and compact inputs
const heroSearchInput = useTemplateRef('heroSearchInput')
const compactSearchInput = useTemplateRef('compactSearchInput')

// Helper to focus the visible input
const focusVisibleInput = () => {
  if (searchResults.value.length > 0 || isSearching.value) {
    // Results view is visible, focus compact input
    compactSearchInput.value?.inputRef?.focus()
  } else {
    // Hero view is visible, focus hero input
    heroSearchInput.value?.inputRef?.focus()
  }
}

// Watch for view changes and transfer focus
watch([searchResults, isSearching], ([results, searching]) => {
  if (searching || results.length > 0) {
    // Switching to results view - transfer focus to compact input
    nextTick(() => {
      compactSearchInput.value?.inputRef?.focus()
    })
  }
})

defineShortcuts({
  '/': {
    usingInput: false,
    handler: () => {
      focusVisibleInput()
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

    <template #body>
      <div class="flex h-full">
        <!-- Main Content Area -->
        <div class="flex-1 overflow-y-auto">
          <!-- Hero Search (when not searching or no results yet) -->
          <div
            v-show="searchResults.length === 0 && !isSearching"
            class="flex items-center justify-center min-h-full px-6 py-12"
          >
            <div class="w-full max-w-5xl mx-auto text-center space-y-12">
              <!-- Logo/Icon -->
              <div class="flex items-center justify-center gap-5">
                <UIcon name="i-lucide-scale" class="size-20 text-primary" />
                <h1 class="text-7xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent tracking-tight">
                  LegalEase AI
                </h1>
              </div>

              <p class="text-xl text-muted max-w-2xl mx-auto">
                Intelligent hybrid search across your legal documents, contracts, and case files
              </p>

              <!-- Hero Search Bar - Centered and Large -->
              <div class="w-full max-w-5xl mx-auto space-y-6">
                <UInput
                  ref="heroSearchInput"
                  v-model="searchQuery"
                  icon="i-lucide-search"
                  placeholder="Search for legal terms, clauses, concepts, or natural language queries..."
                  size="xl"
                  :loading="isLoading"
                  autofocus
                  class="!text-lg shadow-xl hover:shadow-2xl transition-shadow"
                  :ui="{
                    base: 'px-6 py-5 text-lg rounded-2xl',
                    leadingIcon: 'size-7'
                  }"
                >
                  <template #trailing>
                    <UKbd value="/" />
                  </template>
                </UInput>

                <!-- Prominent Filter Bar in Hero View -->
                <div class="flex justify-center">
                  <SearchFilters
                    v-model:selected-cases="selectedCases"
                    v-model:selected-document-types="selectedDocumentTypes"
                    v-model:selected-chunk-types="selectedChunkTypes"
                    :available-cases="availableCases"
                    :show-chunk-types="true"
                    @clear="selectedCases = []; selectedDocumentTypes = []; selectedChunkTypes = []"
                  />
                </div>
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
          <div v-show="searchResults.length > 0 || isSearching" class="p-6">
            <UContainer>
              <!-- Compact Search Bar (kept in DOM to prevent focus loss) -->
              <div class="mb-6 space-y-3">
              <UInput
                ref="compactSearchInput"
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

              <!-- Filter Bar - Always Visible in Results View -->
              <SearchFilters
                v-model:selected-cases="selectedCases"
                v-model:selected-document-types="selectedDocumentTypes"
                v-model:selected-chunk-types="selectedChunkTypes"
                :available-cases="availableCases"
                :show-chunk-types="true"
                :is-compact="true"
                @clear="selectedCases = []; selectedDocumentTypes = []; selectedChunkTypes = []"
              />
            </div>

            <!-- Results Header -->
            <div v-if="searchResults.length > 0" class="mb-6 flex items-center gap-3 flex-wrap">
              <p class="text-sm text-muted">
                About <span class="font-semibold text-highlighted">{{ searchResults.length }}</span> results
              </p>
              <UBadge :label="searchMode" color="primary" variant="soft" size="sm" />
              <UBadge v-if="searchSettings.fusion_method !== 'rrf'" :label="`Fusion: ${searchSettings.fusion_method}`" color="neutral" variant="outline" size="sm" />
            </div>

            <!-- Search Results List -->
            <div class="space-y-4 max-w-5xl">
              <SearchResultCard
                v-for="result in searchResults"
                :key="`${result.id}-${result.metadata?.chunk_id || result.pageNumber}`"
                :result="result" :query="searchQuery"
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

          <USeparator />

          <!-- Case Filter -->
          <UFormField label="Cases" help="Filter results by specific cases">
            <div class="space-y-2 max-h-48 overflow-y-auto">
              <UCheckbox
                v-for="case_ in availableCases"
                :key="case_.id"
                v-model="selectedCases"
                :value="case_.id"
              >
                <template #label>
                  <div class="flex flex-col">
                    <span class="font-medium text-sm">{{ case_.name }}</span>
                    <span class="text-xs text-muted">{{ case_.case_number }}</span>
                  </div>
                </template>
              </UCheckbox>
              <div v-if="availableCases.length === 0" class="text-sm text-muted py-2">
                No cases available
              </div>
            </div>
          </UFormField>

          <USeparator />

          <!-- Document Type Filter -->
          <UFormField label="Document Types" help="Filter results by document type">
            <div class="space-y-2">
              <UCheckbox
                v-for="option in documentTypeOptions"
                :key="option.value"
                v-model="selectedDocumentTypes"
                :value="option.value"
                :label="option.label"
              >
                <template #label>
                  <div class="flex items-center gap-2">
                    <UIcon :name="option.icon" class="size-4" />
                    <span>{{ option.label }}</span>
                  </div>
                </template>
              </UCheckbox>
            </div>
          </UFormField>

          <USeparator />

          <!-- Chunk Type Filter -->
          <UFormField label="Content Granularity" help="Filter by content chunk size">
            <div class="space-y-2">
              <UCheckbox
                v-for="option in chunkTypeOptions"
                :key="option.value"
                v-model="selectedChunkTypes"
                :value="option.value"
              >
                <template #label>
                  <div class="flex flex-col">
                    <span class="font-medium">{{ option.label }}</span>
                    <span class="text-xs text-muted">{{ option.description }}</span>
                  </div>
                </template>
              </UCheckbox>
            </div>
          </UFormField>

          <USeparator />

          <!-- Include Transcripts Toggle -->
          <UFormField label="Transcripts" help="Include or exclude audio transcripts from search results">
            <UCheckbox
              v-model="includeTranscripts"
              label="Include Transcripts in Results"
            >
              <template #label>
                <div class="flex items-center gap-2">
                  <UIcon name="i-lucide-mic" class="size-4" />
                  <span>Include Transcripts</span>
                </div>
              </template>
            </UCheckbox>
          </UFormField>

          <USeparator />

          <!-- Active Filters Summary -->
          <div v-if="selectedCases.length > 0 || selectedDocumentTypes.length > 0 || selectedChunkTypes.length > 0 || !includeTranscripts" class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-highlighted">Active Filters</span>
              <UButton
                label="Clear All"
                color="neutral"
                variant="ghost"
                size="xs"
                @click="selectedCases = []; selectedDocumentTypes = []; selectedChunkTypes = []; includeTranscripts = true"
              />
            </div>
            <div class="flex flex-wrap gap-1.5">
              <UBadge
                v-for="caseId in selectedCases"
                :key="caseId"
                :label="availableCases.find(c => c.id === caseId)?.name || `Case #${caseId}`"
                color="secondary"
                variant="soft"
                size="sm"
                @click="selectedCases = selectedCases.filter(id => id !== caseId)"
              >
                <template #trailing>
                  <UIcon name="i-lucide-x" class="size-3 cursor-pointer" />
                </template>
              </UBadge>
              <UBadge
                v-for="type in selectedDocumentTypes"
                :key="type"
                :label="documentTypeOptions.find(o => o.value === type)?.label || type"
                color="primary"
                variant="soft"
                size="sm"
                @click="selectedDocumentTypes = selectedDocumentTypes.filter(t => t !== type)"
              >
                <template #trailing>
                  <UIcon name="i-lucide-x" class="size-3 cursor-pointer" />
                </template>
              </UBadge>
              <UBadge
                v-for="type in selectedChunkTypes"
                :key="type"
                :label="chunkTypeOptions.find(o => o.value === type)?.label || type"
                color="info"
                variant="soft"
                size="sm"
                @click="selectedChunkTypes = selectedChunkTypes.filter(t => t !== type)"
              >
                <template #trailing>
                  <UIcon name="i-lucide-x" class="size-3 cursor-pointer" />
                </template>
              </UBadge>
              <UBadge
                v-if="!includeTranscripts"
                label="Exclude Transcripts"
                color="warning"
                variant="soft"
                size="sm"
                @click="includeTranscripts = true"
              >
                <template #leading>
                  <UIcon name="i-lucide-mic-off" class="size-3" />
                </template>
                <template #trailing>
                  <UIcon name="i-lucide-x" class="size-3 cursor-pointer" />
                </template>
              </UBadge>
            </div>
          </div>

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
                  <li>• <span class="bg-warning/30 px-1 rounded">Yellow</span> = Keyword match</li>
                  <li>• <span class="bg-primary/20 px-1 rounded">Blue</span> = Semantic match</li>
                </ul>
              </div>
            </div>
          </UCard>
          </div>
        </div>
      </div>
    </template>
  </UDashboardPanel>
</template>
