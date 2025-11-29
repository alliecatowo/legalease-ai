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

// Debounced search
const debouncedSearch = useDebounceFn(async () => {
  if (!searchQuery.value.trim()) {
    results.value = []
    totalFound.value = 0
    return
  }

  isSearching.value = true
  error.value = null

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
    error.value = err?.message || 'Search failed'
    results.value = []
  } finally {
    isSearching.value = false
  }
}, 300)

// Watch for search changes
watch([searchQuery, selectedCaseId, selectedDocumentType], () => {
  debouncedSearch()
})

function clearSearch() {
  searchQuery.value = ''
  results.value = []
  error.value = null
}

function getCaseName(caseId: string | undefined) {
  if (!caseId) return null
  const c = cases.value?.find(c => c.id === caseId)
  return c?.name
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Search">
        <template #trailing>
          <div v-if="searchTime || embeddingTime" class="flex items-center gap-3 text-sm text-muted">
            <span v-if="embeddingTime">Embed: {{ embeddingTime }}ms</span>
            <span v-if="searchTime">Search: {{ searchTime }}ms</span>
          </div>
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <div class="max-w-5xl mx-auto p-6 space-y-6">
        <!-- Search Header -->
        <div class="text-center space-y-4">
          <div class="flex items-center justify-center gap-3">
            <UIcon name="i-lucide-scale" class="size-10 text-primary" />
            <h1 class="text-3xl font-bold">Search Documents</h1>
          </div>
          <p class="text-muted">AI-powered semantic search across your legal documents</p>
        </div>

        <!-- Search Bar -->
        <div class="space-y-4">
          <UInput
            v-model="searchQuery"
            icon="i-lucide-search"
            placeholder="Search for legal terms, clauses, or concepts..."
            size="xl"
            :loading="isSearching"
            class="shadow-lg"
            @keyup.enter="debouncedSearch"
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

          <!-- Filters -->
          <div class="flex flex-wrap gap-4">
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

        <!-- Error -->
        <UAlert v-if="error" color="error" variant="subtle" :description="error" icon="i-lucide-alert-circle" />

        <!-- Results -->
        <div v-if="results.length > 0" class="space-y-4">
          <p class="text-sm text-muted">{{ totalFound }} results found</p>

          <div class="space-y-3">
            <UCard
              v-for="result in results"
              :key="result.id"
              class="cursor-pointer hover:shadow-md transition-shadow"
              @click="router.push(`/documents/${result.documentId}`)"
            >
              <div class="space-y-2">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <UIcon name="i-lucide-file-text" class="size-4 text-muted" />
                    <span class="font-medium">{{ result.metadata?.filename || 'Document' }}</span>
                  </div>
                  <UBadge
                    :label="`${Math.round(result.score * 100)}%`"
                    :color="result.score > 0.8 ? 'success' : result.score > 0.6 ? 'warning' : 'neutral'"
                    variant="soft"
                    size="sm"
                  />
                </div>

                <p class="text-sm text-muted line-clamp-3">{{ result.text }}</p>

                <div class="flex items-center gap-3 text-xs text-muted">
                  <span v-if="result.metadata?.pageNumber">Page {{ result.metadata.pageNumber }}</span>
                  <span v-if="getCaseName(result.metadata?.caseId)">{{ getCaseName(result.metadata?.caseId) }}</span>
                  <UBadge v-if="result.metadata?.documentType" :label="result.metadata.documentType" variant="outline" size="xs" />
                </div>
              </div>
            </UCard>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else-if="searchQuery && !isSearching" class="text-center py-16">
          <UIcon name="i-lucide-search-x" class="size-16 text-muted mx-auto mb-4 opacity-30" />
          <h3 class="text-xl font-semibold mb-2">No results found</h3>
          <p class="text-muted">Try adjusting your search terms or filters</p>
        </div>

        <!-- Initial State -->
        <div v-else-if="!searchQuery" class="text-center py-16">
          <UIcon name="i-lucide-search" class="size-16 text-muted mx-auto mb-4 opacity-30" />
          <h3 class="text-xl font-semibold mb-2">Start searching</h3>
          <p class="text-muted mb-8">Enter a search term to find documents</p>

          <div class="grid grid-cols-3 gap-4 max-w-lg mx-auto text-left">
            <UCard :ui="{ body: 'p-3' }">
              <UIcon name="i-lucide-zap" class="size-5 text-primary mb-1" />
              <p class="text-xs font-medium">Semantic</p>
              <p class="text-xs text-muted">Find by meaning</p>
            </UCard>
            <UCard :ui="{ body: 'p-3' }">
              <UIcon name="i-lucide-layers" class="size-5 text-primary mb-1" />
              <p class="text-xs font-medium">Vector</p>
              <p class="text-xs text-muted">AI embeddings</p>
            </UCard>
            <UCard :ui="{ body: 'p-3' }">
              <UIcon name="i-lucide-filter" class="size-5 text-primary mb-1" />
              <p class="text-xs font-medium">Filtered</p>
              <p class="text-xs text-muted">By case & type</p>
            </UCard>
          </div>
        </div>
      </div>
    </template>
  </UDashboardPanel>
</template>
