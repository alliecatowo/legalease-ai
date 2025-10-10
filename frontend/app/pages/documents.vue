<script setup lang="ts">
import { ref, computed } from 'vue'

const api = useApi()
const { data: documents, refresh } = await useFetch('/api/v1/documents')

const searchQuery = ref('')
const selectedType = ref('all')
const sortBy = ref('recent')
const viewMode = ref<'list' | 'grid'>('list')
const selectedDocuments = ref<Set<string>>(new Set())
const showUploadModal = ref(false)
const showBulkActionsModal = ref(false)
const uploadingFiles = ref<File[]>([])
const uploadProgress = ref(0)

const typeOptions = [
  { label: 'All Documents', value: 'all' },
  { label: 'Contracts', value: 'contract' },
  { label: 'Agreements', value: 'agreement' },
  { label: 'Transcripts', value: 'transcript' },
  { label: 'Court Filings', value: 'court_filing' },
  { label: 'General', value: 'general' }
]

const sortOptions = [
  { label: 'Most Recent', value: 'recent' },
  { label: 'Oldest First', value: 'oldest' },
  { label: 'Name (A-Z)', value: 'name_asc' },
  { label: 'Name (Z-A)', value: 'name_desc' },
  { label: 'Size (Largest)', value: 'size_desc' },
  { label: 'Size (Smallest)', value: 'size_asc' }
]

const filteredDocuments = computed(() => {
  if (!documents.value) return []

  let filtered = [...documents.value]

  // Filter by type
  if (selectedType.value !== 'all') {
    filtered = filtered.filter(d => d.document_type === selectedType.value)
  }

  // Filter by search
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(d =>
      d.filename?.toLowerCase().includes(query) ||
      d.title?.toLowerCase().includes(query) ||
      d.summary?.toLowerCase().includes(query)
    )
  }

  // Sort
  filtered.sort((a, b) => {
    switch (sortBy.value) {
      case 'recent':
        return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      case 'oldest':
        return new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime()
      case 'name_asc':
        return (a.title || a.filename).localeCompare(b.title || b.filename)
      case 'name_desc':
        return (b.title || b.filename).localeCompare(a.title || a.filename)
      case 'size_desc':
        return (b.file_size || 0) - (a.file_size || 0)
      case 'size_asc':
        return (a.file_size || 0) - (b.file_size || 0)
      default:
        return 0
    }
  })

  return filtered
})

const stats = computed(() => {
  if (!documents.value) return { total: 0, thisMonth: 0, storage: 0 }

  const now = new Date()
  const thisMonth = documents.value.filter(d => {
    const createdAt = new Date(d.created_at)
    return createdAt.getMonth() === now.getMonth() && createdAt.getFullYear() === now.getFullYear()
  })

  return {
    total: documents.value.length,
    thisMonth: thisMonth.length,
    storage: documents.value.reduce((acc, d) => acc + (d.file_size || 0), 0)
  }
})

// Bulk selection
const allSelected = computed(() => {
  return filteredDocuments.value.length > 0 &&
    filteredDocuments.value.every(d => selectedDocuments.value.has(d.id))
})

function toggleSelectAll() {
  if (allSelected.value) {
    selectedDocuments.value.clear()
  } else {
    filteredDocuments.value.forEach(d => selectedDocuments.value.add(d.id))
  }
}

function toggleSelect(docId: string) {
  if (selectedDocuments.value.has(docId)) {
    selectedDocuments.value.delete(docId)
  } else {
    selectedDocuments.value.add(docId)
  }
}

// File upload handling
function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files) {
    uploadingFiles.value = Array.from(input.files)
    showUploadModal.value = true
  }
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer?.files) {
    uploadingFiles.value = Array.from(event.dataTransfer.files)
    showUploadModal.value = true
  }
}

async function uploadDocuments() {
  // TODO: Implement actual upload with progress tracking
  uploadProgress.value = 0

  const formData = new FormData()
  uploadingFiles.value.forEach(file => {
    formData.append('files', file)
  })

  try {
    // Simulate upload progress
    const progressInterval = setInterval(() => {
      uploadProgress.value += 10
      if (uploadProgress.value >= 100) {
        clearInterval(progressInterval)
      }
    }, 200)

    // TODO: Replace with actual API call
    // await api.documents.upload(formData)

    await new Promise(resolve => setTimeout(resolve, 2000))

    showUploadModal.value = false
    uploadingFiles.value = []
    refresh()
  } catch (error) {
    console.error('Upload failed:', error)
  }
}

