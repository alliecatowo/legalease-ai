<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { VuePDF, usePDF } from '@tato30/vue-pdf'
import '@tato30/vue-pdf/style.css'

interface BoundingBox {
  id?: string
  page: number
  x: number
  y: number
  width: number
  height: number
  text?: string
  type?: string
  entityType?: string
}

const props = defineProps<{
  documentUrl: string
  boundingBoxes?: BoundingBox[]
  selectedBoxId?: string | null
}>()

const emit = defineEmits<{
  'box-click': [box: BoundingBox]
  'box-hover': [box: BoundingBox | null]
  'page-change': [page: number]
}>()

// PDF state
const { pdf, pages, info } = usePDF(props.documentUrl)
const currentPage = ref(1)
const scale = ref(1.0)
const isLoading = computed(() => !pdf.value)
const error = ref<string | null>(null)

// Page dimensions tracking
const pageElements = ref<HTMLElement[]>([])
const pageDimensions = ref<Map<number, { width: number; height: number; offsetTop: number; pdfWidth?: number; pdfHeight?: number }>>(new Map())

// Computed values
const totalPages = computed(() => {
  // pages.value is a number (page count), not an array
  return typeof pages.value === 'number' ? pages.value : (info.value?.numPages || 0)
})

const currentPageData = computed(() => {
  const pageNum = currentPage.value
  return pageDimensions.value.get(pageNum)
})

// Filter and transform bounding boxes for current page
const currentPageBoxes = computed(() => {
  const pageData = currentPageData.value

  // Don't render boxes until we have complete page dimensions
  if (!pageData || !pageData.pdfWidth || !pageData.pdfHeight) {
    return []
  }

  const filtered = (props.boundingBoxes || []).filter(box => box.page === currentPage.value)

  // Transform all boxes to canvas space
  const transformed = filtered.map(box => ({
    original: box,
    coords: transformBBox(box)
  }))

  // Debug logging (can be removed in production)
  if (transformed.length > 0) {
    console.log(`[PDFViewer] Rendering ${transformed.length} bounding boxes on page ${currentPage.value}`)
  }

  return transformed
})

// Update page dimensions when pages render
async function updatePageDimensions() {
  await nextTick()

  // Look for the canvas rendered by VuePDF
  const canvas = document.querySelector('canvas')
  if (!canvas) {
    console.log('[PDFViewer] Canvas not found, retrying...')
    setTimeout(updatePageDimensions, 200)
    return
  }

  const rect = canvas.getBoundingClientRect()

  // Get PDF page natural dimensions
  let pdfWidth = rect.width / scale.value
  let pdfHeight = rect.height / scale.value

  // Try to get actual PDF page dimensions from the PDF object
  if (pdf.value && pages.value && pages.value[currentPage.value - 1]) {
    try {
      const page = await pdf.value.getPage(currentPage.value)
      const viewport = page.getViewport({ scale: 1.0 })
      pdfWidth = viewport.width
      pdfHeight = viewport.height
      console.log(`[PDFViewer] PDF page ${currentPage.value} natural size:`, { width: pdfWidth, height: pdfHeight })
    } catch (e) {
      console.warn('[PDFViewer] Could not get PDF page dimensions:', e)
    }
  }

  pageDimensions.value.set(currentPage.value, {
    width: rect.width,
    height: rect.height,
    offsetTop: 0,
    pdfWidth,
    pdfHeight
  })
}

// Transform bbox from PDF coordinate space to canvas space
function transformBBox(box: BoundingBox) {
  const pageData = currentPageData.value
  if (!pageData || !pageData.pdfWidth || !pageData.pdfHeight) {
    // Fallback - don't render if we don't have dimensions
    return {
      x: 0,
      y: 0,
      width: 0,
      height: 0
    }
  }

  // Calculate the scale from PDF coordinate space to rendered canvas space
  const scaleX = pageData.width / pageData.pdfWidth
  const scaleY = pageData.height / pageData.pdfHeight

  // Docling bboxes use PDF coordinate system (bottom-left origin, Y increases upward)
  // The bbox format is {l, t, r, b} but in PDF coords where:
  // - t is actually the BOTTOM edge (larger Y value)
  // - b is actually the TOP edge (smaller Y value)
  // DocumentViewer normalizes this to {x, y, width, height} using Math.min for y
  // BUT we still need to flip from PDF (bottom-left) to SVG (top-left) coords

  const canvasX = box.x * scaleX
  // Flip Y-axis: SVG Y = pdfHeight - (PDF Y + height)
  const canvasY = (pageData.pdfHeight - (box.y + box.height)) * scaleY

  return {
    x: canvasX,
    y: canvasY,
    width: box.width * scaleX,
    height: box.height * scaleY
  }
}

