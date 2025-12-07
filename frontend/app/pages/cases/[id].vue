<script setup lang="ts">
import { ref, computed, watchEffect } from 'vue'

definePageMeta({
  layout: 'default'
})

const route = useRoute()
const router = useRouter()
const toast = useToast()

// Use Firestore composables
const { getCase, updateCase, archiveCase: archiveCaseAction } = useCases()
const { documents: documentsData, listDocuments, uploadDocument, deleteDocument: removeDocument } = useDocuments()

// Get case ID from route
const caseId = computed(() => route.params.id as string)

// State
const loading = ref(true)
const error = ref<string | null>(null)
const showEditModal = ref(false)
const showAddDocumentModal = ref(false)
const showUploadTranscriptionModal = ref(false)
const showArchiveConfirm = ref(false)
const uploadingFiles = ref<File[] | null>(null)
const uploadProgress = ref(0)
const caseData = ref<any>(null)

// Fetch case data
async function fetchCaseData() {
  loading.value = true
  error.value = null
  try {
    caseData.value = await getCase(caseId.value)
    if (!caseData.value) {
      error.value = 'Case not found'
    }
  } catch (err: any) {
    error.value = err?.message || 'Failed to load case'
  } finally {
    loading.value = false
  }
}

async function refreshCase() {
  await fetchCaseData()
}

// Fetch documents for this case
async function refreshDocuments() {
  await listDocuments({ caseId: caseId.value })
}

// Initialize data
await fetchCaseData()
await refreshDocuments()

// Watch for route changes
watch(caseId, async () => {
  await fetchCaseData()
  await refreshDocuments()
})

// Transform case data (Firestore uses camelCase)
const case_ = computed(() => {
  if (!caseData.value) return null
  const c = caseData.value

  // Handle Firestore Timestamps
  const createdAt = c.createdAt?.toDate?.() || c.createdAt
  const updatedAt = c.updatedAt?.toDate?.() || c.updatedAt

  return {
    id: c.id,
    name: c.name,
    caseNumber: c.caseNumber,
    type: c.matterType || 'General',
    status: c.status || 'active',
    client: c.client || 'Unknown Client',
    opposingParty: 'N/A',
    court: 'N/A',
    jurisdiction: 'N/A',
    openedDate: createdAt?.toISOString?.() || new Date().toISOString(),
    lastActivity: updatedAt?.toISOString?.() || new Date().toISOString(),
    description: c.matterType ? `${c.matterType} case for ${c.client}` : `Legal case for ${c.client}`,
    notes: '',
    tags: c.matterType ? [c.matterType.toLowerCase()] : [],
    documentCount: documents.value.length
  }
})

// Transform documents (filter out audio/video files - they should be transcriptions)
const documents = computed(() => {
  if (!documentsData.value?.length) return []

  return documentsData.value
    .filter((d) => {
      const mimeType = d.mimeType || ''
      return !mimeType.startsWith('audio/') && !mimeType.startsWith('video/')
    })
    .map((d) => {
      const uploadedAt = d.createdAt?.toDate?.() || d.createdAt
      return {
        id: d.id!,
        filename: d.filename,
        title: d.title || d.filename,
        type: d.documentType || 'general',
        size: d.fileSize || 0,
        uploadedAt: uploadedAt?.toISOString?.() || new Date().toISOString(),
        status: d.status || 'indexed',
        summary: d.summary,
        pageCount: d.pageCount
      }
    })
})

// Transform transcriptions (audio/video files only)
const transcriptions = computed(() => {
  if (!documentsData.value?.length) return []

  return documentsData.value
    .filter((d) => {
      const mimeType = d.mimeType || ''
      return mimeType.startsWith('audio/') || mimeType.startsWith('video/')
    })
    .map((d) => {
      const uploadedAt = d.createdAt?.toDate?.() || d.createdAt
      return {
        id: d.id!,
        filename: d.filename,
        size: d.fileSize || 0,
        uploadedAt: uploadedAt?.toISOString?.() || new Date().toISOString(),
        status: d.status || 'pending',
        duration: undefined,
        speakerCount: undefined
      }
    })
})