// Bulk actions
async function handleBulkAction(action: string) {
  const selectedIds = Array.from(selectedDocuments.value)

  switch (action) {
    case 'delete':
      if (confirm(`Delete ${selectedIds.length} documents?`)) {
        // TODO: Implement bulk delete
        selectedDocuments.value.clear()
        refresh()
      }
      break
    case 'download':
      // TODO: Implement bulk download
      break
    case 'tag':
      // TODO: Show tag modal
      break
    case 'move-to-case':
      // TODO: Show case selection modal
      break
  }
}

// Document actions
async function downloadDocument(docId: string) {
  // TODO: Implement download
  console.log('Download document:', docId)
}

async function deleteDocument(docId: string) {
  if (confirm('Delete this document?')) {
    // TODO: Implement delete
    refresh()
  }
}

function formatBytes(bytes: number) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

const documentTypeLabels: Record<string, string> = {
  contract: 'Contract',
  agreement: 'Agreement',
  transcript: 'Transcript',
  court_filing: 'Court Filing',
  general: 'Document'
}

const documentTypeIcons: Record<string, string> = {
  contract: 'i-lucide-file-text',
  agreement: 'i-lucide-handshake',
  transcript: 'i-lucide-mic',
  court_filing: 'i-lucide-gavel',
  general: 'i-lucide-file'
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Document Library">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #trailing>
          <UButton
            icon="i-lucide-upload"
            label="Upload"
            color="primary"
            @click="showUploadModal = true"
          />
        </template>
      </UDashboardNavbar>
    </template>

    <div class="p-6 space-y-6">
      <!-- Bulk Actions Banner -->
      <div v-if="selectedDocuments.size > 0" class="bg-primary/10 border border-primary rounded-lg p-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <UIcon name="i-lucide-check-circle" class="size-5 text-primary" />
            <span class="font-medium text-highlighted">
              {{ selectedDocuments.size }} document{{ selectedDocuments.size > 1 ? 's' : '' }} selected
            </span>
          </div>
          <div class="flex items-center gap-2">
            <UButton
              label="Move to Case"
              icon="i-lucide-folder-plus"
              color="neutral"
              variant="ghost"
              size="sm"
              @click="handleBulkAction('move-to-case')"
            />
            <UButton
              label="Add Tags"
              icon="i-lucide-tag"
              color="neutral"
              variant="ghost"
              size="sm"
              @click="handleBulkAction('tag')"
            />
            <UButton
              label="Download"
              icon="i-lucide-download"
              color="neutral"
              variant="ghost"
              size="sm"
              @click="handleBulkAction('download')"
            />
            <UButton
              label="Delete"
              icon="i-lucide-trash"
              color="error"
              variant="ghost"
              size="sm"
              @click="handleBulkAction('delete')"
            />
            <UDivider orientation="vertical" class="h-6" />
            <UButton
              label="Clear"
              color="neutral"
              variant="ghost"
              size="sm"
              @click="selectedDocuments.clear()"
            />
          </div>
        </div>
      </div>

      <!-- Controls -->
      <div class="flex items-center gap-3 flex-wrap">
        <!-- Select All Checkbox -->
        <UCheckbox
          :model-value="allSelected"
          :indeterminate="selectedDocuments.size > 0 && !allSelected"
          @update:model-value="toggleSelectAll"
        >
          <template #label>
            <span class="text-sm text-muted">Select All</span>
          </template>
        </UCheckbox>

        <!-- Search -->
        <div class="flex-1 min-w-[240px]">
          <UInput
            v-model="searchQuery"
            icon="i-lucide-search"
            placeholder="Search documents..."
            size="lg"
          />
        </div>

        <!-- Filters -->
        <USelectMenu v-model="selectedType" :items="typeOptions" size="lg" />
        <USelectMenu v-model="sortBy" :items="sortOptions" size="lg" />

        <!-- View Mode Toggle -->
        <div class="flex items-center gap-1 border border-default rounded-lg p-1">
          <UButton
            :variant="viewMode === 'list' ? 'solid' : 'ghost'"
            color="neutral"
            size="sm"
            icon="i-lucide-list"
            @click="viewMode = 'list'"
          />
          <UButton
            :variant="viewMode === 'grid' ? 'solid' : 'ghost'"
            color="neutral"
            size="sm"
            icon="i-lucide-grid-3x3"
            @click="viewMode = 'grid'"
          />
        </div>
      </div>

      <!-- List View -->
      <div v-if="viewMode === 'list'" class="space-y-3">
        <UCard
          v-for="doc in filteredDocuments"
          :key="doc.id"
          class="hover:shadow-md transition-all cursor-pointer"
          :class="selectedDocuments.has(doc.id) ? 'ring-2 ring-primary' : ''"
          @click="navigateTo(`/documents/${doc.id}`)"
        >
          <div class="flex items-start gap-4">
            <!-- Checkbox -->
            <UCheckbox
              :model-value="selectedDocuments.has(doc.id)"
              @update:model-value="toggleSelect(doc.id)"
              @click.stop
            />

            <!-- Icon -->
            <div class="flex-shrink-0 p-3 bg-primary/10 rounded-lg">
              <UIcon
                :name="documentTypeIcons[doc.document_type] || 'i-lucide-file'"
                class="size-6 text-primary"
              />
            </div>

            <!-- Content -->
            <div class="flex-1 min-w-0">
              <div class="flex items-start justify-between gap-4">
                <div class="flex-1 min-w-0">
                  <h3 class="font-semibold text-base truncate">
                    {{ doc.title || doc.filename }}
                  </h3>
                  <div class="flex items-center gap-3 mt-1 text-sm text-muted flex-wrap">
                    <UBadge color="neutral" variant="subtle" size="sm">
                      {{ documentTypeLabels[doc.document_type] || 'Document' }}
                    </UBadge>
                    <span>{{ formatBytes(doc.file_size || 0) }}</span>
                    <span>•</span>
                    <span>{{ formatDate(doc.updated_at) }}</span>
                    <UBadge
                      v-if="doc.status === 'processing'"
                      color="warning"
                      variant="subtle"
                      size="sm"
                    >
                      Processing
                    </UBadge>
                    <UBadge
                      v-else-if="doc.status === 'indexed'"
                      color="success"
                      variant="subtle"
                      size="sm"
                    >
                      Indexed
                    </UBadge>
                  </div>
                  <p v-if="doc.summary" class="text-sm text-muted mt-2 line-clamp-2">
                    {{ doc.summary }}
                  </p>
                </div>

                <!-- Actions -->
                <div class="flex items-center gap-1">
                  <UTooltip text="View Document">
                    <UButton
                      icon="i-lucide-eye"
                      variant="ghost"
                      color="neutral"
                      size="sm"
                      @click.stop="navigateTo(`/documents/${doc.id}`)"
                    />
                  </UTooltip>
                  <UTooltip text="Download">
                    <UButton
                      icon="i-lucide-download"
                      variant="ghost"
                      color="neutral"
                      size="sm"
                      @click.stop="downloadDocument(doc.id)"
                    />
                  </UTooltip>
                  <UDropdownMenu
                    :items="[
                      [
                        { label: 'Add to Case', icon: 'i-lucide-folder-plus' },
                        { label: 'Add Tags', icon: 'i-lucide-tag' },
                        { label: 'Share', icon: 'i-lucide-share' }
                      ],
                      [
                        { label: 'Delete', icon: 'i-lucide-trash', color: 'error', click: () => deleteDocument(doc.id) }
                      ]
                    ]"
                  >
                    <UButton
                      icon="i-lucide-more-vertical"
                      variant="ghost"
                      color="neutral"
                      size="sm"
                      @click.stop
                    />
                  </UDropdownMenu>
                </div>
              </div>
            </div>
          </div>
        </UCard>
      </div>

      <!-- Grid View -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <UCard
          v-for="doc in filteredDocuments"
          :key="doc.id"
          class="hover:shadow-lg transition-all cursor-pointer relative"
          :class="selectedDocuments.has(doc.id) ? 'ring-2 ring-primary' : ''"
          @click="navigateTo(`/documents/${doc.id}`)"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <UCheckbox
                  :model-value="selectedDocuments.has(doc.id)"
                  @update:model-value="toggleSelect(doc.id)"
                  @click.stop
                />
                <div class="p-2 bg-primary/10 rounded-lg">
                  <UIcon
                    :name="documentTypeIcons[doc.document_type] || 'i-lucide-file'"
                    class="size-8 text-primary"
                  />
                </div>
              </div>
              <UDropdownMenu
                :items="[
                  [
                    { label: 'View', icon: 'i-lucide-eye', click: () => navigateTo(`/documents/${doc.id}`) },
                    { label: 'Download', icon: 'i-lucide-download', click: () => downloadDocument(doc.id) }
                  ],
                  [
                    { label: 'Delete', icon: 'i-lucide-trash', color: 'error', click: () => deleteDocument(doc.id) }
                  ]
                ]"
              >
                <UButton
                  icon="i-lucide-more-vertical"
                  variant="ghost"
                  color="neutral"
                  size="sm"
                  @click.stop
                />
              </UDropdownMenu>
            </div>
          </template>

          <div class="space-y-3">
            <div>
              <h3 class="font-semibold text-sm line-clamp-2 min-h-[2.5rem]">
                {{ doc.title || doc.filename }}
              </h3>
              <UBadge color="neutral" variant="subtle" size="sm" class="mt-2">
                {{ documentTypeLabels[doc.document_type] || 'Document' }}
              </UBadge>
            </div>

            <div class="text-xs text-muted space-y-1">
              <div>{{ formatBytes(doc.file_size || 0) }}</div>
              <div>{{ formatDate(doc.updated_at) }}</div>
            </div>

            <p v-if="doc.summary" class="text-xs text-muted line-clamp-3">
              {{ doc.summary }}
            </p>
          </div>
        </UCard>
      </div>

      <!-- Empty State -->
      <div v-if="!filteredDocuments.length" class="text-center py-16">
        <UIcon name="i-lucide-file-search" class="size-16 text-muted mx-auto mb-4 opacity-50" />
        <h3 class="text-xl font-semibold mb-2">No documents found</h3>
        <p class="text-muted mb-6">
          {{ searchQuery ? 'Try adjusting your search or filters' : 'Upload your first document to get started' }}
        </p>
        <UButton v-if="!searchQuery" icon="i-lucide-upload" label="Upload Document" color="primary" @click="showUploadModal = true" />
      </div>
    </div>

    <!-- Upload Modal -->
    <UModal v-model="showUploadModal">
      <UCard>
        <template #header>
          <h3 class="font-semibold text-highlighted">Upload Documents</h3>
        </template>

        <div class="space-y-4">
          <!-- Drop Zone -->
          <div
            class="border-2 border-dashed border-default rounded-lg p-8 text-center transition-colors hover:border-primary hover:bg-primary/5"
            @drop="handleDrop"
            @dragover.prevent
          >
            <UIcon name="i-lucide-upload-cloud" class="size-12 text-muted mx-auto mb-3" />
            <p class="text-sm font-medium text-highlighted mb-2">
              Drag and drop files here, or click to browse
            </p>
            <p class="text-xs text-muted mb-4">
              Supported: PDF, DOCX, TXT (max 100MB each)
            </p>
            <input
              type="file"
              multiple
              accept=".pdf,.docx,.txt"
              class="hidden"
              id="fileInput"
              @change="handleFileSelect"
            />
            <UButton
              label="Browse Files"
              color="primary"
              variant="outline"
              @click="() => document.getElementById('fileInput')?.click()"
            />
          </div>

          <!-- Selected Files -->
          <div v-if="uploadingFiles.length > 0" class="space-y-2">
            <h4 class="text-sm font-medium text-highlighted">Selected Files ({{ uploadingFiles.length }})</h4>
            <div class="space-y-2 max-h-48 overflow-y-auto">
              <div
                v-for="(file, index) in uploadingFiles"
                :key="index"
                class="flex items-center justify-between p-2 rounded-lg bg-muted/10"
              >
                <div class="flex items-center gap-2 flex-1 min-w-0">
                  <UIcon name="i-lucide-file" class="size-4 text-muted shrink-0" />
                  <span class="text-sm truncate">{{ file.name }}</span>
                  <span class="text-xs text-dimmed shrink-0">{{ formatBytes(file.size) }}</span>
                </div>
                <UButton
                  icon="i-lucide-x"
                  color="neutral"
                  variant="ghost"
                  size="xs"
                  @click="uploadingFiles.splice(index, 1)"
                />
              </div>
            </div>
          </div>

          <!-- Upload Progress -->
          <div v-if="uploadProgress > 0 && uploadProgress < 100" class="space-y-2">
            <div class="flex items-center justify-between text-sm">
              <span class="text-muted">Uploading...</span>
              <span class="font-medium text-highlighted">{{ uploadProgress }}%</span>
            </div>
            <div class="h-2 bg-muted/20 rounded-full overflow-hidden">
              <div
                class="h-full bg-primary transition-all duration-300"
                :style="{ width: `${uploadProgress}%` }"
              />
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton
              label="Cancel"
              color="neutral"
              variant="ghost"
              @click="showUploadModal = false; uploadingFiles = []"
            />
            <UButton
              label="Upload"
              icon="i-lucide-upload"
              color="primary"
              :disabled="uploadingFiles.length === 0"
              @click="uploadDocuments"
            />
          </div>
        </template>
      </UCard>
    </UModal>
  </UDashboardPanel>
</template>
