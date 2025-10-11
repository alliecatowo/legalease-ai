<script setup lang="ts">
import { ref, computed } from 'vue'

definePageMeta({
  layout: 'default'
})

const route = useRoute()
const router = useRouter()
const api = useApi()
const toast = useToast()

const documentId = computed(() => route.params.id as string)

// Fetch document details
const { data: document, pending: loadingDocument, error: documentError, refresh: refreshDocument } = await useAsyncData(
  `document-${documentId.value}`,
  () => api.documents.get(documentId.value),
  {
    default: () => null
  }
)

// Fetch document content
const { data: content, pending: loadingContent, error: contentError } = await useAsyncData(
  `document-content-${documentId.value}`,
  () => api.documents.content(documentId.value),
  {
    default: () => null
  }
)

// Fetch case details if document has case_id (lazy loading)
const { data: caseData } = useLazyAsyncData(
  `case-${documentId.value}`,
  async () => {
    if (!document.value?.case_id) return null
    try {
      return await api.cases.get(document.value.case_id.toString())
    } catch (err) {
      console.error('Failed to load case:', err)
      return null
    }
  },
  {
    default: () => null,
    watch: [() => document.value?.case_id]
  }
)

// Fetch related documents from the same case (lazy loading)
const { data: relatedDocs } = useLazyAsyncData(
  `related-docs-${documentId.value}`,
  async () => {
    if (!document.value?.case_id) return []
    try {
      const response = await api.documents.listByCase(document.value.case_id)
      return response?.documents?.filter((d: any) => d.id !== parseInt(documentId.value)) || []
    } catch (err) {
      console.error('Failed to load related docs:', err)
      return []
    }
  },
  {
    default: () => [],
    watch: [() => document.value?.case_id]
  }
)

// UI State
const selectedTab = ref('content')
const showDeleteModal = ref(false)
const showAddToCaseModal = ref(false)
const isDeleting = ref(false)
const searchWithinQuery = ref('')
const searchWithinResults = ref<any[]>([])

// Document type configuration
const typeConfig = computed(() => {
  const docType = document.value?.meta_data?.document_type || 'general'
  const configs: Record<string, { icon: string; color: string; label: string; iconClass: string }> = {
    contract: { icon: 'i-lucide-file-text', color: 'primary', label: 'Contract', iconClass: 'text-primary' },
    agreement: { icon: 'i-lucide-handshake', color: 'info', label: 'Agreement', iconClass: 'text-info' },
    transcript: { icon: 'i-lucide-mic', color: 'warning', label: 'Transcript', iconClass: 'text-warning' },
    court_filing: { icon: 'i-lucide-gavel', color: 'error', label: 'Court Filing', iconClass: 'text-error' },
    brief: { icon: 'i-lucide-file-pen', color: 'success', label: 'Brief', iconClass: 'text-success' },
    motion: { icon: 'i-lucide-file-check', color: 'secondary', label: 'Motion', iconClass: 'text-secondary' },
    general: { icon: 'i-lucide-file', color: 'neutral', label: 'Document', iconClass: 'text-neutral' }
  }
  return configs[docType] || configs.general
})

// Status badge configuration
const statusConfig = computed(() => {
  const status = document.value?.status || 'pending'
  const configs: Record<string, { color: string; label: string; icon: string }> = {
    pending: { color: 'warning', label: 'Pending', icon: 'i-lucide-clock' },
    processing: { color: 'info', label: 'Processing', icon: 'i-lucide-loader-circle' },
    indexed: { color: 'success', label: 'Indexed', icon: 'i-lucide-check-circle' },
    failed: { color: 'error', label: 'Failed', icon: 'i-lucide-alert-circle' }
  }
  return configs[status] || configs.pending
})