// Status configuration
const statusColors: Record<string, string> = {
  active: 'success',
  staging: 'warning',
  pending: 'warning',
  unloaded: 'neutral',
  closed: 'neutral',
  archived: 'neutral'
}

const statusLabels: Record<string, string> = {
  active: 'Active',
  staging: 'Staging',
  pending: 'Pending',
  unloaded: 'Closed',
  closed: 'Closed',
  archived: 'Archived'
}

// Document type configuration
const documentTypeIcons: Record<string, string> = {
  contract: 'i-lucide-file-text',
  agreement: 'i-lucide-handshake',
  transcript: 'i-lucide-mic',
  court_filing: 'i-lucide-gavel',
  brief: 'i-lucide-file-pen',
  motion: 'i-lucide-file-check',
  correspondence: 'i-lucide-mail',
  general: 'i-lucide-file'
}

const documentTypeLabels: Record<string, string> = {
  contract: 'Contract',
  agreement: 'Agreement',
  transcript: 'Transcript',
  court_filing: 'Court Filing',
  brief: 'Brief',
  motion: 'Motion',
  correspondence: 'Correspondence',
  general: 'Document'
}

// Stats computation
const stats = computed(() => {
  if (!case_.value) return { documents: 0, recentDocs: 0, totalSize: 0, transcriptions: 0 }

  const now = new Date()
  const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)

  const recentDocs = documents.value.filter(d =>
    new Date(d.uploadedAt) >= thirtyDaysAgo
  ).length

  const totalSize = documents.value.reduce((acc, d) => acc + (d.size || 0), 0)

  return {
    documents: documents.value.length,
    recentDocs,
    totalSize,
    transcriptions: transcriptions.value.length
  }
})

// Activity timeline (mock data for now - can be enhanced with real API)
const activityTimeline = computed(() => {
  const activities = []

  // Add case creation
  if (case_.value?.openedDate) {
    activities.push({
      id: 'created',
      type: 'case_created',
      title: 'Case Opened',
      description: `Case ${case_.value.caseNumber} was created`,
      date: getRelativeTime(case_.value.openedDate),
      icon: 'i-lucide-folder-plus',
      _timestamp: case_.value.openedDate
    })
  }

  // Add document uploads
  documents.value.slice(0, 5).forEach((doc, idx) => {
    activities.push({
      id: `doc-${doc.id}`,
      type: 'document_uploaded',
      title: 'Document Uploaded',
      description: doc.title,
      date: getRelativeTime(doc.uploadedAt),
      icon: 'i-lucide-file-plus',
      _timestamp: doc.uploadedAt
    })
  })

  // Sort by timestamp descending, then remove temporary timestamp field
  return activities
    .sort((a, b) => new Date(b._timestamp).getTime() - new Date(a._timestamp).getTime())
    .slice(0, 10)
    .map(({ _timestamp, ...rest }) => rest)
})

// Actions
async function handleLoadCase() {
  try {
    await updateCase(caseId.value, { status: 'active' })
    toast.add({ title: 'Success', description: 'Case loaded successfully', color: 'success' })
    await refreshCase()
  } catch (err) {
    toast.add({ title: 'Error', description: 'Failed to load case', color: 'error' })
  }
}

async function handleUnloadCase() {
  try {
    await updateCase(caseId.value, { status: 'unloaded' })
    toast.add({ title: 'Success', description: 'Case unloaded successfully', color: 'success' })
    await refreshCase()
  } catch (err) {
    toast.add({ title: 'Error', description: 'Failed to unload case', color: 'error' })
  }
}

