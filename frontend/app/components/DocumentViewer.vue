<script setup lang="ts">
import VuePdfEmbed from 'vue-pdf-embed'

interface BBox {
  l?: number
  t?: number
  r?: number
  b?: number
  x0?: number
  y0?: number
  x1?: number
  y1?: number
}

interface DocumentItem {
  text: string
  type: string
  bboxes?: Array<BBox | { bbox: BBox; text?: string; page?: number }>
  chunk_id?: number
}

interface PageData {
  page_number: number
  text: string
  items: DocumentItem[]
  bboxes?: Array<BBox | { bbox?: BBox; x0?: number; y0?: number; x1?: number; y1?: number; text?: string }>
}

interface Props {
  documentId: number | string
  searchQuery?: string
  highlightBboxes?: BBox[]
  initialPage?: number
  chunkId?: number
}

const props = withDefaults(defineProps<Props>(), {
  searchQuery: '',
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
const pdfContainer = useTemplateRef('pdfContainer')
const pdfEmbed = useTemplateRef('pdfEmbed')

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


// Simple, cohesive highlight list from item.bboxes only
const pageHighlights = computed(() => {
  const page = currentPageData.value
  if (!page) return [] as Array<{ x: number; y: number; width: number; height: number; text?: string }>
  const q = (props.searchQuery || '').toLowerCase().trim()
  const out: Array<{ x: number; y: number; width: number; height: number; text?: string }> = []
  for (const item of page.items) {
    for (const entry of item.bboxes || []) {
      const t = (entry as any).text || item.text || ''
      if (!q || t.toLowerCase().includes(q)) {
        const box = (entry as any).bbox ? (entry as any).bbox as BBox : (entry as BBox)
        const nb = normalizeBBox(box)
        out.push({ x: nb.x, y: nb.y, width: nb.width, height: nb.height, text: t })
      }
    }
  }
  return out
})


// Build highlight rectangles for current page from item.bboxes
const currentPageHighlights = computed(() => {
  if (!currentPageData.value) return [] as Array<{ x: number; y: number; width: number; height: number; text?: string }>
  const results: Array<{ x: number; y: number; width: number; height: number; text?: string }> = []
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

// Collect boxes from page-level and item-level
const collectBoxesForPage = (page: PageData) => {
  const out: Array<{ x: number; y: number; width: number; height: number; text?: string }> = []
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

// Ensure we reset currentPage to initialPage on load or when props change
watch(() => props.initialPage, (p) => { currentPage.value = p || 1 })
watch(() => props.documentId, () => { currentPage.value = props.initialPage || 1 })

  return out
}

  return results
})

  // Log sizing and first box for debug
  if (documentContent.value?.pages?.length) {
    const p = documentContent.value.pages[0]
    const first = p.items.find(i => (i.bboxes||[]).length)?.bboxes?.[0] as any
    if (first?.bbox) {
      const nb = normalizeBBox(first.bbox)
      console.debug('First bbox (normalized):', nb)
    }
  }


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

// Build highlight rectangles for current page from item.bboxes
const currentPageHighlights = computed(() => {
  if (!currentPageData.value) return [] as Array<{ x: number; y: number; width: number; height: number; text?: string }>
  const results: Array<{ x: number; y: number; width: number; height: number; text?: string }> = []
  const query = (props.searchQuery || '').toLowerCase()

  for (const item of currentPageData.value.items) {
    // Skip items that don't match search when a query is provided
    if (query && !(item.text && item.text.toLowerCase().includes(query))) continue

    const boxes = item.bboxes || []
    for (const entry of boxes) {

  // If chunkId provided, set page to the item's page when found
  if (props.chunkId && currentPageData.value) {
    const pageIdx = documentContent.value?.pages.findIndex(p => p.items.some(i => i.chunk_id === props.chunkId))
    if (pageIdx !== undefined && pageIdx >= 0) {
      currentPage.value = documentContent.value!.pages[pageIdx].page_number
    }
  }

      const box = (entry as any).bbox ? (entry as any).bbox as BBox : (entry as BBox)
      const norm = normalizeBBox(box)
      results.push({ x: norm.x, y: norm.y, width: norm.width, height: norm.height, text: (entry as any).text || item.text })
    }
  }

  return results
})

  } catch (e: any) {
    console.error('Error fetching document content:', e)
    error.value = e.message || 'Failed to load document'
  } finally {
    isLoading.value = false
  }
}

