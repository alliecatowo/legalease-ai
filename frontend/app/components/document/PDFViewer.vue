<template>
  <div class="relative">
    <!-- Toolbar -->
    <div class="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
      <div class="flex items-center space-x-4">
        <UButton
          variant="outline"
          size="sm"
          @click="previousPage"
          :disabled="currentPage <= 1"
        >
          <UIcon name="i-heroicons-chevron-left-20-solid" class="w-4 h-4" />
        </UButton>

        <span class="text-sm text-gray-700">
          Page {{ currentPage }} of {{ totalPages }}
        </span>

        <UButton
          variant="outline"
          size="sm"
          @click="nextPage"
          :disabled="currentPage >= totalPages"
        >
          <UIcon name="i-heroicons-chevron-right-20-solid" class="w-4 h-4" />
        </UButton>
      </div>

      <div class="flex items-center space-x-4">
        <USelectMenu
          v-model="zoom"
          :options="zoomOptions"
          size="sm"
          class="w-24"
          @update:model-value="setZoom"
        />

        <UButton
          variant="outline"
          size="sm"
          @click="fitToWidth"
        >
          <UIcon name="i-heroicons-arrows-right-left-20-solid" class="w-4 h-4" />
        </UButton>

        <UButton
          variant="outline"
          size="sm"
          @click="fitToPage"
        >
          <UIcon name="i-heroicons-arrows-up-down-20-solid" class="w-4 h-4" />
        </UButton>
      </div>
    </div>

    <!-- PDF Container -->
    <div
      ref="containerRef"
      class="relative overflow-auto bg-gray-100"
      :style="{ height: containerHeight }"
    >
      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center h-full">
        <div class="text-center">
          <UIcon name="i-heroicons-arrow-path-20-solid" class="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
          <p class="text-gray-600">Loading PDF...</p>
        </div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="flex items-center justify-center h-full">
        <div class="text-center">
          <UIcon name="i-heroicons-exclamation-triangle-20-solid" class="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h3 class="text-lg font-medium text-gray-900 mb-2">Failed to load PDF</h3>
          <p class="text-gray-500">{{ error }}</p>
        </div>
      </div>

      <!-- PDF Canvas -->
      <div
        v-else
        ref="canvasRef"
        class="relative mx-auto"
        :style="{ width: canvasWidth, height: canvasHeight }"
      >
        <canvas
          ref="pdfCanvas"
          class="shadow-lg"
          :width="canvasWidth"
          :height="canvasHeight"
        />

        <!-- Highlight Layer -->
        <svg
          v-if="highlights.length > 0"
          class="absolute inset-0 pointer-events-none"
          :width="canvasWidth"
          :height="canvasHeight"
        >
          <rect
            v-for="highlight in highlights"
            :key="`${highlight.page}-${highlight.x}-${highlight.y}`"
            :x="highlight.x"
            :y="highlight.y"
            :width="highlight.width"
            :height="highlight.height"
            fill="rgba(255, 255, 0, 0.3)"
            stroke="rgba(255, 215, 0, 0.8)"
            stroke-width="1"
            class="cursor-pointer hover:fill-yellow-400"
            @click="onHighlightClick(highlight)"
          />
        </svg>

        <!-- Entity Highlight Layer -->
        <svg
          v-if="entityHighlights.length > 0"
          class="absolute inset-0 pointer-events-none"
          :width="canvasWidth"
          :height="canvasHeight"
        >
          <rect
            v-for="entity in entityHighlights"
            :key="`entity-${entity.id}`"
            :x="entity.x"
            :y="entity.y"
            :width="entity.width"
            :height="entity.height"
            :fill="getEntityColor(entity.type)"
            fill-opacity="0.2"
            stroke="currentColor"
            stroke-width="1"
            class="cursor-pointer hover:opacity-50"
            @click="onEntityClick(entity)"
          />
        </svg>

        <!-- Text Selection Overlay -->
        <div
          v-if="textSelection"
          class="absolute pointer-events-none bg-blue-200 opacity-50"
          :style="{
            left: textSelection.x + 'px',
            top: textSelection.y + 'px',
            width: textSelection.width + 'px',
            height: textSelection.height + 'px'
          }"
        />
      </div>
    </div>

    <!-- Thumbnail Sidebar -->
    <div v-if="showThumbnails" class="absolute left-0 top-0 h-full w-48 bg-white border-r border-gray-200 overflow-y-auto">
      <div class="p-4">
        <h4 class="text-sm font-medium text-gray-900 mb-3">Pages</h4>
        <div class="space-y-2">
          <div
            v-for="pageNum in totalPages"
            :key="pageNum"
            class="relative cursor-pointer rounded border-2 overflow-hidden"
            :class="pageNum === currentPage ? 'border-blue-500' : 'border-gray-200'"
            @click="goToPage(pageNum)"
          >
            <canvas
              :ref="(el) => setThumbnailRef(el, pageNum)"
              class="w-full h-auto"
              :width="thumbnailWidth"
              :height="thumbnailHeight"
            />
            <div class="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-xs text-center py-1">
              {{ pageNum }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'

interface Props {
  url: string
  highlights?: Array<{
    page: number
    x: number
    y: number
    width: number
    height: number
    text?: string
  }>
  entities?: Array<{
    id: string
    text: string
    type: string
    positions: Array<{
      page: number
      x: number
      y: number
      width: number
      height: number
    }>
  }>
}

interface Emits {
  (e: 'highlight-click', highlight: any): void
  (e: 'entity-click', entity: any): void
  (e: 'text-select', text: string): void
  (e: 'page-change', page: number): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Refs
const containerRef = ref<HTMLElement>()
const canvasRef = ref<HTMLElement>()
const pdfCanvas = ref<HTMLCanvasElement>()

// Reactive state
const loading = ref(true)
const error = ref('')
const pdfDocument = ref<any>(null)
const currentPage = ref(1)
const totalPages = ref(0)
const zoom = ref(1.0)
const showThumbnails = ref(false)

// Canvas dimensions
const canvasWidth = ref(800)
const canvasHeight = ref(1100)
const containerHeight = ref('600px')

// Options
const zoomOptions = [
  { label: '50%', value: 0.5 },
  { label: '75%', value: 0.75 },
  { label: '100%', value: 1.0 },
  { label: '125%', value: 1.25 },
  { label: '150%', value: 1.5 },
  { label: '200%', value: 2.0 }
]

// Thumbnail refs
const thumbnailRefs = ref<Map<number, HTMLCanvasElement>>(new Map())
const thumbnailWidth = 150
const thumbnailHeight = 200

// Computed
const highlights = computed(() => {
  return props.highlights?.filter(h => h.page === currentPage.value) || []
})

const entityHighlights = computed(() => {
  if (!props.entities) return []

  const highlights: any[] = []
  props.entities.forEach(entity => {
    entity.positions
      .filter(pos => pos.page === currentPage.value)
      .forEach(pos => {
        highlights.push({
          id: entity.id,
          text: entity.text,
          type: entity.type,
          ...pos
        })
      })
  })

  return highlights
})

const textSelection = ref<{
  x: number
  y: number
  width: number
  height: number
} | null>(null)

// Methods
async function loadPDF() {
  if (!props.url) return

  loading.value = true
  error.value = ''

  try {
    // Import PDF.js dynamically
    const pdfjsLib = await import('pdfjs-dist')

    // Set worker path
    pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js'

    // Load PDF
    const loadingTask = pdfjsLib.getDocument(props.url)
    pdfDocument.value = await loadingTask.promise

    totalPages.value = pdfDocument.value.numPages

    await renderPage(currentPage.value)
    await renderThumbnails()

  } catch (err: any) {
    error.value = err.message || 'Failed to load PDF'
    console.error('PDF loading error:', err)
  } finally {
    loading.value = false
  }
}

async function renderPage(pageNum: number) {
  if (!pdfDocument.value) return

  try {
    const page = await pdfDocument.value.getPage(pageNum)
    const viewport = page.getViewport({ scale: zoom.value })

    canvasWidth.value = viewport.width
    canvasHeight.value = viewport.height

    if (pdfCanvas.value) {
      const context = pdfCanvas.value.getContext('2d')!
      pdfCanvas.value.width = viewport.width
      pdfCanvas.value.height = viewport.height

      const renderContext = {
        canvasContext: context,
        viewport: viewport
      }

      await page.render(renderContext).promise
    }

  } catch (err) {
    console.error('Page rendering error:', err)
  }
}

async function renderThumbnails() {
  if (!pdfDocument.value) return

  for (let pageNum = 1; pageNum <= totalPages.value; pageNum++) {
    try {
      const page = await pdfDocument.value.getPage(pageNum)
      const viewport = page.getViewport({ scale: thumbnailWidth / page.getViewport({ scale: 1 }).width })

      const canvas = thumbnailRefs.value.get(pageNum)
      if (canvas) {
        const context = canvas.getContext('2d')!
        canvas.width = viewport.width
        canvas.height = viewport.height

        const renderContext = {
          canvasContext: context,
          viewport: viewport
        }

        await page.render(renderContext).promise
      }
    } catch (err) {
      console.error(`Thumbnail rendering error for page ${pageNum}:`, err)
    }
  }
}

function setThumbnailRef(el: HTMLCanvasElement | null, pageNum: number) {
  if (el) {
    thumbnailRefs.value.set(pageNum, el)
  }
}

function previousPage() {
  if (currentPage.value > 1) {
    goToPage(currentPage.value - 1)
  }
}

function nextPage() {
  if (currentPage.value < totalPages.value) {
    goToPage(currentPage.value + 1)
  }
}

function goToPage(pageNum: number) {
  currentPage.value = pageNum
  renderPage(pageNum)
  emit('page-change', pageNum)
}

function setZoom(newZoom: number) {
  zoom.value = newZoom
  renderPage(currentPage.value)
}

function fitToWidth() {
  if (!containerRef.value) return

  const containerWidth = containerRef.value.clientWidth - 32 // padding
  const scale = containerWidth / canvasWidth.value
  zoom.value = Math.max(0.5, Math.min(2.0, scale))
  renderPage(currentPage.value)
}

function fitToPage() {
  if (!containerRef.value) return

  const containerHeight = containerRef.value.clientHeight - 100 // toolbar
  const scale = containerHeight / canvasHeight.value
  zoom.value = Math.max(0.5, Math.min(2.0, scale))
  renderPage(currentPage.value)
}

function onHighlightClick(highlight: any) {
  emit('highlight-click', highlight)
}

function onEntityClick(entity: any) {
  emit('entity-click', entity)
}

function getEntityColor(type: string): string {
  const colors: Record<string, string> = {
    PERSON: 'rgba(59, 130, 246, 0.3)', // blue
    ORGANIZATION: 'rgba(147, 51, 234, 0.3)', // purple
    COURT: 'rgba(34, 197, 94, 0.3)', // green
    DATE: 'rgba(251, 146, 60, 0.3)', // orange
    AMOUNT: 'rgba(239, 68, 68, 0.3)', // red
    CITATION: 'rgba(99, 102, 241, 0.3)' // indigo
  }
  return colors[type] || 'rgba(156, 163, 175, 0.3)' // gray
}

// Text selection handling
function handleMouseDown(event: MouseEvent) {
  if (!pdfCanvas.value) return

  const rect = pdfCanvas.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  textSelection.value = { x, y, width: 0, height: 0 }
}

function handleMouseMove(event: MouseEvent) {
  if (!textSelection.value || !pdfCanvas.value) return

  const rect = pdfCanvas.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  textSelection.value.width = x - textSelection.value.x
  textSelection.value.height = y - textSelection.value.y
}

function handleMouseUp(event: MouseEvent) {
  if (!textSelection.value) return

  // If selection is very small, clear it
  if (Math.abs(textSelection.value.width) < 10 || Math.abs(textSelection.value.height) < 10) {
    textSelection.value = null
    return
  }

  // Extract text from selection area
  extractTextFromSelection()
  textSelection.value = null
}

async function extractTextFromSelection() {
  if (!pdfDocument.value || !textSelection.value) return

  try {
    const page = await pdfDocument.value.getPage(currentPage.value)
    const textContent = await page.getTextContent()

    // This is a simplified text extraction
    // In a real implementation, you'd need to map coordinates to text items
    const selectedText = textContent.items
      .filter((item: any) => {
        // Basic bounding box check (simplified)
        return true // You'd implement proper coordinate checking
      })
      .map((item: any) => item.str)
      .join(' ')

    if (selectedText.trim()) {
      emit('text-select', selectedText.trim())
    }

  } catch (err) {
    console.error('Text extraction error:', err)
  }
}

// Event listeners
onMounted(async () => {
  await loadPDF()

  // Add text selection event listeners
  if (pdfCanvas.value) {
    pdfCanvas.value.addEventListener('mousedown', handleMouseDown)
    pdfCanvas.value.addEventListener('mousemove', handleMouseMove)
    pdfCanvas.value.addEventListener('mouseup', handleMouseUp)
  }
})

onUnmounted(() => {
  if (pdfCanvas.value) {
    pdfCanvas.value.removeEventListener('mousedown', handleMouseDown)
    pdfCanvas.value.removeEventListener('mousemove', handleMouseMove)
    pdfCanvas.value.removeEventListener('mouseup', handleMouseUp)
  }
})

// Watch for URL changes
watch(() => props.url, async (newUrl) => {
  if (newUrl) {
    await loadPDF()
  }
})

// Watch for zoom changes
watch(() => zoom.value, () => {
  renderPage(currentPage.value)
})
</script>

<style scoped>
canvas {
  max-width: 100%;
  height: auto;
}
</style>