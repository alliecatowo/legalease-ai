<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <div class="bg-white border-b border-gray-200">
      <div class="container mx-auto px-4 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-4">
            <UButton
              variant="ghost"
              @click="navigateTo('/search')"
            >
              <UIcon name="i-heroicons-arrow-left-20-solid" class="w-5 h-5 mr-2" />
              Back to Search
            </UButton>

            <div class="h-6 w-px bg-gray-300" />

            <div>
              <h1 class="text-xl font-semibold text-gray-900">
                {{ document.filename }}
              </h1>
              <p class="text-sm text-gray-500">
                {{ document.case_name }} • {{ formatDate(document.created_at) }}
              </p>
            </div>
          </div>

          <div class="flex items-center space-x-3">
            <UButton
              variant="outline"
              @click="summarizeDocument"
              :loading="summarizing"
            >
              <UIcon name="i-heroicons-document-text-20-solid" class="w-4 h-4 mr-2" />
              {{ document.summary ? 'View Summary' : 'Summarize' }}
            </UButton>

            <UButton
              variant="outline"
              @click="showTranscript"
              :disabled="!hasTranscript"
            >
              <UIcon name="i-heroicons-chat-bubble-left-right-20-solid" class="w-4 h-4 mr-2" />
              Transcript
            </UButton>

            <UButton
              variant="outline"
              @click="downloadDocument"
            >
              <UIcon name="i-heroicons-arrow-down-tray-20-solid" class="w-4 h-4 mr-2" />
              Download
            </UButton>

            <UDropdownMenu :items="actionMenu">
              <UButton variant="outline">
                <UIcon name="i-heroicons-ellipsis-vertical-20-solid" class="w-5 h-5" />
              </UButton>
            </UDropdownMenu>
          </div>
        </div>
      </div>
    </div>

    <div class="container mx-auto px-4 py-6">
      <div class="grid grid-cols-12 gap-6">
        <!-- Main Content -->
        <div class="col-span-8">
          <!-- PDF Viewer -->
          <div class="bg-white rounded-lg border border-gray-200">
            <PDFViewer
              v-if="document.file_url"
              :url="document.file_url"
              :highlights="searchHighlights"
              :entities="document.entities"
              @highlight-click="onHighlightClick"
              @text-select="onTextSelect"
            />
            <div v-else class="flex items-center justify-center h-96">
              <div class="text-center">
                <UIcon name="i-heroicons-document-20-solid" class="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p class="text-gray-500">Document not available</p>
              </div>
            </div>
          </div>

          <!-- Summary Panel -->
          <div v-if="document.summary" class="mt-6 bg-white rounded-lg border border-gray-200 p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold text-gray-900">Document Summary</h3>
              <UButton
                variant="ghost"
                size="sm"
                @click="regenerateSummary"
                :loading="summarizing"
              >
                <UIcon name="i-heroicons-arrow-path-20-solid" class="w-4 h-4 mr-1" />
                Regenerate
              </UButton>
            </div>
            <p class="text-gray-700 leading-relaxed">{{ document.summary }}</p>
          </div>
        </div>

        <!-- Sidebar -->
        <div class="col-span-4 space-y-6">
          <!-- Document Info -->
          <div class="bg-white rounded-lg border border-gray-200 p-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">Document Info</h3>

            <div class="space-y-3">
              <div>
                <label class="text-sm font-medium text-gray-500">File Size</label>
                <p class="text-sm text-gray-900">{{ formatFileSize(document.size) }}</p>
              </div>

              <div>
                <label class="text-sm font-medium text-gray-500">Type</label>
                <p class="text-sm text-gray-900">{{ document.doc_type || 'Document' }}</p>
              </div>

              <div>
                <label class="text-sm font-medium text-gray-500">Uploaded</label>
                <p class="text-sm text-gray-900">{{ formatDate(document.created_at) }}</p>
              </div>

              <div>
                <label class="text-sm font-medium text-gray-500">Processed</label>
                <p class="text-sm text-gray-900">
                  {{ document.processed_at ? formatDate(document.processed_at) : 'Not processed' }}
                </p>
              </div>
            </div>
          </div>

          <!-- Tags -->
          <div v-if="document.tags && document.tags.length > 0" class="bg-white rounded-lg border border-gray-200 p-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">Tags</h3>
            <div class="flex flex-wrap gap-2">
              <UBadge
                v-for="tag in document.tags"
                :key="tag"
                variant="outline"
                @click="searchByTag(tag)"
              >
                {{ tag }}
              </UBadge>
            </div>
          </div>

          <!-- Entities -->
          <div v-if="document.entities && document.entities.length > 0" class="bg-white rounded-lg border border-gray-200 p-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">Key Entities</h3>
            <div class="space-y-2">
              <div
                v-for="entity in document.entities.slice(0, 10)"
                :key="entity.text"
                class="flex items-center justify-between p-2 rounded hover:bg-gray-50 cursor-pointer"
                @click="highlightEntity(entity)"
              >
                <div>
                  <span class="text-sm font-medium text-gray-900">{{ entity.text }}</span>
                  <UBadge
                    :color="getEntityColor(entity.type)"
                    variant="subtle"
                    size="sm"
                    class="ml-2"
                  >
                    {{ entity.type }}
                  </UBadge>
                </div>
                <span class="text-xs text-gray-500">{{ Math.round(entity.confidence * 100) }}%</span>
              </div>
            </div>
            <div v-if="document.entities.length > 10" class="mt-4">
              <UButton variant="link" size="sm">
                Show {{ document.entities.length - 10 }} more
              </UButton>
            </div>
          </div>

          <!-- Related Documents -->
          <div v-if="relatedDocuments.length > 0" class="bg-white rounded-lg border border-gray-200 p-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">Related Documents</h3>
            <div class="space-y-3">
              <div
                v-for="doc in relatedDocuments.slice(0, 5)"
                :key="doc.id"
                class="p-3 rounded border border-gray-200 hover:bg-gray-50 cursor-pointer"
                @click="openDocument(doc.id)"
              >
                <p class="text-sm font-medium text-gray-900">{{ doc.filename }}</p>
                <p class="text-xs text-gray-500">{{ formatDate(doc.created_at) }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const route = useRoute()
const documentId = route.params.id as string

const { apiFetch } = useApi()

// Reactive state
const document = ref({
  id: '',
  filename: '',
  case_name: '',
  created_at: '',
  processed_at: '',
  size: 0,
  doc_type: '',
  file_url: '',
  summary: '',
  tags: [] as string[],
  entities: [] as Array<{ text: string; type: string; confidence: number }>
})

const relatedDocuments = ref([])
const searchHighlights = ref([])
const summarizing = ref(false)
const hasTranscript = ref(false)

// Computed
const actionMenu = computed(() => [
  {
    label: 'Edit Metadata',
    icon: 'i-heroicons-pencil-square-20-solid',
    click: editMetadata
  },
  {
    label: 'Reprocess Document',
    icon: 'i-heroicons-arrow-path-20-solid',
    click: reprocessDocument
  },
  {
    label: 'Delete Document',
    icon: 'i-heroicons-trash-20-solid',
    click: deleteDocument
  }
])

// Methods
async function loadDocument() {
  try {
    const response = await apiFetch(`/documents/${documentId}`)
    document.value = response.document

    // Check for transcript
    try {
      await apiFetch(`/transcriptions/${documentId}`)
      hasTranscript.value = true
    } catch {
      hasTranscript.value = false
    }

    // Load related documents
    await loadRelatedDocuments()

  } catch (error) {
    console.error('Failed to load document:', error)
    throw createError({
      statusCode: 404,
      statusMessage: 'Document not found'
    })
  }
}

async function loadRelatedDocuments() {
  try {
    const response = await apiFetch(`/documents/${documentId}/related`)
    relatedDocuments.value = response.documents || []
  } catch (error) {
    console.error('Failed to load related documents:', error)
  }
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function getEntityColor(type: string): string {
  const colors: Record<string, string> = {
    PERSON: 'blue',
    ORGANIZATION: 'purple',
    COURT: 'green',
    DATE: 'orange',
    AMOUNT: 'red',
    CITATION: 'indigo'
  }
  return colors[type] || 'gray'
}

async function summarizeDocument() {
  if (document.value.summary) {
    // Show existing summary (handled in template)
    return
  }

  summarizing.value = true
  try {
    const response = await apiFetch(`/documents/${documentId}/summarize`, {
      method: 'POST'
    })
    document.value.summary = response.summary
  } catch (error) {
    console.error('Failed to summarize document:', error)
  } finally {
    summarizing.value = false
  }
}

async function regenerateSummary() {
  summarizing.value = true
  try {
    const response = await apiFetch(`/documents/${documentId}/summarize`, {
      method: 'POST',
      body: { regenerate: true }
    })
    document.value.summary = response.summary
  } catch (error) {
    console.error('Failed to regenerate summary:', error)
  } finally {
    summarizing.value = false
  }
}

function showTranscript() {
  navigateTo(`/transcripts/${documentId}`)
}

async function downloadDocument() {
  try {
    const response = await apiFetch(`/documents/${documentId}/download`, {
      method: 'GET',
      responseType: 'blob'
    })

    const url = window.URL.createObjectURL(new Blob([response]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', document.value.filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (error) {
    console.error('Failed to download document:', error)
  }
}

function searchByTag(tag: string) {
  navigateTo(`/search?q=tag:${tag}`)
}

function highlightEntity(entity: any) {
  // TODO: Scroll to entity in PDF
  console.log('Highlight entity:', entity)
}

function onHighlightClick(highlight: any) {
  console.log('Highlight clicked:', highlight)
}

function onTextSelect(text: string) {
  console.log('Text selected:', text)
}

function openDocument(docId: string) {
  navigateTo(`/documents/${docId}`)
}

function editMetadata() {
  // TODO: Implement metadata editing
  console.log('Edit metadata')
}

function reprocessDocument() {
  // TODO: Implement document reprocessing
  console.log('Reprocess document')
}

function deleteDocument() {
  // TODO: Implement document deletion with confirmation
  console.log('Delete document')
}

// Lifecycle
onMounted(async () => {
  await loadDocument()
})
</script>