// Get color for bounding box type
function getBoxColor(type?: string): string {
  const colors: Record<string, string> = {
    BM25_MATCH: '#3B82F6',        // Blue for BM25 keyword matches
    SEMANTIC_MATCH: '#FBBF24',    // Yellow for semantic matches
    TEXT_MATCH: '#FBBF24',        // Yellow for exact text matches
    PERSON: '#3B82F6',
    ORGANIZATION: '#8B5CF6',
    LOCATION: '#10B981',
    DATE: '#F59E0B',
    MONEY: '#EF4444',
    COURT: '#EC4899',
    CITATION: '#6366F1',
    entity: '#6B7280',
    highlight: '#FBBF24',
    annotation: '#8B5CF6',
    clause: '#F97316'
  }
  return colors[type || ''] || '#FBBF24'
}

// Navigation
function goToPage(page: number) {
  if (page >= 1 && page <= totalPages.value) {
    console.log(`[PDFViewer] Navigating to page ${page}`)
    currentPage.value = page
    emit('page-change', page)
  }
}

function nextPage() {
  goToPage(currentPage.value + 1)
}

function prevPage() {
  goToPage(currentPage.value - 1)
}

// Zoom controls
function zoomIn() {
  scale.value = Math.min(scale.value + 0.25, 3.0)
}

function zoomOut() {
  scale.value = Math.max(scale.value - 0.25, 0.5)
}

function resetZoom() {
  scale.value = 1.5
}

// Handle bounding box interactions
function handleBoxClick(box: BoundingBox) {
  emit('box-click', box)
}

function handleBoxHover(box: BoundingBox | null) {
  emit('box-hover', box)
}

// Watch for PDF load and update dimensions
watch(pdf, (newPdf) => {
  if (newPdf) {
    setTimeout(updatePageDimensions, 500)
  }
})

watch(() => props.documentUrl, () => {
  error.value = null
  currentPage.value = 1
})

// Update dimensions on scale or page change
watch([scale, currentPage], () => {
  setTimeout(updatePageDimensions, 100)
})

onMounted(() => {
  setTimeout(updatePageDimensions, 1000)
})

defineExpose({
  goToPage,
  nextPage,
  prevPage,
  zoomIn,
  zoomOut,
  resetZoom,
  currentPage,
  totalPages,
  scale
})
</script>

