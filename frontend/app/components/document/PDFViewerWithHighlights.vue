<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import type { BoundingBox } from '~/composables/usePDFHighlights'

// PDF.js worker setup
if (process.client) {
  pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`
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
  'text-select': [selection: { text: string; page: number; rect: DOMRect }]
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const overlayRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)

const pdf = ref<any>(null)
const currentPage = ref(1)
const totalPages = ref(0)
const scale = ref(1.5)
const isLoading = ref(true)
const error = ref<string | null>(null)

const pageWidth = ref(0)
const pageHeight = ref(0)

// Load PDF document
async function loadPDF() {
  if (!props.documentUrl) return

  try {
    isLoading.value = true
    error.value = null

    const loadingTask = pdfjsLib.getDocument(props.documentUrl)
    pdf.value = await loadingTask.promise
    totalPages.value = pdf.value.numPages

    await renderPage(currentPage.value)
  } catch (err) {
    console.error('Error loading PDF:', err)
    error.value = 'Failed to load PDF document'
  } finally {
    isLoading.value = false
  }
}

// Render specific page
async function renderPage(pageNum: number) {
  if (!pdf.value || !canvasRef.value) return

  try {
    const page = await pdf.value.getPage(pageNum)
    const viewport = page.getViewport({ scale: scale.value })

    const canvas = canvasRef.value
    const context = canvas.getContext('2d')
    if (!context) return

    canvas.height = viewport.height
    canvas.width = viewport.width
    pageWidth.value = viewport.width
    pageHeight.value = viewport.height

    const renderContext = {
      canvasContext: context,
      viewport: viewport
    }

    await page.render(renderContext).promise

    // Render overlay after page is rendered
    await nextTick()
    renderOverlay()

    emit('page-change', pageNum)
  } catch (err) {
    console.error('Error rendering page:', err)
  }
}

// Render bounding box overlay
function renderOverlay() {
  if (!overlayRef.value) return

  const canvas = overlayRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // Match overlay canvas size to PDF canvas
  canvas.width = pageWidth.value
  canvas.height = pageHeight.value

  // Clear previous drawings
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // Filter boxes for current page
  const currentBoxes = props.boundingBoxes?.filter(box => box.page === currentPage.value) || []

  // Draw each bounding box
  currentBoxes.forEach(box => {
    const isSelected = box.id === props.selectedBoxId
    const color = getBoxColor(box.entityType || box.type)

    // Draw rectangle
    ctx.strokeStyle = color
    ctx.lineWidth = isSelected ? 3 : 2
    ctx.setLineDash(isSelected ? [] : [5, 5])
    ctx.strokeRect(box.x, box.y, box.width, box.height)

    // Fill with semi-transparent color
    ctx.fillStyle = color + '20' // 20 = 12% opacity in hex
    ctx.fillRect(box.x, box.y, box.width, box.height)

    // Draw label if selected
    if (isSelected && box.entityType) {
      ctx.fillStyle = color
      ctx.font = '12px sans-serif'
      ctx.fillText(box.entityType, box.x, box.y - 5)
    }
  })
}

// Get color for box type
function getBoxColor(type: string): string {
  const colors: Record<string, string> = {
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
  return colors[type] || '#6B7280'
}

// Handle canvas click to detect box clicks
function handleCanvasClick(event: MouseEvent) {
  if (!overlayRef.value) return

  const rect = overlayRef.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  // Find clicked box (check in reverse order for top-most)
  const currentBoxes = props.boundingBoxes?.filter(box => box.page === currentPage.value) || []

  for (let i = currentBoxes.length - 1; i >= 0; i--) {
    const box = currentBoxes[i]
    if (x >= box.x && x <= box.x + box.width &&
        y >= box.y && y <= box.y + box.height) {
      emit('box-click', box)
      return
    }
  }
}

// Handle mouse move for hover effects
function handleCanvasHover(event: MouseEvent) {
  if (!overlayRef.value) return

  const rect = overlayRef.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  const currentBoxes = props.boundingBoxes?.filter(box => box.page === currentPage.value) || []

  for (let i = currentBoxes.length - 1; i >= 0; i--) {
    const box = currentBoxes[i]
    if (x >= box.x && x <= box.x + box.width &&
        y >= box.y && y <= box.y + box.height) {
      overlayRef.value.style.cursor = 'pointer'
      emit('box-hover', box)
      return
    }
  }

  overlayRef.value.style.cursor = 'default'
  emit('box-hover', null)
}

// Navigation
function goToPage(page: number) {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    renderPage(page)
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
  renderPage(currentPage.value)
}

function zoomOut() {
  scale.value = Math.max(scale.value - 0.25, 0.5)
  renderPage(currentPage.value)
}

function resetZoom() {
  scale.value = 1.5
  renderPage(currentPage.value)
}

// Watch for prop changes
watch(() => props.documentUrl, loadPDF)
watch(() => props.boundingBoxes, renderOverlay, { deep: true })
watch(() => props.selectedBoxId, renderOverlay)

onMounted(() => {
  loadPDF()
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
  <div ref="containerRef" class="relative w-full h-full flex flex-col bg-muted/20">
    <!-- Toolbar -->
    <div class="flex items-center justify-between p-3 border-b border-default bg-default">
      <!-- Page Navigation -->
      <div class="flex items-center gap-2">
        <UButtonGroup>
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
        </UButtonGroup>
        <span class="text-sm text-muted">/ {{ totalPages }}</span>
      </div>

      <!-- Zoom Controls -->
      <div class="flex items-center gap-2">
        <UButtonGroup>
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
        </UButtonGroup>
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
    <div class="flex-1 overflow-auto p-6 flex items-start justify-center">
      <div v-if="isLoading" class="flex flex-col items-center justify-center py-20">
        <UIcon name="i-lucide-loader" class="size-12 text-primary animate-spin mb-4" />
        <p class="text-muted">Loading document...</p>
      </div>

      <div v-else-if="error" class="flex flex-col items-center justify-center py-20">
        <UIcon name="i-lucide-file-x" class="size-12 text-error mb-4" />
        <p class="text-error font-medium mb-2">{{ error }}</p>
        <UButton
          label="Retry"
          color="neutral"
          variant="outline"
          @click="loadPDF"
        />
      </div>

      <div v-else class="relative shadow-2xl">
        <!-- PDF Canvas -->
        <canvas
          ref="canvasRef"
          class="block"
        />

        <!-- Overlay Canvas for Bounding Boxes -->
        <canvas
          ref="overlayRef"
          class="absolute top-0 left-0 pointer-events-auto"
          @click="handleCanvasClick"
          @mousemove="handleCanvasHover"
        />
      </div>
    </div>
  </div>
</template>