// PDF events
const onPdfLoaded = (pdf: any) => {
  console.log('PDF loaded:', pdf)
  if (pdf.numPages) {
    totalPages.value = pdf.numPages
  }
}

const onPdfError = (e: any) => {
  console.error('PDF loading error:', e)
  error.value = 'Failed to load PDF'
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

// Watch for query or content changes to rehighlight and jump to first match
watch([() => props.searchQuery, documentContent], () => {
  // Jump to page that contains first item matching query
  const q = (props.searchQuery || '').toLowerCase()
  if (!q || !documentContent.value) return
  for (const page of documentContent.value.pages) {
    if (page.items.some(i => i.text?.toLowerCase().includes(q))) {
      currentPage.value = page.page_number
      break
    }
  }
})

}

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
    <div class="viewer-toolbar sticky top-0 z-10 bg-default border-b border-default p-3 flex items-center justify-between gap-3">
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
        <UTooltip v-if="searchQuery" text="Highlighting search results">
          <UBadge color="warning" variant="soft" size="sm">
            <template #leading>
              <UIcon name="i-lucide-search" class="size-3" />
            </template>
            {{ pageHighlights.length }} highlights
          </UBadge>
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

      <div class="mb-2 text-xs text-muted">
        <span>PDF: {{ Math.round(pageWidth) }}x{{ Math.round(pageHeight) }} | Boxes: {{ pageHighlights.length }}</span>
      </div>
      </div>
    </div>

    <!-- PDF Viewer Container -->
    <div
      ref="pdfContainer"
      class="viewer-content relative overflow-auto bg-muted/5 p-6"
      style="height: calc(100vh - 200px);"
    >
      <!-- Loading State -->
      <div v-if="isLoading" class="flex items-center justify-center h-full">
        <div class="text-center space-y-4">
          <UIcon name="i-lucide-loader-circle" class="size-12 text-primary animate-spin mx-auto" />
          <p class="text-muted">Loading document...</p>
        </div>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="flex items-center justify-center h-full">
        <UCard class="max-w-md">
          <div class="text-center space-y-4">
            <UIcon name="i-lucide-alert-circle" class="size-12 text-error mx-auto" />
            <h3 class="text-lg font-semibold">Failed to Load Document</h3>
            <p class="text-muted">{{ error }}</p>
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
      <div v-else class="pdf-wrapper relative inline-block mx-auto shadow-lg">
          <g>
            <rect
              v-for="(box, idx) in pageHighlights"
              :key="`bg-${idx}`"
              :x="box.x"
              :y="box.y"
              :width="box.width"
              :height="box.height"
              fill="rgba(255, 235, 59, 0.20)"
              stroke="none"
            />
            <rect
              v-for="(box, idx) in pageHighlights"
              :key="`fg-${idx}`"
              :x="box.x"
              :y="box.y"
              :width="box.width"
              :height="box.height"
              fill="none"
              stroke="rgba(255, 193, 7, 0.9)"
              stroke-width="2"
              rx="2"
            />
          </g>
        <VuePdfEmbed
          ref="pdfEmbed"
          :source="pdfUrl"
          :page="currentPage"
          class="pdf-page"
          :style="{ transform: `scale(${zoom})`, transformOrigin: 'top left' }"
          @loaded="onPdfLoaded"
          @loading-failed="onPdfError"
        />

        <!-- SVG Overlay for Bounding Boxes -->
        <svg
          v-if="pageHighlights.length > 0"
          class="bbox-overlay absolute top-0 left-0 w-full h-full pointer-events-none"
          :style="{ transform: `scale(${zoom})`, transformOrigin: 'top left' }"
        >
          <rect
            v-for="(box, idx) in pageHighlights"
            :key="idx"
            :x="box.x"
            :y="box.y"
            :width="box.width"
            :height="box.height"
            class="highlight-box"
            fill="rgba(255, 235, 59, 0.3)"
            stroke="rgba(255, 235, 59, 0.8)"
            stroke-width="2"
            rx="2"
          >
            <title>{{ (box.text || '').substring(0, 100) }}</title>
          </rect>
        </svg>
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
.pdf-page {
  display: block;
  max-width: 100%;
  background: white;
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

.viewer-content {
  display: flex;
  align-items: flex-start;
  justify-content: center;
}

.pdf-wrapper {
  position: relative;
  background: white;
}
</style>