// Format helpers
function formatBytes(bytes: number) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Extract stats from document
const documentStats = computed(() => {
  const text = content.value?.text || ''
  const wordCount = text.split(/\s+/).filter(Boolean).length
  const pageCount = document.value?.meta_data?.page_count ||
                    document.value?.meta_data?.pages ||
                    Math.ceil(wordCount / 300) // Estimate pages

  return {
    wordCount,
    pageCount,
    charCount: text.length,
    paragraphCount: text.split(/\n\n+/).filter(Boolean).length
  }
})

// Extract entities from metadata
const entities = computed(() => {
  const meta = document.value?.meta_data || {}
  const extracted: Array<{ type: string; text: string; icon: string }> = []

  // Extract parties
  if (meta.parties && Array.isArray(meta.parties)) {
    meta.parties.forEach((party: string) => {
      extracted.push({ type: 'PERSON', text: party, icon: 'i-lucide-user' })
    })
  }

  // Extract court
  if (meta.court) {
    extracted.push({ type: 'COURT', text: meta.court, icon: 'i-lucide-landmark' })
  }

  // Extract organizations
  if (meta.organizations && Array.isArray(meta.organizations)) {
    meta.organizations.forEach((org: string) => {
      extracted.push({ type: 'ORGANIZATION', text: org, icon: 'i-lucide-building' })
    })
  }

  // Extract dates
  if (meta.filing_date) {
    extracted.push({
      type: 'DATE',
      text: new Date(meta.filing_date).toLocaleDateString(),
      icon: 'i-lucide-calendar'
    })
  }

  // Extract entities array if present
  if (meta.entities && Array.isArray(meta.entities)) {
    meta.entities.forEach((entity: any) => {
      const icon = entity.type === 'PERSON' ? 'i-lucide-user' :
                   entity.type === 'ORGANIZATION' ? 'i-lucide-building' :
                   entity.type === 'LOCATION' ? 'i-lucide-map-pin' :
                   'i-lucide-tag'
      extracted.push({ type: entity.type, text: entity.text, icon })
    })
  }

  return extracted
})

// Tags from metadata
const tags = computed(() => {
  return document.value?.meta_data?.tags || []
})

// Search within document
function searchWithinDocument() {
  if (!searchWithinQuery.value.trim() || !content.value?.text) {
    searchWithinResults.value = []
    return
  }

  const text = content.value.text
  const query = searchWithinQuery.value.toLowerCase()
  const results: any[] = []

  // Split into paragraphs
  const paragraphs = text.split(/\n\n+/)

  paragraphs.forEach((para, idx) => {
    if (para.toLowerCase().includes(query)) {
      results.push({
        index: idx,
        text: para.substring(0, 300) + (para.length > 300 ? '...' : ''),
        highlighted: highlightText(para.substring(0, 300), query)
      })
    }
  })

  searchWithinResults.value = results.slice(0, 50) // Limit to 50 results
}

function highlightText(text: string, query: string): string {
  if (!query) return text
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
  return text.replace(regex, '<mark class="bg-primary/20 text-primary-600 dark:text-primary-400 font-medium px-0.5 rounded">$1</mark>')
}

// Actions
async function handleDownload() {
  if (!import.meta.client) return

  try {
    const response = await api.documents.download(documentId.value)
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response]))
    const link = window.document.createElement('a')
    link.href = url
    link.download = document.value?.filename || 'document'
    link.click()
    window.URL.revokeObjectURL(url)

    toast.add({
      title: 'Download Started',
      description: `Downloading ${document.value?.filename}`,
      color: 'success',
      icon: 'i-lucide-download'
    })
  } catch (error) {
    console.error('Download error:', error)
  }
}

async function handleDelete() {
  if (!document.value) return

  isDeleting.value = true
  try {
    await api.documents.delete(documentId.value)
    toast.add({
      title: 'Document Deleted',
      description: `${document.value.filename} has been deleted`,
      color: 'success',
      icon: 'i-lucide-trash'
    })
    router.push('/documents')
  } catch (error) {
    console.error('Delete error:', error)
    isDeleting.value = false
  }
}

