<script setup lang="ts">
// Import types from composable to avoid duplication
import type { BBox, DocumentContentItem, PageData } from '~/composables/useDocumentViewer'

interface SearchResult {
  chunk_id: number
  score: number
  text: string
  page_number?: number
  bboxes?: Array<BBox | { bbox: BBox, text?: string, page?: number }>
}

interface Props {
  documentId: number | string
  searchQuery?: string
  bm25Results?: SearchResult[] // BM25 keyword results (blue)
  fusionResults?: SearchResult[] // Fusion hybrid results (yellow)
  highlightBboxes?: BBox[]
  initialPage?: number
  chunkId?: number
}

const props = withDefaults(defineProps<Props>(), {
  searchQuery: '',
  bm25Results: () => [],
  fusionResults: () => [],
  highlightBboxes: () => [],
  initialPage: 1
})

const api = useApi()
const config = useRuntimeConfig()

// State
const pdfUrl = ref<string>('')
const currentPage = ref(props.initialPage)
const totalPages = ref(0)
const zoom = ref(1.0)
const isLoading = ref(true)
const error = ref<string | null>(null)
const pdfViewerRef = useTemplateRef('pdfViewerRef')

// Document content data
const documentContent = ref<{
  pages: PageData[]
  metadata: any
  text: string
} | null>(null)

// Computed
const currentPageData = computed(() => {
  if (!documentContent.value) return null
  return documentContent.value.pages.find(p => p.page_number === currentPage.value)
})

// Normalize bbox coordinates (handle both {l,t,r,b} and {x0,y0,x1,y1} formats)
const normalizeBBox = (bbox: BBox) => {
  if (bbox.l !== undefined) {
    const l = bbox.l
    const t = bbox.t ?? 0
    const r = bbox.r ?? l
    const b = bbox.b ?? t
    return {
      x: l,
      y: Math.min(t, b),
      width: Math.abs(r - l),
      height: Math.abs(b - t)
    }
  } else if (bbox.x0 !== undefined) {
    const x0 = bbox.x0
    const y0 = bbox.y0 ?? 0
    const x1 = bbox.x1 ?? x0
    const y1 = bbox.y1 ?? y0
    return {
      x: x0,
      y: Math.min(y0, y1),
      width: Math.abs(x1 - x0),
      height: Math.abs(y1 - y0)
    }
  }
  return { x: 0, y: 0, width: 0, height: 0 }
}

// Collect boxes from page-level and item-level bboxes
const collectBoxesForPage = (page: PageData) => {
  const out: Array<{ x: number, y: number, width: number, height: number, text?: string }> = []

  // Page-level bboxes
  for (const pb of page.bboxes || []) {
    const box = (pb as any).bbox ? (pb as any).bbox as BBox : (pb as any)
    const norm = normalizeBBox(box)
    out.push({ x: norm.x, y: norm.y, width: norm.width, height: norm.height, text: (pb as any).text })
  }

  // Item-level bboxes
  for (const item of page.items) {
    for (const entry of item.bboxes || []) {
      const box = (entry as any).bbox ? (entry as any).bbox as BBox : (entry as BBox)
      const norm = normalizeBBox(box)
      out.push({ x: norm.x, y: norm.y, width: norm.width, height: norm.height, text: (entry as any).text || item.text })
    }
  }

  return out
}

