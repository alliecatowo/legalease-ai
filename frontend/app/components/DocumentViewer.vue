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
  bbox?: BBox
  bboxes?: Array<BBox | { bbox: BBox; text?: string; page?: number }>
  chunk_id?: number
}

interface PageData {
  page_number: number
  text: string
  items: DocumentItem[]
}

interface Props {
  documentId: number | string
  searchQuery?: string
  highlightBboxes?: BBox[]
  initialPage?: number
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

// Normalize bbox coordinates (handle both {l,t,r,b} and {x0,y0,x1,y1} formats)
const normalizeBBox = (bbox: BBox) => {
  if (bbox.l !== undefined) {
    return {
      x: bbox.l,
      y: bbox.t || 0,
      width: (bbox.r || 0) - bbox.l,
      height: (bbox.b || 0) - (bbox.t || 0)
    }
  } else if (bbox.x0 !== undefined) {
    return {
      x: bbox.x0,
      y: bbox.y0 || 0,
      width: (bbox.x1 || 0) - bbox.x0,
      height: (bbox.y1 || 0) - (bbox.y0 || 0)
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

    const boxes = item.bboxes || (item.bbox ? [item.bbox] : [])
    for (const entry of boxes) {
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
            {{ currentPageHighlights.length }} highlights
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
          v-if="currentPageHighlights.length > 0"
          class="bbox-overlay absolute top-0 left-0 w-full h-full pointer-events-none"
          :style="{ transform: `scale(${zoom})`, transformOrigin: 'top left' }"
        >
          <rect
            v-for="(box, idx) in currentPageHighlights"
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
        <div v-if="currentPageHighlights.length > 0" class="text-warning">
          {{ currentPageHighlights.length }} highlighted
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