async function handleArchiveCase() {
  try {
    await archiveCaseAction(caseId.value)
    toast.add({ title: 'Success', description: 'Case archived successfully', color: 'success' })
    showArchiveConfirm.value = false
    router.push('/cases')
  } catch (err) {
    toast.add({ title: 'Error', description: 'Failed to archive case', color: 'error' })
  }
}

async function handleUploadDocuments() {
  if (!uploadingFiles.value?.length) return

  const files = uploadingFiles.value
  const total = files.length
  uploadProgress.value = 0

  // Track progress per file for aggregate progress
  const fileProgress = new Map<string, number>()
  files.forEach((_, i) => fileProgress.set(`${i}`, 0))

  const updateTotalProgress = () => {
    const sum = Array.from(fileProgress.values()).reduce((a, b) => a + b, 0)
    uploadProgress.value = Math.round(sum / total)
  }

  try {
    // Upload files in parallel (up to 5 concurrent uploads)
    const CONCURRENCY = 5
    const results: Promise<void>[] = []
    let fileIndex = 0

    const uploadNext = async (): Promise<void> => {
      if (fileIndex >= files.length) return

      const currentIndex = fileIndex++
      const file = files[currentIndex]

      try {
        await uploadDocument(caseId.value, file, {
          onProgress: (p) => {
            fileProgress.set(`${currentIndex}`, p.progress)
            updateTotalProgress()
          }
        })
        fileProgress.set(`${currentIndex}`, 100)
        updateTotalProgress()
      } catch (err) {
        // Continue with other uploads even if one fails
        console.error(`Failed to upload ${file.name}:`, err)
        throw err
      }

      // Start next upload if more files remain
      if (fileIndex < files.length) {
        await uploadNext()
      }
    }

    // Start initial batch of concurrent uploads
    const initialBatch = Math.min(CONCURRENCY, files.length)
    for (let i = 0; i < initialBatch; i++) {
      results.push(uploadNext())
    }

    await Promise.all(results)

    toast.add({
      title: 'Success',
      description: `${total} document(s) uploaded successfully`,
      color: 'success'
    })

    uploadingFiles.value = null
    uploadProgress.value = 0
    showAddDocumentModal.value = false
    await refreshDocuments()
  } catch (err) {
    toast.add({ title: 'Error', description: 'Failed to upload documents', color: 'error' })
    uploadProgress.value = 0
  }
}

async function handleDeleteDocument(docId: string) {
  if (!confirm('Are you sure you want to delete this document?')) return

  try {
    await removeDocument(docId)
    toast.add({ title: 'Success', description: 'Document deleted successfully', color: 'success' })
    await refreshDocuments()
  } catch (err) {
    toast.add({ title: 'Error', description: 'Failed to delete document', color: 'error' })
  }
}

