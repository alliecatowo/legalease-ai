<script setup lang="ts">
definePageMeta({ layout: 'default' })

const route = useRoute()
const router = useRouter()
const toast = useToast()

const documentId = computed(() => route.params.id as string)
const { getDocument, deleteDocument, getDocumentPages, getDocumentChunks, getRelatedDocuments } = useDocuments()
const { getCase } = useCases()

// Fetch document
const loading = ref(true)
const error = ref<string | null>(null)
const document = ref<any>(null)
const caseData = ref<any>(null)
const showDeleteModal = ref(false)
const isDeleting = ref(false)

// Tabs
const activeTab = ref('content')
const tabs = [
  { label: 'Content', value: 'content', icon: 'i-lucide-file-text' },
  { label: 'Metadata', value: 'metadata', icon: 'i-lucide-info' },
  { label: 'Related', value: 'related', icon: 'i-lucide-files' }
]

// Pages and chunks data (for PDF viewer)
const pages = ref<any[]>([])
const chunks = ref<any[]>([])
const relatedDocs = ref<any[]>([])
const loadingPages = ref(false)

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    document.value = await getDocument(documentId.value)
    if (!document.value) {
      error.value = 'Document not found'
      return
    }
    if (document.value.caseId) {
      caseData.value = await getCase(document.value.caseId)
      // Fetch related documents in background
      getRelatedDocuments(document.value.caseId, documentId.value, 5)
        .then(docs => { relatedDocs.value = docs })
        .catch(() => { /* ignore */ })
    }
    // Fetch pages/chunks if document is indexed
    if (document.value.status === 'indexed' || document.value.status === 'completed') {
      loadingPages.value = true
      Promise.all([
        getDocumentPages(documentId.value),
        getDocumentChunks(documentId.value)
      ]).then(([p, c]) => {
        pages.value = p
        chunks.value = c
      }).finally(() => {
        loadingPages.value = false
      })
    }
  } catch (err: any) {
    error.value = err?.message || 'Failed to load document'
  } finally {
    loading.value = false
  }
}

await fetchData()

// Helpers
function formatBytes(bytes: number) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function formatDate(date: any) {
  const d = date?.toDate?.() || new Date(date)
  return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
}

const statusColors: Record<string, string> = {
  uploading: 'warning',
  processing: 'info',
  indexed: 'success',
  completed: 'success',
  failed: 'error'
}

// Actions
async function handleDownload() {
  if (!document.value?.downloadUrl) return
  window.open(document.value.downloadUrl, '_blank')
}

async function handleDelete() {
  if (!document.value) return
  isDeleting.value = true
  try {
    await deleteDocument(documentId.value)
    toast.add({ title: 'Deleted', description: 'Document deleted successfully', color: 'success' })
    router.push('/documents')
  } catch (err) {
    toast.add({ title: 'Error', description: 'Failed to delete document', color: 'error' })
    isDeleting.value = false
  }
}