// Get search result highlights - BM25 (blue) and Fusion (yellow) separately
const allHighlights = computed(() => {
  const bm25Boxes: Array<{ x: number, y: number, width: number, height: number, text?: string, page: number, type: 'bm25' | 'semantic', score: number }> = []
  const fusionBoxes: Array<{ x: number, y: number, width: number, height: number, text?: string, page: number, type: 'bm25' | 'semantic', score: number }> = []
  const seenPositions = new Set<string>()

  // Collect BM25 boxes (blue) - up to 5 boxes
  for (const result of props.bm25Results || []) {
    const page = result.page_number || 1
    for (const entry of result.bboxes || []) {
      const box = (entry as any).bbox ? (entry as any).bbox as BBox : (entry as BBox)
      const nb = normalizeBBox(box)
      if (nb.width === 0 || nb.height === 0) continue

      const posKey = `${page}-${Math.round(nb.x)}-${Math.round(nb.y)}-${Math.round(nb.width)}-${Math.round(nb.height)}`
      if (seenPositions.has(posKey)) continue
      seenPositions.add(posKey)

      bm25Boxes.push({
        x: nb.x, y: nb.y, width: nb.width, height: nb.height,
        text: (entry as any).text || result.text,
        page,
        type: 'bm25', // BLUE
        score: result.score
      })
      if (bm25Boxes.length >= 5) break
    }
    if (bm25Boxes.length >= 5) break
  }

  // Collect Fusion boxes (yellow) - up to 5 boxes
  for (const result of props.fusionResults || []) {
    const page = result.page_number || 1
    for (const entry of result.bboxes || []) {
      const box = (entry as any).bbox ? (entry as any).bbox as BBox : (entry as BBox)
      const nb = normalizeBBox(box)
      if (nb.width === 0 || nb.height === 0) continue

      const posKey = `${page}-${Math.round(nb.x)}-${Math.round(nb.y)}-${Math.round(nb.width)}-${Math.round(nb.height)}`
      if (seenPositions.has(posKey)) continue
      seenPositions.add(posKey)

      fusionBoxes.push({
        x: nb.x, y: nb.y, width: nb.width, height: nb.height,
        text: (entry as any).text || result.text,
        page,
        type: 'semantic', // YELLOW
        score: result.score
      })
      if (fusionBoxes.length >= 5) break
    }
    if (fusionBoxes.length >= 5) break
  }

  // Combine: 5 BM25 + 5 Fusion = 10 total
  const out = [...bm25Boxes, ...fusionBoxes]

  console.log(`[DocumentViewer] ${bm25Boxes.length} BM25 (blue), ${fusionBoxes.length} fusion (yellow)`)
  return out
})

// Get text-based highlights (exact query matches) from document content
// Only highlight individual bboxes whose text contains the query (not whole items)
const textHighlights = computed(() => {
  if (!documentContent.value) return []
  const q = (props.searchQuery || '').toLowerCase().trim()
  if (!q) return []

  const out: Array<{ x: number, y: number, width: number, height: number, text?: string, page: number, type: 'text' }> = []

  for (const page of documentContent.value.pages) {
    for (const item of page.items) {
      for (const entry of item.bboxes || []) {
        const bboxText = (entry as any).text || ''

        // Only highlight this specific bbox if ITS text contains the query
        if (bboxText && bboxText.toLowerCase().includes(q)) {
          const box = (entry as any).bbox ? (entry as any).bbox as BBox : (entry as BBox)
          const nb = normalizeBBox(box)
          out.push({
            x: nb.x,
            y: nb.y,
            width: nb.width,
            height: nb.height,
            text: bboxText,
            page: page.page_number,
            type: 'text'
          })
        }
      }
    }
  }

  console.log(`[DocumentViewer] Text highlights: ${out.length}`)
  return out
})

// Just the highlights for the current page
const pageHighlights = computed(() => {
  return allHighlights.value.filter(h => h.page === currentPage.value)
})

// Build highlight rectangles for current page from item.bboxes
const currentPageHighlights = computed(() => {
  if (!currentPageData.value) return [] as Array<{ x: number, y: number, width: number, height: number, text?: string }>
  const results: Array<{ x: number, y: number, width: number, height: number, text?: string }> = []
  const q = (props.searchQuery || '').toLowerCase()

  const pushEntry = (entry: any, fallbackText?: string) => {
    const box = entry.bbox ? (entry.bbox as BBox) : (entry as BBox)
    const norm = normalizeBBox(box)
    results.push({ x: norm.x, y: norm.y, width: norm.width, height: norm.height, text: entry.text || fallbackText })
  }

  // Prefer bbox text matching when available
  if (q) {
    for (const item of currentPageData.value.items) {
      for (const entry of item.bboxes || []) {
        const t = (entry as any).text || item.text || ''
        if (t.toLowerCase().includes(q)) pushEntry(entry, item.text)
      }
    }
  }

  // Fallbacks
  if (results.length === 0) {
    if (props.chunkId) {
      const item = currentPageData.value.items.find(i => i.chunk_id === props.chunkId)
      if (item) (item.bboxes || []).forEach(e => pushEntry(e, item.text))
    }
    if (results.length === 0 && !q) {
      // No query: show all bboxes on page
      collectBoxesForPage(currentPageData.value).forEach(e => results.push(e))
    }
  }

  return results
})