<template>
  <ClientOnly>
    <div class="relative w-full h-full flex flex-col bg-muted/20">
      <!-- Toolbar -->
      <div class="flex items-center justify-between p-3 border-b border-default bg-default">
        <!-- Page Navigation -->
        <div class="flex items-center gap-2">
          <div class="inline-flex items-center gap-1">
            <UButton
              icon="i-lucide-chevron-left"
              color="neutral"
              variant="outline"
              size="sm"
              :disabled="currentPage <= 1"
              @click="prevPage"
            />
            <UInput
              :model-value="currentPage"
              type="number"
              :min="1"
              :max="totalPages"
              class="w-16 text-center"
              size="sm"
              @update:model-value="(val: any) => goToPage(Number(val))"
            />
            <UButton
              icon="i-lucide-chevron-right"
              color="neutral"
              variant="outline"
              size="sm"
              :disabled="currentPage >= totalPages"
              @click="nextPage"
            />
          </div>
          <span class="text-sm text-muted">/ {{ totalPages }}</span>
        </div>

        <!-- Zoom Controls -->
        <div class="flex items-center gap-2">
          <div class="inline-flex items-center gap-1">
            <UButton
              icon="i-lucide-zoom-out"
              color="neutral"
              variant="outline"
              size="sm"
              @click="zoomOut"
            />
            <UButton
              :label="`${Math.round(scale * 100)}%`"
              color="neutral"
              variant="outline"
              size="sm"
              @click="resetZoom"
            />
            <UButton
              icon="i-lucide-zoom-in"
              color="neutral"
              variant="outline"
              size="sm"
              @click="zoomIn"
            />
          </div>
        </div>

        <!-- Additional Tools -->
        <div class="flex items-center gap-2">
          <UTooltip text="Download">
            <UButton
              icon="i-lucide-download"
              color="neutral"
              variant="ghost"
              size="sm"
            />
          </UTooltip>
          <UTooltip text="Print">
            <UButton
              icon="i-lucide-printer"
              color="neutral"
              variant="ghost"
              size="sm"
            />
          </UTooltip>
        </div>
      </div>

      <!-- PDF Canvas Container -->
      <div class="flex-1 overflow-auto pdf-container">
        <div v-if="isLoading" class="flex flex-col items-center justify-center py-20">
          <UIcon name="i-lucide-loader" class="size-12 text-primary animate-spin mb-4" />
          <p class="text-muted">Loading document...</p>
        </div>

        <div v-else-if="error" class="flex flex-col items-center justify-center py-20">
          <UIcon name="i-lucide-file-x" class="size-12 text-error mb-4" />
          <p class="text-error font-medium mb-2">{{ error }}</p>
        </div>

        <div v-else class="relative flex items-start justify-center p-6">
          <!-- PDF Renderer -->
          <div class="relative shadow-2xl">
            <div class="relative">
              <VuePDF
                :pdf="pdf"
                :page="currentPage"
                :scale="scale"
                @loaded="updatePageDimensions"
              />

              <!-- Bounding Box Overlay -->
              <svg
                v-if="currentPageData && currentPageBoxes.length > 0"
                class="bbox-overlay"
                :width="currentPageData.width"
                :height="currentPageData.height"
              >
              <g
                v-for="box in currentPageBoxes"
                :key="box.original.id || `${box.original.x}-${box.original.y}`"
                class="pointer-events-auto cursor-pointer"
                @click="handleBoxClick(box.original)"
                @mouseenter="handleBoxHover(box.original)"
                @mouseleave="handleBoxHover(null)"
              >
                <!-- Background Rectangle -->
                <rect
                  :x="box.coords.x"
                  :y="box.coords.y"
                  :width="box.coords.width"
                  :height="box.coords.height"
                  :fill="getBoxColor(box.original.entityType || box.original.type)"
                  fill-opacity="0.15"
                />
                <!-- Border Rectangle -->
                <rect
                  :x="box.coords.x"
                  :y="box.coords.y"
                  :width="box.coords.width"
                  :height="box.coords.height"
                  :stroke="getBoxColor(box.original.entityType || box.original.type)"
                  :stroke-width="box.original.id === selectedBoxId ? 3 : 2"
                  :stroke-dasharray="box.original.id === selectedBoxId ? '0' : '5,5'"
                  fill="none"
                />
                <!-- Label for selected box -->
                <text
                  v-if="box.original.id === selectedBoxId && box.original.entityType"
                  :x="box.coords.x"
                  :y="box.coords.y - 5"
                  :fill="getBoxColor(box.original.entityType)"
                  font-size="12"
                  font-weight="bold"
                >
                  {{ box.original.entityType }}
                </text>
              </g>
            </svg>
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #fallback>
      <div class="flex items-center justify-center h-full">
        <UIcon name="i-lucide-loader" class="size-12 text-primary animate-spin" />
      </div>
    </template>
  </ClientOnly>
</template>

<style scoped>
.pdf-container {
  background: linear-gradient(to bottom, transparent, rgba(0,0,0,0.03));
}

/* Bounding box overlay positioning */
.bbox-overlay {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  z-index: 10;
}

/* Override vue-pdf styles if needed */
:deep(.vue-pdf-main) {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

:deep(.vue-pdf-page) {
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  background: white;
}
</style>