function handleShare() {
  navigator.clipboard.writeText(window.location.href)
  toast.add({ title: 'Copied', description: 'Link copied to clipboard', color: 'success' })
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar>
        <template #leading>
          <div class="flex items-center gap-3">
            <UButton
              icon="i-lucide-arrow-left"
              color="neutral"
              variant="ghost"
              @click="router.back()"
            />
            <USeparator orientation="vertical" class="h-6" />
            <UBreadcrumb
              :items="[
                { label: 'Documents', to: '/documents', icon: 'i-lucide-folder' },
                { label: document?.filename || 'Document', icon: 'i-lucide-file-text' }
              ]"
            />
          </div>
        </template>
        <template #trailing>
          <div class="flex items-center gap-2">
            <UButton
              icon="i-lucide-download"
              color="neutral"
              variant="ghost"
              @click="handleDownload"
            />
            <UButton
              icon="i-lucide-share"
              color="neutral"
              variant="ghost"
              @click="handleShare"
            />
            <UButton
              icon="i-lucide-trash"
              color="error"
              variant="ghost"
              @click="showDeleteModal = true"
            />
          </div>
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <UIcon name="i-lucide-loader-circle" class="size-12 text-primary animate-spin" />
      </div>

      <!-- Error -->
      <div v-else-if="error || !document" class="text-center py-20">
        <UIcon name="i-lucide-alert-circle" class="size-16 text-error mx-auto mb-4 opacity-50" />
        <h3 class="text-xl font-semibold mb-2">
          Document Not Found
        </h3>
        <p class="text-muted mb-6">
          {{ error || 'The document you are looking for does not exist.' }}
        </p>
        <UButton label="Back to Documents" icon="i-lucide-arrow-left" to="/documents" />
      </div>

      <!-- Document Content -->
      <div v-else class="h-full flex flex-col">
        <!-- Header -->
        <div class="shrink-0 border-b border-default bg-elevated p-4">
          <div class="max-w-7xl mx-auto flex items-start gap-4">
            <div class="p-3 bg-primary/10 rounded-lg">
              <UIcon name="i-lucide-file-text" class="size-8 text-primary" />
            </div>
            <div class="flex-1 min-w-0">
              <h1 class="text-xl font-bold truncate">
                {{ document.title || document.filename }}
              </h1>
              <div class="flex items-center gap-3 mt-1 flex-wrap">
                <UBadge :label="document.status || 'pending'" :color="statusColors[document.status] || 'neutral'" variant="soft" size="sm" />
                <span class="text-sm text-muted">{{ formatBytes(document.fileSize) }}</span>
                <span v-if="document.pageCount" class="text-sm text-muted">{{ document.pageCount }} pages</span>
                <span v-if="caseData" class="text-sm">
                  <NuxtLink :to="`/cases/${caseData.id}`" class="text-primary hover:underline flex items-center gap-1">
                    <UIcon name="i-lucide-briefcase" class="size-3" />
                    {{ caseData.name }}
                  </NuxtLink>
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Tabs -->
        <div class="shrink-0 border-b border-default bg-default">
          <div class="max-w-7xl mx-auto">
            <div class="flex gap-4 px-4">
              <button
                v-for="tab in tabs"
                :key="tab.value"
                class="flex items-center gap-2 px-3 py-3 text-sm font-medium border-b-2 transition-colors"
                :class="activeTab === tab.value
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted hover:text-foreground hover:border-muted'"
                @click="activeTab = tab.value"
              >
                <UIcon :name="tab.icon" class="size-4" />
                {{ tab.label }}
              </button>
            </div>
          </div>
        </div>

        <!-- Tab Content -->
        <div class="flex-1 overflow-y-auto">
          <!-- Content Tab - PDF Viewer -->
          <div v-if="activeTab === 'content'" class="p-4 max-w-7xl mx-auto">
            <!-- Processing State -->
            <div v-if="document.status === 'processing'" class="text-center py-20">
              <UIcon name="i-lucide-loader-circle" class="size-12 text-primary animate-spin mx-auto mb-4" />
              <h3 class="text-lg font-semibold mb-2">Processing Document</h3>
              <p class="text-muted">Extracting content and generating embeddings...</p>
            </div>

            <!-- Failed State -->
            <div v-else-if="document.status === 'failed'" class="text-center py-20">
              <UIcon name="i-lucide-alert-circle" class="size-12 text-error mx-auto mb-4 opacity-50" />
              <h3 class="text-lg font-semibold mb-2">Extraction Failed</h3>
              <p class="text-muted mb-4">{{ document.error || 'Failed to process document' }}</p>
              <UButton label="Download Original" icon="i-lucide-download" @click="handleDownload" />
            </div>

            <!-- PDF Viewer (for indexed documents) -->
            <div v-else-if="document.downloadUrl && document.mimeType === 'application/pdf'">
              <UCard class="overflow-hidden">
                <template #header>
                  <div class="flex items-center justify-between">
                    <h3 class="font-semibold">Document Preview</h3>
                    <div class="flex items-center gap-2 text-sm text-muted">
                      <span v-if="pages.length">{{ pages.length }} pages extracted</span>
                      <span v-if="chunks.length">{{ chunks.length }} chunks indexed</span>
                    </div>
                  </div>
                </template>
                <div class="aspect-[3/4] bg-muted/10">
                  <iframe
                    :src="document.downloadUrl"
                    class="w-full h-full border-0"
                    title="PDF Preview"
                  />
                </div>
              </UCard>
            </div>

            <!-- Markdown Preview (for extracted text) -->
            <div v-else-if="document.markdownPreview" class="prose prose-sm dark:prose-invert max-w-none">
              <UCard>
                <template #header>
                  <h3 class="font-semibold">Extracted Content</h3>
                </template>
                <div class="whitespace-pre-wrap text-sm text-muted">
                  {{ document.markdownPreview }}
                </div>
              </UCard>
            </div>

            <!-- Fallback: Download only -->
            <div v-else class="text-center py-20">
              <UIcon name="i-lucide-file" class="size-16 text-muted mx-auto mb-4 opacity-30" />
              <h3 class="text-lg font-semibold mb-2">Preview Not Available</h3>
              <p class="text-muted mb-4">This document type cannot be previewed in the browser.</p>
              <UButton label="Download Document" icon="i-lucide-download" @click="handleDownload" />
            </div>
          </div>

          <!-- Metadata Tab -->
          <div v-else-if="activeTab === 'metadata'" class="p-4 max-w-3xl mx-auto space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <UCard :ui="{ body: 'p-4' }">
                <p class="text-xs text-muted mb-1">Filename</p>
                <p class="font-medium truncate">{{ document.filename }}</p>
              </UCard>
              <UCard :ui="{ body: 'p-4' }">
                <p class="text-xs text-muted mb-1">Uploaded</p>
                <p class="font-medium">{{ formatDate(document.createdAt) }}</p>
              </UCard>
              <UCard :ui="{ body: 'p-4' }">
                <p class="text-xs text-muted mb-1">Type</p>
                <p class="font-medium capitalize">{{ document.documentType || 'General' }}</p>
              </UCard>
              <UCard :ui="{ body: 'p-4' }">
                <p class="text-xs text-muted mb-1">Size</p>
                <p class="font-medium">{{ formatBytes(document.fileSize) }}</p>
              </UCard>
              <UCard :ui="{ body: 'p-4' }">
                <p class="text-xs text-muted mb-1">MIME Type</p>
                <p class="font-medium">{{ document.mimeType }}</p>
              </UCard>
              <UCard :ui="{ body: 'p-4' }">
                <p class="text-xs text-muted mb-1">Status</p>
                <UBadge :label="document.status" :color="statusColors[document.status] || 'neutral'" />
              </UCard>
              <UCard v-if="document.pageCount" :ui="{ body: 'p-4' }">
                <p class="text-xs text-muted mb-1">Pages</p>
                <p class="font-medium">{{ document.pageCount }}</p>
              </UCard>
              <UCard v-if="document.chunkCount" :ui="{ body: 'p-4' }">
                <p class="text-xs text-muted mb-1">Indexed Chunks</p>
                <p class="font-medium">{{ document.chunkCount }}</p>
              </UCard>
            </div>

            <!-- Extraction Info -->
            <UCard v-if="document.extraction">
              <template #header>
                <h3 class="font-semibold">Extraction Details</h3>
              </template>
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span class="text-muted">Provider:</span>
                  <span class="ml-2">{{ document.extraction.provider }}</span>
                </div>
                <div>
                  <span class="text-muted">Processing Time:</span>
                  <span class="ml-2">{{ document.extraction.processingTimeMs }}ms</span>
                </div>
                <div>
                  <span class="text-muted">OCR Used:</span>
                  <span class="ml-2">{{ document.extraction.usedOcr ? 'Yes' : 'No' }}</span>
                </div>
                <div v-if="document.extraction.language">
                  <span class="text-muted">Language:</span>
                  <span class="ml-2">{{ document.extraction.language }}</span>
                </div>
              </div>
            </UCard>

            <!-- Summary -->
            <UCard v-if="document.summary">
              <template #header>
                <h3 class="font-semibold">Summary</h3>
              </template>
              <p class="text-muted">{{ document.summary }}</p>
            </UCard>

            <!-- Actions -->
            <UCard>
              <template #header>
                <h3 class="font-semibold">Actions</h3>
              </template>
              <div class="flex flex-wrap gap-2">
                <UButton label="Download" icon="i-lucide-download" variant="soft" @click="handleDownload" />
                <UButton v-if="document.caseId" label="View Case" icon="i-lucide-folder" variant="outline" :to="`/cases/${document.caseId}`" />
                <UButton label="Share Link" icon="i-lucide-share" variant="outline" @click="handleShare" />
              </div>
            </UCard>
          </div>

          <!-- Related Tab -->
          <div v-else-if="activeTab === 'related'" class="p-4 max-w-3xl mx-auto space-y-4">
            <div v-if="!document.caseId" class="text-center py-12">
              <UIcon name="i-lucide-folder-x" class="size-12 text-muted mx-auto mb-4 opacity-30" />
              <h3 class="text-lg font-semibold mb-2">No Case Assigned</h3>
              <p class="text-muted">This document is not associated with a case.</p>
            </div>

            <div v-else-if="relatedDocs.length === 0" class="text-center py-12">
              <UIcon name="i-lucide-files" class="size-12 text-muted mx-auto mb-4 opacity-30" />
              <h3 class="text-lg font-semibold mb-2">No Related Documents</h3>
              <p class="text-muted">There are no other documents in this case.</p>
            </div>

            <template v-else>
              <p class="text-sm text-muted">Other documents in {{ caseData?.name || 'this case' }}:</p>
              <div class="space-y-2">
                <UCard
                  v-for="doc in relatedDocs"
                  :key="doc.id"
                  class="cursor-pointer hover:shadow-md transition-shadow"
                  @click="router.push(`/documents/${doc.id}`)"
                >
                  <div class="flex items-center gap-3">
                    <UIcon name="i-lucide-file-text" class="size-5 text-muted shrink-0" />
                    <div class="flex-1 min-w-0">
                      <p class="font-medium truncate">{{ doc.filename }}</p>
                      <div class="flex items-center gap-2 text-xs text-muted">
                        <span>{{ formatBytes(doc.fileSize) }}</span>
                        <UBadge :label="doc.status" :color="statusColors[doc.status] || 'neutral'" size="xs" />
                      </div>
                    </div>
                    <UIcon name="i-lucide-chevron-right" class="size-4 text-muted" />
                  </div>
                </UCard>
              </div>
            </template>
          </div>
        </div>
      </div>
    </template>
  </UDashboardPanel>

  <!-- Delete Modal -->
  <ClientOnly>
    <UModal v-model:open="showDeleteModal" title="Delete Document">
      <template #body>
        <p class="text-muted">
          Are you sure you want to delete <strong>{{ document?.filename }}</strong>? This cannot be undone.
        </p>
      </template>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton label="Cancel" variant="ghost" @click="showDeleteModal = false" />
          <UButton
            label="Delete"
            color="error"
            :loading="isDeleting"
            @click="handleDelete"
          />
        </div>
      </template>
    </UModal>
  </ClientOnly>
</template>