function handleShare() {
  // Copy link to clipboard
  const url = window.location.href
  navigator.clipboard.writeText(url)
  toast.add({
    title: 'Link Copied',
    description: 'Document link copied to clipboard',
    color: 'success',
    icon: 'i-lucide-link'
  })
}

// Get file extension
const fileExtension = computed(() => {
  const filename = document.value?.filename || ''
  return filename.split('.').pop()?.toUpperCase() || 'FILE'
})

// Check if file is viewable
const isViewable = computed(() => {
  const ext = fileExtension.value.toLowerCase()
  return ['txt', 'md', 'json', 'xml', 'html'].includes(ext) || content.value?.text
})

// Breadcrumb items
const breadcrumbItems = computed(() => {
  const items = [
    { label: 'Documents', to: '/documents', icon: 'i-lucide-folder' }
  ]

  if (caseData.value?.name && caseData.value?.id) {
    items.push({
      label: caseData.value.name,
      to: `/cases/${caseData.value.id}`,
      icon: 'i-lucide-briefcase'
    })
  }

  if (document.value) {
    items.push({
      label: document.value.filename || 'Document',
      to: route.path,
      icon: typeConfig.value.icon
    })
  }

  return items
})

// Tab items - make it computed to reactively update badge
const tabItems = computed(() => [
  { key: 'content', label: 'Content', icon: 'i-lucide-file-text' },
  { key: 'metadata', label: 'Metadata', icon: 'i-lucide-info' },
  { key: 'activity', label: 'Activity', icon: 'i-lucide-activity' },
  { key: 'related', label: 'Related', icon: 'i-lucide-link', badge: relatedDocs.value?.length || 0 }
])
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
            <UBreadcrumb :items="breadcrumbItems" />
          </div>
        </template>
        <template #trailing>
          <div class="flex items-center gap-2">
            <UTooltip text="Refresh">
              <UButton
                icon="i-lucide-refresh-cw"
                color="neutral"
                variant="ghost"
                :loading="loadingDocument"
                @click="refreshDocument"
              />
            </UTooltip>
            <UTooltip text="Download">
              <UButton
                icon="i-lucide-download"
                color="neutral"
                variant="ghost"
                @click="handleDownload"
              />
            </UTooltip>
            <UTooltip text="Share">
              <UButton
                icon="i-lucide-share"
                color="neutral"
                variant="ghost"
                @click="handleShare"
              />
            </UTooltip>
            <UDropdownMenu
              :items="[
                [
                  { label: 'Add to Case', icon: 'i-lucide-folder-plus', click: () => showAddToCaseModal = true },
                  { label: 'Add Tags', icon: 'i-lucide-tag' },
                  { label: 'Export', icon: 'i-lucide-file-down' }
                ],
                [
                  { label: 'Delete', icon: 'i-lucide-trash', color: 'error', click: () => showDeleteModal = true }
                ]
              ]"
            >
              <UButton
                icon="i-lucide-more-vertical"
                color="neutral"
                variant="ghost"
              />
            </UDropdownMenu>
          </div>
        </template>
      </UDashboardNavbar>
    </template>

    <div class="overflow-y-auto h-[calc(100vh-64px)]">
      <!-- Error State -->
      <div v-if="documentError" class="flex items-center justify-center min-h-[60vh] p-6">
        <UCard class="max-w-md">
          <div class="text-center space-y-4">
            <UIcon name="i-lucide-alert-circle" class="size-16 text-error mx-auto" />
            <h3 class="text-xl font-semibold">Document Not Found</h3>
            <p class="text-muted">
              The document you're looking for doesn't exist or has been deleted.
            </p>
            <UButton
              label="Back to Documents"
              icon="i-lucide-arrow-left"
              color="primary"
              to="/documents"
            />
          </div>
        </UCard>
      </div>

      <!-- Loading State -->
      <div v-else-if="loadingDocument" class="p-6 space-y-6">
        <USkeleton class="h-32 w-full" />
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div class="lg:col-span-2 space-y-4">
            <USkeleton class="h-96 w-full" />
          </div>
          <div class="space-y-4">
            <USkeleton class="h-48 w-full" />
            <USkeleton class="h-48 w-full" />
          </div>
        </div>
      </div>

      <!-- Document Content -->
      <div v-else-if="document" class="max-w-7xl mx-auto p-6 space-y-6">
        <!-- Hero Section -->
        <div class="relative overflow-hidden rounded-xl border border-default bg-gradient-to-br from-primary/5 via-transparent to-secondary/5 p-8">
          <div class="flex items-start gap-6">
            <!-- Document Icon -->
            <div class="flex-shrink-0 p-4 bg-white dark:bg-gray-900 rounded-xl shadow-lg border border-default">
              <UIcon :name="typeConfig.icon" class="size-16" :class="typeConfig.iconClass" />
            </div>

            <!-- Document Info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-start justify-between gap-4 mb-3">
                <div class="flex-1 min-w-0">
                  <h1 class="text-3xl font-bold text-highlighted mb-2 break-words">
                    {{ document.meta_data?.title || document.filename }}
                  </h1>
                  <div class="flex items-center gap-3 flex-wrap">
                    <UBadge
                      :label="typeConfig.label"
                      :color="typeConfig.color"
                      variant="soft"
                    />
                    <UBadge
                      :label="statusConfig.label"
                      :color="statusConfig.color"
                      variant="subtle"
                    >
                      <template #leading>
                        <UIcon :name="statusConfig.icon" :class="statusConfig.icon.includes('loader') ? 'animate-spin' : ''" />
                      </template>
                    </UBadge>
                    <span class="text-sm text-muted">{{ formatBytes(document.size) }}</span>
                    <span class="text-sm text-muted">{{ fileExtension }}</span>
                  </div>
                </div>
              </div>

              <!-- Case Link -->
              <div v-if="caseData" class="flex items-center gap-2 text-sm">
                <UIcon name="i-lucide-briefcase" class="size-4 text-muted" />
                <span class="text-muted">Part of case:</span>
                <NuxtLink :to="`/cases/${caseData.id}`" class="text-primary hover:underline font-medium">
                  {{ caseData.name }}
                </NuxtLink>
              </div>

              <!-- Summary -->
              <p v-if="document.meta_data?.summary" class="mt-4 text-muted leading-relaxed">
                {{ document.meta_data.summary }}
              </p>
            </div>
          </div>
        </div>

        <!-- Stats Cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <UCard>
            <div class="flex items-center gap-3">
              <div class="p-2 bg-primary/10 rounded-lg">
                <UIcon name="i-lucide-file-text" class="size-5 text-primary" />
              </div>
              <div>
                <p class="text-2xl font-bold text-highlighted">{{ documentStats.pageCount }}</p>
                <p class="text-sm text-muted">Pages</p>
              </div>
            </div>
          </UCard>

          <UCard>
            <div class="flex items-center gap-3">
              <div class="p-2 bg-info/10 rounded-lg">
                <UIcon name="i-lucide-type" class="size-5 text-info" />
              </div>
              <div>
                <p class="text-2xl font-bold text-highlighted">{{ documentStats.wordCount.toLocaleString() }}</p>
                <p class="text-sm text-muted">Words</p>
              </div>
            </div>
          </UCard>

          <UCard>
            <div class="flex items-center gap-3">
              <div class="p-2 bg-success/10 rounded-lg">
                <UIcon name="i-lucide-align-left" class="size-5 text-success" />
              </div>
              <div>
                <p class="text-2xl font-bold text-highlighted">{{ documentStats.paragraphCount }}</p>
                <p class="text-sm text-muted">Paragraphs</p>
              </div>
            </div>
          </UCard>

          <UCard>
            <div class="flex items-center gap-3">
              <div class="p-2 bg-warning/10 rounded-lg">
                <UIcon name="i-lucide-calendar" class="size-5 text-warning" />
              </div>
              <div>
                <p class="text-sm font-semibold text-highlighted">{{ new Date(document.uploaded_at).toLocaleDateString() }}</p>
                <p class="text-sm text-muted">Uploaded</p>
              </div>
            </div>
          </UCard>
        </div>

        <!-- Main Content Area -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- Left: Document Viewer -->
          <div class="lg:col-span-2 space-y-4">
            <!-- Tabs -->
            <UCard>
              <template #header>
                <UTabs v-model="selectedTab" :items="tabItems" />
              </template>

              <!-- Content Tab -->
              <div v-if="selectedTab === 'content'" class="space-y-4">
                <!-- Search within document -->
                <div>
                  <UInput
                    v-model="searchWithinQuery"
                    icon="i-lucide-search"
                    placeholder="Search within this document..."
                    size="lg"
                    @keyup.enter="searchWithinDocument"
                  >
                    <template #trailing>
                      <UButton
                        v-if="searchWithinQuery"
                        label="Search"
                        size="xs"
                        @click="searchWithinDocument"
                      />
                    </template>
                  </UInput>
                </div>

                <!-- Search Results -->
                <div v-if="searchWithinResults.length > 0" class="space-y-2">
                  <p class="text-sm text-muted">
                    Found {{ searchWithinResults.length }} result{{ searchWithinResults.length > 1 ? 's' : '' }}
                  </p>
                  <div class="space-y-2 max-h-96 overflow-y-auto">
                    <div
                      v-for="(result, idx) in searchWithinResults"
                      :key="idx"
                      class="p-3 bg-muted/10 rounded-lg border border-default/50"
                    >
                      <p class="text-sm" v-html="result.highlighted" />
                    </div>
                  </div>
                </div>

                <!-- Document Content Viewer -->
                <div v-if="!searchWithinResults.length">
                  <div v-if="loadingContent" class="space-y-3">
                    <USkeleton class="h-4 w-full" />
                    <USkeleton class="h-4 w-5/6" />
                    <USkeleton class="h-4 w-4/6" />
                  </div>
                  <div v-else-if="contentError" class="text-center py-12">
                    <UIcon name="i-lucide-alert-circle" class="size-12 text-error mx-auto mb-4" />
                    <p class="text-muted">Failed to load document content</p>
                  </div>
                  <div v-else-if="content?.text" class="prose prose-sm dark:prose-invert max-w-none">
                    <div class="whitespace-pre-wrap font-mono text-sm bg-muted/5 p-6 rounded-lg border border-default">
                      {{ content.text }}
                    </div>
                  </div>
                  <div v-else class="text-center py-12">
                    <UIcon name="i-lucide-file-x" class="size-12 text-muted mx-auto mb-4 opacity-50" />
                    <p class="text-muted mb-4">Content preview not available for this file type</p>
                    <UButton
                      label="Download to View"
                      icon="i-lucide-download"
                      color="primary"
                      @click="handleDownload"
                    />
                  </div>
                </div>
              </div>

              <!-- Metadata Tab -->
              <div v-else-if="selectedTab === 'metadata'" class="space-y-4">
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <p class="text-sm text-muted mb-1">Filename</p>
                    <p class="font-medium text-highlighted">{{ document.filename }}</p>
                  </div>
                  <div>
                    <p class="text-sm text-muted mb-1">MIME Type</p>
                    <p class="font-medium text-highlighted">{{ document.mime_type || 'Unknown' }}</p>
                  </div>
                  <div>
                    <p class="text-sm text-muted mb-1">File Size</p>
                    <p class="font-medium text-highlighted">{{ formatBytes(document.size) }}</p>
                  </div>
                  <div>
                    <p class="text-sm text-muted mb-1">Uploaded</p>
                    <p class="font-medium text-highlighted">{{ formatDate(document.uploaded_at) }}</p>
                  </div>
                </div>

                <USeparator />

                <!-- Additional Metadata -->
                <div v-if="document.meta_data && Object.keys(document.meta_data).length > 0" class="space-y-3">
                  <h4 class="font-semibold text-highlighted">Additional Information</h4>
                  <div class="space-y-2">
                    <div
                      v-for="[key, value] in Object.entries(document.meta_data).filter(([k]) => !['title', 'summary', 'tags', 'entities', 'parties', 'organizations'].includes(k))"
                      :key="key"
                      class="flex items-start gap-3 p-3 bg-muted/10 rounded-lg"
                    >
                      <UIcon name="i-lucide-info" class="size-4 text-muted shrink-0 mt-0.5" />
                      <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium text-highlighted capitalize">{{ key.replace(/_/g, ' ') }}</p>
                        <p class="text-sm text-muted break-words">{{ typeof value === 'object' ? JSON.stringify(value) : value }}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Activity Tab -->
              <div v-else-if="selectedTab === 'activity'" class="space-y-4">
                <div class="text-center py-12">
                  <UIcon name="i-lucide-activity" class="size-12 text-muted mx-auto mb-4 opacity-50" />
                  <p class="text-muted">Activity history coming soon</p>
                </div>
              </div>

              <!-- Related Tab -->
              <div v-else-if="selectedTab === 'related'" class="space-y-3">
                <div v-if="relatedDocs && relatedDocs.length > 0" class="space-y-3">
                  <NuxtLink
                    v-for="doc in relatedDocs.slice(0, 10)"
                    :key="doc.id"
                    :to="`/documents/${doc.id}`"
                    class="block p-4 bg-muted/10 hover:bg-muted/20 rounded-lg border border-default/50 transition-colors"
                  >
                    <div class="flex items-center gap-3">
                      <UIcon name="i-lucide-file-text" class="size-5 text-muted" />
                      <div class="flex-1 min-w-0">
                        <p class="font-medium text-highlighted truncate">{{ doc.filename }}</p>
                        <p class="text-sm text-muted">{{ formatBytes(doc.size || 0) }}</p>
                      </div>
                      <UIcon name="i-lucide-arrow-right" class="size-4 text-muted" />
                    </div>
                  </NuxtLink>
                </div>
                <div v-else class="text-center py-12">
                  <UIcon name="i-lucide-link-2-off" class="size-12 text-muted mx-auto mb-4 opacity-50" />
                  <p class="text-muted">No related documents found</p>
                </div>
              </div>
            </UCard>
          </div>

          <!-- Right: Sidebar -->
          <div class="space-y-4">
            <!-- Entities -->
            <UCard v-if="entities.length > 0">
              <template #header>
                <div class="flex items-center gap-2">
                  <UIcon name="i-lucide-tags" class="size-5 text-primary" />
                  <h3 class="font-semibold text-highlighted">Entities</h3>
                </div>
              </template>
              <div class="space-y-2">
                <div
                  v-for="(entity, idx) in entities"
                  :key="idx"
                  class="flex items-center gap-2 p-2 bg-muted/10 rounded-lg"
                >
                  <UIcon :name="entity.icon" class="size-4 text-muted" />
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-highlighted truncate">{{ entity.text }}</p>
                    <p class="text-xs text-muted">{{ entity.type }}</p>
                  </div>
                </div>
              </div>
            </UCard>

            <!-- Tags -->
            <UCard v-if="tags.length > 0">
              <template #header>
                <div class="flex items-center gap-2">
                  <UIcon name="i-lucide-tag" class="size-5 text-primary" />
                  <h3 class="font-semibold text-highlighted">Tags</h3>
                </div>
              </template>
              <div class="flex flex-wrap gap-2">
                <UBadge
                  v-for="tag in tags"
                  :key="tag"
                  :label="tag"
                  color="primary"
                  variant="soft"
                />
              </div>
            </UCard>

            <!-- Document Info -->
            <UCard>
              <template #header>
                <div class="flex items-center gap-2">
                  <UIcon name="i-lucide-info" class="size-5 text-primary" />
                  <h3 class="font-semibold text-highlighted">Document Info</h3>
                </div>
              </template>
              <div class="space-y-3">
                <div>
                  <p class="text-xs text-muted mb-1">File Path</p>
                  <p class="text-sm font-mono text-highlighted break-all">{{ document.file_path }}</p>
                </div>
                <USeparator />
                <div>
                  <p class="text-xs text-muted mb-1">Document ID</p>
                  <p class="text-sm font-mono text-highlighted">{{ document.id }}</p>
                </div>
                <div>
                  <p class="text-xs text-muted mb-1">Case ID</p>
                  <p class="text-sm font-mono text-highlighted">{{ document.case_id }}</p>
                </div>
              </div>
            </UCard>

            <!-- Quick Actions -->
            <UCard>
              <template #header>
                <div class="flex items-center gap-2">
                  <UIcon name="i-lucide-zap" class="size-5 text-primary" />
                  <h3 class="font-semibold text-highlighted">Quick Actions</h3>
                </div>
              </template>
              <div class="space-y-2">
                <UButton
                  label="Download Document"
                  icon="i-lucide-download"
                  color="primary"
                  variant="soft"
                  block
                  @click="handleDownload"
                />
                <UButton
                  label="Search Similar"
                  icon="i-lucide-search"
                  color="neutral"
                  variant="soft"
                  block
                  @click="router.push(`/search?q=${document.filename}`)"
                />
                <UButton
                  label="Add to Case"
                  icon="i-lucide-folder-plus"
                  color="neutral"
                  variant="soft"
                  block
                  @click="showAddToCaseModal = true"
                />
                <UButton
                  label="Share Document"
                  icon="i-lucide-share"
                  color="neutral"
                  variant="soft"
                  block
                  @click="handleShare"
                />
              </div>
            </UCard>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <UModal v-model:open="showDeleteModal" title="Delete Document">
      <template #body>
        <div class="space-y-4">
          <div class="flex items-center gap-3">
            <div class="p-2 bg-error/10 rounded-lg">
              <UIcon name="i-lucide-alert-triangle" class="size-5 text-error" />
            </div>
            <p class="text-muted">
              Are you sure you want to delete <strong class="text-highlighted">{{ document?.filename }}</strong>?
              This action cannot be undone.
            </p>
          </div>
          <UAlert
            color="error"
            variant="soft"
            icon="i-lucide-info"
            title="Warning"
            description="All associated data and search indexes will be permanently removed."
          />
        </div>
      </template>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton
            label="Cancel"
            color="neutral"
            variant="ghost"
            @click="showDeleteModal = false"
          />
          <UButton
            label="Delete Document"
            icon="i-lucide-trash"
            color="error"
            :loading="isDeleting"
            @click="handleDelete"
          />
        </div>
      </template>
    </UModal>

    <!-- Add to Case Modal (Placeholder) -->
    <UModal v-model:open="showAddToCaseModal" title="Add to Case">
      <template #body>
        <div class="text-center py-8">
          <UIcon name="i-lucide-folder-plus" class="size-12 text-muted mx-auto mb-4 opacity-50" />
          <p class="text-muted">Case management coming soon</p>
        </div>
      </template>

      <template #footer>
        <div class="flex justify-end">
          <UButton
            label="Close"
            color="neutral"
            variant="ghost"
            @click="showAddToCaseModal = false"
          />
        </div>
      </template>
    </UModal>
  </UDashboardPanel>
</template>