// Utility functions
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diffInSeconds < 60) return 'just now'
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} days ago`

  return formatDate(dateStr)
}

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: 'warning',
    processing: 'info',
    completed: 'success',
    indexed: 'success',
    failed: 'error'
  }
  return colors[status] || 'neutral'
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar :title="case_?.name || 'Loading...'">
        <template #leading>
          <UButton
            icon="i-lucide-arrow-left"
            color="neutral"
            variant="ghost"
            @click="router.push('/cases')"
          />
        </template>
        <template #trailing>
          <div class="flex items-center gap-2">
            <UButton
              v-if="case_?.status === 'staging'"
              label="Load Case"
              icon="i-lucide-play"
              color="success"
              variant="soft"
              @click="handleLoadCase"
            />
            <UButton
              v-if="case_?.status === 'active'"
              label="Unload Case"
              icon="i-lucide-pause"
              color="warning"
              variant="soft"
              @click="handleUnloadCase"
            />
            <UButton
              label="Add Document"
              icon="i-lucide-file-plus"
              color="primary"
              @click="showAddDocumentModal = true"
            />
            <UDropdownMenu
              :items="[
                [
                  { label: 'Edit Case', icon: 'i-lucide-edit', click: () => showEditModal = true },
                  { label: 'Export Documents', icon: 'i-lucide-download' }
                ],
                [
                  { label: 'Archive Case', icon: 'i-lucide-archive', color: 'warning', click: () => showArchiveConfirm = true }
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

    <template #body>
      <div class="max-w-7xl mx-auto space-y-6">
        <!-- Loading State -->
        <div v-if="loading" class="flex items-center justify-center py-20">
          <UIcon name="i-lucide-loader-circle" class="size-12 text-primary animate-spin" />
        </div>

        <!-- Error State -->
        <div v-else-if="error || !case_" class="text-center py-20">
          <UIcon name="i-lucide-alert-circle" class="size-16 text-error mx-auto mb-4 opacity-50" />
          <h3 class="text-xl font-semibold mb-2">
            Error Loading Case
          </h3>
          <p class="text-muted mb-6">
            {{ error || 'Case not found' }}
          </p>
          <UButton
            label="Back to Cases"
            icon="i-lucide-arrow-left"
            color="primary"
            @click="router.push('/cases')"
          />
        </div>

        <!-- Case Content -->
        <template v-else-if="case_">
          <!-- Hero Section -->
          <div class="bg-gradient-to-br from-primary/10 via-secondary/5 to-transparent rounded-xl p-8 border border-default">
            <div class="flex items-start justify-between gap-6 flex-wrap">
              <div class="flex items-start gap-4 flex-1 min-w-0">
                <div class="p-4 bg-primary/20 rounded-xl">
                  <UIcon name="i-lucide-briefcase" class="size-10 text-primary" />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-3 flex-wrap mb-2">
                    <h1 class="text-3xl font-bold text-highlighted">
                      {{ case_.name }}
                    </h1>
                    <UBadge
                      :label="statusLabels[case_.status]"
                      :color="statusColors[case_.status]"
                      variant="soft"
                      size="lg"
                      class="capitalize"
                    />
                  </div>
                  <div class="flex items-center gap-4 text-muted mb-3 flex-wrap">
                    <div class="flex items-center gap-2">
                      <UIcon name="i-lucide-hash" class="size-4" />
                      <span class="font-mono">{{ case_.caseNumber }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <UIcon name="i-lucide-tag" class="size-4" />
                      <span>{{ case_.type }}</span>
                    </div>
                  </div>
                  <p class="text-base text-muted max-w-3xl">
                    {{ case_.description }}
                  </p>
                </div>
              </div>

              <!-- Quick Actions -->
              <div class="flex flex-col gap-2 min-w-[160px]">
                <UButton
                  label="Search Documents"
                  icon="i-lucide-search"
                  color="neutral"
                  variant="outline"
                  block
                  @click="router.push(`/search?case_id=${case_.id}`)"
                />
                <UButton
                  label="View Analytics"
                  icon="i-lucide-bar-chart"
                  color="neutral"
                  variant="outline"
                  block
                  to="/analytics"
                />
              </div>
            </div>
          </div>

          <!-- Stats Cards -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <UCard :ui="{ body: 'space-y-2' }">
              <div class="flex items-center justify-between">
                <UIcon name="i-lucide-files" class="size-8 text-primary" />
                <UBadge
                  :label="String(stats.documents)"
                  size="lg"
                  variant="soft"
                  color="primary"
                />
              </div>
              <div>
                <p class="text-sm text-muted">
                  Total Documents
                </p>
                <p class="text-2xl font-bold">
                  {{ stats.documents }}
                </p>
              </div>
            </UCard>

            <UCard :ui="{ body: 'space-y-2' }">
              <div class="flex items-center justify-between">
                <UIcon name="i-lucide-clock" class="size-8 text-info" />
                <UBadge
                  :label="`+${stats.recentDocs}`"
                  size="lg"
                  variant="soft"
                  color="info"
                />
              </div>
              <div>
                <p class="text-sm text-muted">
                  Added Last 30 Days
                </p>
                <p class="text-2xl font-bold">
                  {{ stats.recentDocs }}
                </p>
              </div>
            </UCard>

            <UCard :ui="{ body: 'space-y-2' }">
              <div class="flex items-center justify-between">
                <UIcon name="i-lucide-hard-drive" class="size-8 text-success" />
              </div>
              <div>
                <p class="text-sm text-muted">
                  Total Storage
                </p>
                <p class="text-2xl font-bold">
                  {{ formatBytes(stats.totalSize) }}
                </p>
              </div>
            </UCard>

            <UCard :ui="{ body: 'space-y-2' }">
              <div class="flex items-center justify-between">
                <UIcon name="i-lucide-calendar" class="size-8 text-warning" />
              </div>
              <div>
                <p class="text-sm text-muted">
                  Last Activity
                </p>
                <p class="text-lg font-bold">
                  {{ getRelativeTime(case_.lastActivity) }}
                </p>
              </div>
            </UCard>
          </div>

          <!-- Main Content Grid -->
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Left Column - Case Details & Documents -->
            <div class="lg:col-span-2 space-y-6">
              <!-- Case Information -->
              <UCard>
                <template #header>
                  <div class="flex items-center justify-between">
                    <h2 class="text-xl font-semibold text-highlighted flex items-center gap-2">
                      <UIcon name="i-lucide-info" class="size-5" />
                      Case Information
                    </h2>
                    <UButton
                      icon="i-lucide-edit"
                      color="neutral"
                      variant="ghost"
                      size="sm"
                      @click="showEditModal = true"
                    />
                  </div>
                </template>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div class="space-y-1">
                    <div class="flex items-center gap-2 text-sm text-muted">
                      <UIcon name="i-lucide-user" class="size-4" />
                      <span>Client</span>
                    </div>
                    <p class="font-medium text-highlighted">
                      {{ case_.client }}
                    </p>
                  </div>

                  <div class="space-y-1">
                    <div class="flex items-center gap-2 text-sm text-muted">
                      <UIcon name="i-lucide-users" class="size-4" />
                      <span>Opposing Party</span>
                    </div>
                    <p class="font-medium text-highlighted">
                      {{ case_.opposingParty }}
                    </p>
                  </div>

                  <div class="space-y-1">
                    <div class="flex items-center gap-2 text-sm text-muted">
                      <UIcon name="i-lucide-landmark" class="size-4" />
                      <span>Court</span>
                    </div>
                    <p class="font-medium text-highlighted">
                      {{ case_.court }}
                    </p>
                  </div>

                  <div class="space-y-1">
                    <div class="flex items-center gap-2 text-sm text-muted">
                      <UIcon name="i-lucide-map-pin" class="size-4" />
                      <span>Jurisdiction</span>
                    </div>
                    <p class="font-medium text-highlighted">
                      {{ case_.jurisdiction }}
                    </p>
                  </div>

                  <div class="space-y-1">
                    <div class="flex items-center gap-2 text-sm text-muted">
                      <UIcon name="i-lucide-calendar-plus" class="size-4" />
                      <span>Opened Date</span>
                    </div>
                    <p class="font-medium text-highlighted">
                      {{ formatDate(case_.openedDate) }}
                    </p>
                  </div>

                  <div class="space-y-1">
                    <div class="flex items-center gap-2 text-sm text-muted">
                      <UIcon name="i-lucide-activity" class="size-4" />
                      <span>Last Updated</span>
                    </div>
                    <p class="font-medium text-highlighted">
                      {{ formatDate(case_.lastActivity) }}
                    </p>
                  </div>
                </div>

                <div v-if="case_.notes" class="mt-6 pt-6 border-t border-default">
                  <div class="flex items-center gap-2 text-sm text-muted mb-2">
                    <UIcon name="i-lucide-sticky-note" class="size-4" />
                    <span>Notes</span>
                  </div>
                  <p class="text-muted whitespace-pre-wrap">
                    {{ case_.notes }}
                  </p>
                </div>
              </UCard>

              <!-- Documents Section -->
              <UCard>
                <template #header>
                  <div class="flex items-center justify-between">
                    <h2 class="text-xl font-semibold text-highlighted flex items-center gap-2">
                      <UIcon name="i-lucide-folder" class="size-5" />
                      Documents
                      <UBadge :label="String(documents.length)" variant="soft" color="primary" />
                    </h2>
                    <UButton
                      label="Add Document"
                      icon="i-lucide-plus"
                      color="primary"
                      size="sm"
                      @click="showAddDocumentModal = true"
                    />
                  </div>
                </template>

                <!-- Documents List -->
                <div v-if="documents.length > 0" class="space-y-3">
                  <div
                    v-for="doc in documents"
                    :key="doc.id"
                    class="flex items-start gap-3 p-3 rounded-lg hover:bg-muted/5 transition-colors cursor-pointer group"
                    @click="router.push(`/documents/${doc.id}`)"
                  >
                    <div class="p-2 bg-primary/10 rounded-lg">
                      <UIcon
                        :name="documentTypeIcons[doc.type] || 'i-lucide-file'"
                        class="size-5 text-primary"
                      />
                    </div>

                    <div class="flex-1 min-w-0">
                      <div class="flex items-start justify-between gap-2">
                        <div class="flex-1 min-w-0">
                          <h3 class="font-medium text-highlighted truncate">
                            {{ doc.title }}
                          </h3>
                          <div class="flex items-center gap-3 mt-1 text-sm text-muted flex-wrap">
                            <UBadge
                              :label="documentTypeLabels[doc.type] || 'Document'"
                              variant="outline"
                              size="xs"
                            />
                            <span>{{ formatBytes(doc.size) }}</span>
                            <span>•</span>
                            <span>{{ formatDate(doc.uploadedAt) }}</span>
                            <UBadge
                              v-if="doc.status === 'processing'"
                              label="Processing"
                              color="warning"
                              variant="soft"
                              size="xs"
                            />
                            <UBadge
                              v-else-if="doc.status === 'indexed'"
                              label="Indexed"
                              color="success"
                              variant="soft"
                              size="xs"
                            />
                          </div>
                          <p v-if="doc.summary" class="text-sm text-muted mt-1 line-clamp-2">
                            {{ doc.summary }}
                          </p>
                        </div>

                        <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <UTooltip text="View Document">
                            <UButton
                              icon="i-lucide-eye"
                              variant="ghost"
                              color="neutral"
                              size="xs"
                              @click.stop="router.push(`/documents/${doc.id}`)"
                            />
                          </UTooltip>
                          <UDropdownMenu
                            :items="[
                              [
                                { label: 'Download', icon: 'i-lucide-download' },
                                { label: 'Share', icon: 'i-lucide-share' }
                              ],
                              [
                                { label: 'Delete', icon: 'i-lucide-trash', color: 'error', click: () => handleDeleteDocument(doc.id) }
                              ]
                            ]"
                          >
                            <UButton
                              icon="i-lucide-more-vertical"
                              variant="ghost"
                              color="neutral"
                              size="xs"
                              @click.stop
                            />
                          </UDropdownMenu>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Empty State -->
                <div v-else class="text-center py-12">
                  <UIcon name="i-lucide-folder-open" class="size-12 text-muted mx-auto mb-4 opacity-30" />
                  <h3 class="text-lg font-semibold mb-2">
                    No documents yet
                  </h3>
                  <p class="text-sm text-muted mb-4">
                    Upload documents to get started
                  </p>
                  <UButton
                    label="Add Document"
                    icon="i-lucide-plus"
                    color="primary"
                    size="sm"
                    @click="showAddDocumentModal = true"
                  />
                </div>
              </UCard>

              <!-- Transcriptions Section -->
              <UCard>
                <template #header>
                  <div class="flex items-center justify-between">
                    <h2 class="text-xl font-semibold text-highlighted flex items-center gap-2">
                      <UIcon name="i-lucide-mic" class="size-5" />
                      Transcriptions
                      <UBadge :label="String(transcriptions.length)" variant="soft" color="primary" />
                    </h2>
                    <UButton
                      label="Upload Audio"
                      icon="i-lucide-plus"
                      color="primary"
                      size="sm"
                      @click="showUploadTranscriptionModal = true"
                    />
                  </div>
                </template>

                <div v-if="transcriptions.length > 0" class="space-y-3">
                  <div
                    v-for="trans in transcriptions"
                    :key="trans.id"
                    class="flex items-start gap-3 p-3 rounded-lg hover:bg-muted/5 transition-colors cursor-pointer group"
                    @click="router.push(`/transcripts/${trans.id}`)"
                  >
                    <div class="p-2 bg-primary/10 rounded-lg">
                      <UIcon name="i-lucide-mic" class="size-5 text-primary" />
                    </div>

                    <div class="flex-1 min-w-0">
                      <div class="flex items-start justify-between gap-2">
                        <div class="flex-1 min-w-0">
                          <h3 class="font-medium text-highlighted truncate">
                            {{ trans.filename }}
                          </h3>
                          <div class="flex items-center gap-3 mt-1 text-sm text-muted flex-wrap">
                            <span>{{ formatBytes(trans.size) }}</span>
                            <span>•</span>
                            <span>{{ formatDate(trans.uploadedAt) }}</span>
                            <template v-if="trans.duration">
                              <span>•</span>
                              <span>{{ formatDuration(trans.duration) }}</span>
                            </template>
                            <UBadge
                              :label="trans.status"
                              :color="getStatusColor(trans.status)"
                              variant="soft"
                              size="xs"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-else class="text-center py-12">
                  <UIcon name="i-lucide-mic" class="size-12 text-muted mx-auto mb-4 opacity-30" />
                  <h3 class="text-lg font-semibold mb-2">
                    No transcriptions yet
                  </h3>
                  <p class="text-sm text-muted mb-4">
                    Upload audio or video files to transcribe
                  </p>
                  <UButton
                    label="Upload Audio"
                    icon="i-lucide-plus"
                    color="primary"
                    size="sm"
                    @click="showUploadTranscriptionModal = true"
                  />
                </div>
              </UCard>
            </div>

            <!-- Right Column - Activity Timeline -->
            <div class="space-y-6">
              <!-- Activity Timeline -->
              <UCard>
                <template #header>
                  <h2 class="text-xl font-semibold text-highlighted flex items-center gap-2">
                    <UIcon name="i-lucide-history" class="size-5" />
                    Recent Activity
                  </h2>
                </template>

                <UTimeline
                  v-if="activityTimeline.length > 0"
                  :items="activityTimeline"
                  size="xs"
                  color="primary"
                />

                <div v-else class="text-center py-8">
                  <UIcon name="i-lucide-activity" class="size-10 text-muted mx-auto mb-3 opacity-30" />
                  <p class="text-sm text-muted">
                    No recent activity
                  </p>
                </div>
              </UCard>

              <!-- Quick Links -->
              <UCard>
                <template #header>
                  <h2 class="text-xl font-semibold text-highlighted flex items-center gap-2">
                    <UIcon name="i-lucide-zap" class="size-5" />
                    Quick Actions
                  </h2>
                </template>

                <div class="space-y-2">
                  <UButton
                    label="Search in Case"
                    icon="i-lucide-search"
                    color="neutral"
                    variant="outline"
                    block
                    @click="router.push(`/search?case_id=${case_.id}`)"
                  />
                  <UButton
                    label="Upload Documents"
                    icon="i-lucide-upload"
                    color="neutral"
                    variant="outline"
                    block
                    @click="showAddDocumentModal = true"
                  />
                  <UButton
                    label="Generate Report"
                    icon="i-lucide-file-text"
                    color="neutral"
                    variant="outline"
                    block
                  />
                  <UButton
                    label="View Timeline"
                    icon="i-lucide-clock"
                    color="neutral"
                    variant="outline"
                    block
                  />
                </div>
              </UCard>

              <!-- Case Tags (if any) -->
              <UCard v-if="case_.tags && case_.tags.length > 0">
                <template #header>
                  <h2 class="text-xl font-semibold text-highlighted flex items-center gap-2">
                    <UIcon name="i-lucide-tags" class="size-5" />
                    Tags
                  </h2>
                </template>

                <div class="flex flex-wrap gap-2">
                  <UBadge
                    v-for="tag in case_.tags"
                    :key="tag"
                    :label="tag"
                    variant="soft"
                    color="primary"
                  />
                </div>
              </UCard>
            </div>
          </div>
        </template>
      </div>
    </template>
  </UDashboardPanel>

  <!-- Add Document Modal -->
  <ClientOnly>
    <UModal
      v-model:open="showAddDocumentModal"
      title="Add Documents to Case"
      :ui="{ content: 'max-w-2xl' }"
    >
      <template #body>
        <div class="space-y-4">
          <!-- File Upload Component -->
          <UFileUpload
            v-model="uploadingFiles"
            multiple
            accept=".pdf,.docx,.txt"
            label="Drop your documents here"
            description="PDF, DOCX, TXT (max 100MB each)"
            icon="i-lucide-upload-cloud"
            class="min-h-48"
          />

          <!-- Upload Progress -->
          <div v-if="uploadProgress > 0 && uploadProgress < 100" class="space-y-2">
            <div class="flex items-center justify-between text-sm">
              <span class="text-muted">Uploading...</span>
              <span class="font-medium text-highlighted">{{ uploadProgress }}%</span>
            </div>
            <UProgress :model-value="uploadProgress" color="primary" />
          </div>
        </div>
      </template>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton
            label="Cancel"
            color="neutral"
            variant="ghost"
            @click="showAddDocumentModal = false; uploadingFiles = null; uploadProgress = 0"
          />
          <UButton
            label="Upload"
            icon="i-lucide-upload"
            color="primary"
            :disabled="!uploadingFiles || uploadingFiles.length === 0 || uploadProgress > 0"
            @click="handleUploadDocuments"
          />
        </div>
      </template>
    </UModal>
  </ClientOnly>

  <!-- Upload Transcription Modal -->
  <ClientOnly>
    <UploadTranscriptionModal
      v-model:open="showUploadTranscriptionModal"
      :case-id="caseId"
      @uploaded="refreshDocuments"
    />
  </ClientOnly>

  <!-- Archive Confirmation Modal -->
  <ClientOnly>
    <UModal
      v-model:open="showArchiveConfirm"
      title="Archive Case"
      icon="i-lucide-archive"
    >
      <template #body>
        <div class="space-y-4">
          <p class="text-muted">
            Are you sure you want to archive this case? The case and all its documents will be moved to the archive.
          </p>

          <UAlert
            color="warning"
            variant="soft"
            icon="i-lucide-alert-triangle"
            title="This action can be reversed"
            description="You can unarchive this case later from the archived cases section."
          />
        </div>
      </template>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton
            label="Cancel"
            color="neutral"
            variant="ghost"
            @click="showArchiveConfirm = false"
          />
          <UButton
            label="Archive Case"
            icon="i-lucide-archive"
            color="warning"
            @click="handleArchiveCase"
          />
        </div>
      </template>
    </UModal>
  </ClientOnly>
</template>