function jumpToFirstMatch() {
  const q = (props.searchQuery || '').toLowerCase().trim()
  if (!q || !documentContent.value?.pages) return
  for (const p of documentContent.value.pages) {
    if (p.items?.some(it => (it.bboxes || []).some((e: any) => ((e.text || it.text || '').toLowerCase().includes(q))))) {
      currentPage.value = p.page_number
      break
    }
  }
}

// Fetch document content
const fetchDocumentContent = async () => {
  try {
    isLoading.value = true
    error.value = null

    // Fetch document content with bboxes
    const content = await api.documents.content(props.documentId.toString()) as {
      pages: PageData[]
      metadata: any
      text: string
      total_pages?: number
    }
    documentContent.value = content

    // Set PDF URL for download endpoint
    pdfUrl.value = `${config.public.apiBase}/api/v1/documents/${props.documentId}/download`

    totalPages.value = content.total_pages || content.pages?.length || 0

    jumpToFirstMatch()

    // Get accurate page count from PDF viewer after it loads
    setTimeout(() => {
      if (pdfViewerRef.value?.totalPages) {
        totalPages.value = pdfViewerRef.value.totalPages
      }
    }, 1000)
  } catch (e: any) {
    console.error('Error fetching document content:', e)
    error.value = e.message || 'Failed to load document'
  } finally {
    isLoading.value = false
  }
}

// Navigation
const goToPage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
  }
}

const nextPage = () => goToPage(currentPage.value + 1)
const prevPage = () => goToPage(currentPage.value - 1)

// Zoom
const zoomIn = () => {
  zoom.value = Math.min(zoom.value + 0.25, 3.0)
}

const zoomOut = () => {
  zoom.value = Math.max(zoom.value - 0.25, 0.5)
}

const resetZoom = () => {
  zoom.value = 1.0
}

// Print functionality
const handlePrint = () => {
  if (!pdfUrl.value) return
  // Open PDF in new window and trigger print dialog
  const printWindow = window.open(pdfUrl.value, '_blank')
  if (printWindow) {
    printWindow.addEventListener('load', () => {
      printWindow.print()
    })
  }
}

// Watch for query or content changes to rehighlight and jump to first match
watch([() => props.searchQuery, documentContent], () => {
  jumpToFirstMatch()
})

// Ensure we reset currentPage to initialPage on load or when props change
watch(() => props.initialPage, (p) => {
  currentPage.value = p || 1
})
watch(() => props.documentId, () => {
  currentPage.value = props.initialPage || 1
})

// Initialize
onMounted(() => {
  fetchDocumentContent()
})

// Watch for document ID changes
watch(() => props.documentId, () => {
  fetchDocumentContent()
})
</script>

