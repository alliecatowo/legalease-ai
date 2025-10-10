<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <UPageHeader
      :title="document.filename"
      :description="getDocumentDescription()"
    >
      <template #links>
        <UButton
          variant="ghost"
          to="/search"
        >
          <UIcon name="i-heroicons-arrow-left-20-solid" class="w-5 h-5 mr-2" />
          Back to Search
        </UButton>
      </template>

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
    </UPageHeader>

    <UPageSection>
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Main Content -->
        <div class="lg:col-span-2">
          <!-- PDF Viewer -->
          <UCard class="overflow-hidden">
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
          </UCard>

          <!-- Summary Panel -->
          <UCard v-if="document.summary" class="mt-6">
            <template #header>
              <div class="flex items-center justify-between">
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
            </template>
            <p class="text-gray-700 leading-relaxed">{{ document.summary }}</p>
          </UCard>
        </div>

        <!-- Sidebar -->
        <div class="space-y-6">
          <!-- Document Info -->
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold text-gray-900">Document Info</h3>
            </template>

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
          </UCard>

          <!-- Tags -->
          <UCard v-if="document.tags && document.tags.length > 0">
            <template #header>
              <h3 class="text-lg font-semibold text-gray-900">Tags</h3>
            </template>
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
          </UCard>

          <!-- Entities -->
          <UCard v-if="document.entities && document.entities.length > 0">
            <template #header>
              <h3 class="text-lg font-semibold text-gray-900">Key Entities</h3>
            </template>
            <div class="space-y-3">
              <div
                v-for="entity in document.entities.slice(0, 10)"
                :key="entity.text"
                class="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                @click="highlightEntity(entity)"
              >
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 mb-1">
                    <span class="text-sm font-medium text-gray-900 truncate">{{ entity.text }}</span>
                    <UChip
                      :text="`${Math.round(entity.confidence * 100)}%`"
                      size="xs"
                      color="info"
                    />
                  </div>
                  <UBadge
                    :color="getEntityColor(entity.type)"
                    variant="soft"
                    size="sm"
                  >
                    {{ entity.type }}
                  </UBadge>
                </div>
              </div>
            </div>
            <template #footer v-if="document.entities.length > 10">
              <UButton variant="ghost" size="sm" color="gray">
                Show {{ document.entities.length - 10 }} more
              </UButton>
            </template>
          </UCard>

          <!-- Related Documents -->
          <UCard v-if="relatedDocuments.length > 0">
            <template #header>
              <h3 class="text-lg font-semibold text-gray-900">Related Documents</h3>
            </template>
            <div class="space-y-3">
              <div
                v-for="doc in relatedDocuments.slice(0, 5)"
                :key="doc.id"
                class="p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors"
                @click="openDocument(doc.id)"
              >
                <div class="flex items-start justify-between">
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-900 truncate">{{ doc.filename }}</p>
                    <p class="text-xs text-gray-500 mt-1">{{ formatDate(doc.created_at) }}</p>
                  </div>
                  <UIcon name="i-heroicons-chevron-right-20-solid" class="w-4 h-4 text-gray-400 ml-2 flex-shrink-0" />
                </div>
              </div>
            </div>
          </UCard>
        </div>
      </div>
    </UPageSection>
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

function getDocumentDescription(): string {
  const parts = []
  if (document.value.case_name) parts.push(document.value.case_name)
  if (document.value.created_at) parts.push(formatDate(document.value.created_at))
  return parts.join(' • ')
}

// Methods
async function loadDocument() {
  try {
    const response = await apiFetch(`/documents/${documentId}`) as any
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
    const response = await apiFetch(`/documents/${documentId}/related`) as any
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
    }) as any
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
    }) as any
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
      method: 'GET'
    }) as any

    const url = window.URL.createObjectURL(new Blob([response]))
    const link = window.document.createElement('a')
    link.href = url
    link.setAttribute('download', document.value.filename)
    window.document.body.appendChild(link)
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