<template>
  <div class="document-viewer relative">
    <!-- Toolbar -->
    <div class="viewer-toolbar bg-default border-b border-default p-3 flex items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <UButton
          icon="i-lucide-chevron-left"
          color="neutral"
          variant="ghost"
          size="sm"
          :disabled="currentPage <= 1"
          @click="prevPage"
        />
        <div class="flex items-center gap-2">
          <UInput
            v-model.number="currentPage"
            type="number"
            size="sm"
            class="w-16"
            :min="1"
            :max="totalPages"
            @change="goToPage(currentPage)"
          />
          <span class="text-sm text-muted">/ {{ totalPages }}</span>
        </div>
        <UButton
          icon="i-lucide-chevron-right"
          color="neutral"
          variant="ghost"
          size="sm"
          :disabled="currentPage >= totalPages"
          @click="nextPage"
        />
      </div>

      <div class="flex items-center gap-2">
        <UButton
          icon="i-lucide-zoom-out"
          color="neutral"
          variant="ghost"
          size="sm"
          :disabled="zoom <= 0.5"
          @click="zoomOut"
        />
        <UButton
          :label="`${Math.round(zoom * 100)}%`"
          color="neutral"
          variant="ghost"
          size="sm"
          @click="resetZoom"
        />
        <UButton
          icon="i-lucide-zoom-in"
          color="neutral"
          variant="ghost"
          size="sm"
          :disabled="zoom >= 3.0"
          @click="zoomIn"
        />
      </div>

      <div class="flex items-center gap-2">
        <UTooltip v-if="searchQuery && pageHighlights.length > 0" :text="`${allHighlights.length} total highlights across document`">
          <UBadge color="warning" variant="soft" size="sm">
            <template #leading>
              <UIcon name="i-lucide-search" class="size-3" />
            </template>
            {{ pageHighlights.length }} on this page
          </UBadge>
        </UTooltip>
        <UTooltip text="Print Document">
          <UButton
            icon="i-lucide-printer"
            color="neutral"
            variant="ghost"
            size="sm"
            @click="handlePrint"
          />
        </UTooltip>
        <UButton
          icon="i-lucide-refresh-cw"
          color="neutral"
          variant="ghost"
          size="sm"
          :loading="isLoading"
          @click="fetchDocumentContent"
        />
      </div>
    </div>

    <!-- PDF Viewer Container -->
    <div class="viewer-content relative bg-muted/5">
      <!-- Loading State -->
      <div v-if="isLoading" class="flex items-center justify-center h-full">
        <div class="text-center space-y-4">
          <UIcon name="i-lucide-loader-circle" class="size-12 text-primary animate-spin mx-auto" />
          <p class="text-muted">
            Loading document...
          </p>
        </div>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="flex items-center justify-center h-full">
        <UCard class="max-w-md">
          <div class="text-center space-y-4">
            <UIcon name="i-lucide-alert-circle" class="size-12 text-error mx-auto" />
            <h3 class="text-lg font-semibold">
              Failed to Load Document
            </h3>
            <p class="text-muted">
              {{ error }}
            </p>
            <UButton
              label="Retry"
              icon="i-lucide-refresh-cw"
              color="primary"
              @click="fetchDocumentContent"
            />
          </div>
        </UCard>
      </div>

      <!-- PDF with Overlay -->
      <div v-else class="pdf-wrapper">
        <LazyDocumentPDFViewerWithHighlights
          ref="pdfViewerRef"
          :document-url="pdfUrl"
          :page="currentPage"
          :zoom="zoom"
          :bounding-boxes="allHighlights.map((b, i) => ({
            id: String(i),
            page: b.page,
            x: b.x,
            y: b.y,
            width: b.width,
            height: b.height,
            text: b.text,
            type: b.type,
            entityType: b.type === 'bm25' ? 'BM25_MATCH' : 'SEMANTIC_MATCH'
          }))"
          @page-change="(p:number) => currentPage = p"
        />
      </div>
    </div>

    <!-- Page Info Footer -->
    <div v-if="currentPageData" class="viewer-footer border-t border-default p-3 bg-default">
      <div class="flex items-center justify-between text-sm">
        <div class="flex items-center gap-4">
          <span class="text-muted">
            Page {{ currentPage }} of {{ totalPages }}
          </span>
          <span v-if="currentPageData.items.length > 0" class="text-muted">
            {{ currentPageData.items.length }} elements
          </span>
        </div>
        <div v-if="pageHighlights.length > 0" class="text-warning">
          {{ pageHighlights.length }} highlighted
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.document-viewer {
  display: flex;
  flex-direction: column;
  height: 800px; /* Fixed height for the viewer - taller rectangle */
}

.viewer-toolbar {
  flex-shrink: 0;
}

.viewer-content {
  flex: 1;
  min-height: 0; /* Important for flex children with overflow */
  overflow: hidden;
}

.viewer-footer {
  flex-shrink: 0;
}

.pdf-page {
  display: block;
  width: 100%;
  height: auto;
  background: white;
}

.pdf-wrapper {
  width: 100%;
  height: 100%;
}

.bbox-overlay {
  z-index: 10;
}

.highlight-box {
  transition: all 0.2s ease;
}

.highlight-box:hover {
  fill: rgba(255, 235, 59, 0.5);
  stroke-width: 3;
}
</style>
