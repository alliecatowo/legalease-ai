<script setup lang="ts">
const api = useApi()
const toast = useToast()

// Modal state
const showUploadDocModal = ref(false)
const showUploadAudioModal = ref(false)
const showCreateCaseModal = ref(false)

// Fetch all data in parallel for better performance
const [
  { data: casesData, refresh: refreshCases },
  { data: documentsData, refresh: refreshDocuments },
  { data: transcriptionsData, refresh: refreshTranscriptions }
] = await Promise.all([
  useAsyncData('dashboard-cases', () => api.cases.list(), {
    default: () => ({ cases: [], total: 0 })
  }),
  useAsyncData('dashboard-documents', () => api.documents.listAll(), {
    default: () => ({ documents: [], total: 0 })
  }),
  useAsyncData('dashboard-transcriptions', () => api.transcriptions.listAll(), {
    default: () => ({ transcriptions: [], total: 0 })
  })
])

// Refresh all dashboard data
async function refreshDashboard() {
  await Promise.all([
    refreshCases(),
    refreshDocuments(),
    refreshTranscriptions()
  ])
}

// Upload document modal state
const uploadingDocFiles = ref<File[] | null>(null)
const uploadDocProgress = ref(0)

async function uploadDocuments() {
  if (!uploadingDocFiles.value || uploadingDocFiles.value.length === 0) return

  // Get the first available case ID (or show error if no cases exist)
  if (!casesData.value?.cases || casesData.value.cases.length === 0) {
    if (import.meta.client) {
      toast.add({
        title: 'No Case Available',
        description: 'Please create a case first before uploading documents',
        color: 'error'
      })
    }
    return
  }

  const caseId = casesData.value.cases[0].id
  uploadDocProgress.value = 0

  const formData = new FormData()
  uploadingDocFiles.value.forEach(file => {
    formData.append('files', file)
  })

  try {
    uploadDocProgress.value = 50
    await api.documents.upload(caseId, formData)
    uploadDocProgress.value = 100

    if (import.meta.client) {
      toast.add({
        title: 'Upload Successful',
        description: `${uploadingDocFiles.value.length} document(s) uploaded successfully`,
        color: 'success'
      })
    }

    showUploadDocModal.value = false
    uploadingDocFiles.value = null
    uploadDocProgress.value = 0
    await refreshDashboard()
  } catch (error) {
    console.error('Upload failed:', error)
    uploadDocProgress.value = 0
  }
}

// Upload audio modal state
const uploadingAudioFiles = ref<File[]>([])
const selectedCaseForUpload = ref<number | null>(null)
const isUploadingAudio = ref(false)
const uploadAudioError = ref<string | null>(null)
const transcriptionOptions = ref({
  language: null as string | null,
  task: 'transcribe' as 'transcribe' | 'translate',
  enable_diarization: true,
  min_speakers: 2,
  max_speakers: 10,
  temperature: 0.0,
  initial_prompt: null as string | null
})
const fileInputRef = ref<HTMLInputElement>()

function handleAudioFilesSelected(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files) {
    uploadingAudioFiles.value = Array.from(target.files)
  }
}

function removeAudioFile(index: number) {
  uploadingAudioFiles.value.splice(index, 1)
}

async function uploadAudioTranscript() {
  if (!selectedCaseForUpload.value || uploadingAudioFiles.value.length === 0) {
    toast.add({
      title: 'Missing Information',
      description: 'Please select a case and at least one file',
      color: 'error'
    })
    return
  }

  isUploadingAudio.value = true
  uploadAudioError.value = null

  try {
    for (const file of uploadingAudioFiles.value) {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('options', JSON.stringify(transcriptionOptions.value))

      await api.transcriptions.upload(selectedCaseForUpload.value, formData)

      toast.add({
        title: 'Upload Successful',
        description: `${file.name} queued for transcription`,
        color: 'success'
      })
    }

    showUploadAudioModal.value = false
    uploadingAudioFiles.value = []
    selectedCaseForUpload.value = null
    uploadAudioError.value = null
    await refreshDashboard()
  } catch (error: any) {
    uploadAudioError.value = error.message || 'Upload failed'
    toast.add({
      title: 'Upload Failed',
      description: error.message || 'An error occurred during upload',
      color: 'error'
    })
  } finally {
    isUploadingAudio.value = false
  }
}

// Create case modal handler
async function handleCaseCreated(caseData: any) {
  await refreshDashboard()
  toast.add({
    title: 'Case Created',
    description: `Case "${caseData.name}" has been created successfully`,
    color: 'success'
  })
}

// Case options for upload modals
const caseOptions = computed(() => [
  { label: 'All Cases', value: null },
  ...(casesData.value?.cases || []).map((c: any) => ({
    label: c.name,
    value: c.id
  }))
])

// Compute stats from real data
const stats = computed(() => {
  const cases = casesData.value?.cases || []
  const documents = documentsData.value?.documents || []
  const transcriptions = transcriptionsData.value?.transcriptions || []

  // Calculate total storage from actual document sizes
  const totalStorage = documents.reduce((sum: number, doc: any) => sum + (doc.size || 0), 0)

  // Debug: Log transcription statuses to see actual values
  if (transcriptions.length > 0) {
    console.log('Transcription statuses:', transcriptions.map((t: any) => ({ id: t.id, status: t.status })))
  }

  // Count active/processing items
  const activeCases = cases.filter((c: any) => c.status === 'ACTIVE').length

  // Status values from backend are UPPERCASE (PENDING, PROCESSING, COMPLETED, FAILED)
  // The backend returns document.status.value from the Document model enum
  const processingTranscriptions = transcriptions.filter((t: any) => {
    const status = t.status?.toUpperCase()
    return status === 'PROCESSING' || status === 'PENDING'
  }).length

  const completedTranscriptions = transcriptions.filter((t: any) =>
    t.status?.toUpperCase() === 'COMPLETED'
  ).length

  return {
    total_cases: cases.length,
    active_cases: activeCases,
    total_documents: documents.length,
    total_transcriptions: transcriptions.length,
    processing_transcriptions: processingTranscriptions,
    completed_transcriptions: completedTranscriptions,
    total_storage: totalStorage
  }
})

// Recent documents (last 10)
const recentDocuments = computed(() => {
  const docs = documentsData.value?.documents || []
  return docs.slice(0, 10)
})

// Recent transcriptions (last 5)
const recentTranscriptions = computed(() => {
  const trans = transcriptionsData.value?.transcriptions || []
  return trans.slice(0, 5)
})

// Recent cases (last 5)
const recentCases = computed(() => {
  const cases = casesData.value?.cases || []
  return cases.slice(0, 5)
})

const quickActions = [[{
  label: 'Upload Document',
  icon: 'i-lucide-upload',
  click: () => { showUploadDocModal.value = true }
}, {
  label: 'New Transcription',
  icon: 'i-lucide-mic',
  click: () => { showUploadAudioModal.value = true }
}, {
  label: 'Create Case',
  icon: 'i-lucide-folder-plus',
  click: () => { showCreateCaseModal.value = true }
}]]

function formatBytes(bytes: number) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function formatDate(dateStr: string) {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  })
}

function formatDuration(seconds: number | null) {
  if (!seconds) return 'N/A'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${String(secs).padStart(2, '0')}`
}

function getStatusColor(status: string) {
  const statusMap: Record<string, string> = {
    // Document/Transcription statuses (UPPERCASE)
    'COMPLETED': 'success',
    'PROCESSING': 'primary',
    'PENDING': 'warning',
    'FAILED': 'error',
    // Legacy lowercase statuses (for backward compatibility)
    'completed': 'success',
    'processing': 'primary',
    'queued': 'warning',
    'failed': 'error',
    // Case statuses
    'ACTIVE': 'success',
    'STAGING': 'warning',
    'UNLOADED': 'neutral',
    'ARCHIVED': 'neutral'
  }
  return statusMap[status] || 'neutral'
}
</script>

<template>
  <UDashboardPanel id="home">
    <template #header>
      <UDashboardNavbar title="Dashboard">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>

        <template #right>
          <UDropdownMenu :items="quickActions">
            <UButton icon="i-lucide-plus" label="Quick Actions" />
          </UDropdownMenu>
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <div class="p-6 space-y-6">
        <!-- Welcome Section -->
        <div>
          <h1 class="text-2xl font-bold">Welcome to LegalEase</h1>
          <p class="text-muted mt-1">Your AI-powered legal document search and transcription platform</p>
        </div>

        <!-- Stats Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <UCard>
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-folder" class="size-8 text-primary" />
              <div>
                <p class="text-2xl font-bold">{{ stats?.total_cases?.toString() || '0' }}</p>
                <p class="text-sm text-muted">Total Cases</p>
                <p class="text-xs text-muted mt-1">{{ stats?.active_cases || 0 }} active</p>
              </div>
            </div>
          </UCard>

          <UCard>
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-file-text" class="size-8 text-primary" />
              <div>
                <p class="text-2xl font-bold">{{ stats?.total_documents?.toString() || '0' }}</p>
                <p class="text-sm text-muted">Documents</p>
                <p class="text-xs text-muted mt-1">across all cases</p>
              </div>
            </div>
          </UCard>

          <UCard>
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-mic" class="size-8 text-primary" />
              <div>
                <p class="text-2xl font-bold">{{ stats?.total_transcriptions?.toString() || '0' }}</p>
                <p class="text-sm text-muted">Transcriptions</p>
                <p class="text-xs text-muted mt-1">{{ stats?.completed_transcriptions || 0 }} completed, {{ stats?.processing_transcriptions || 0 }} processing</p>
              </div>
            </div>
          </UCard>

          <UCard>
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-hard-drive" class="size-8 text-primary" />
              <div>
                <p class="text-2xl font-bold">{{ formatBytes(stats?.total_storage || 0) }}</p>
                <p class="text-sm text-muted">Storage Used</p>
                <p class="text-xs text-muted mt-1">{{ stats?.total_documents || 0 }} files</p>
              </div>
            </div>
          </UCard>
        </div>

        <!-- Main Content Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- Recent Activity Column (2/3 width) -->
          <div class="lg:col-span-2 space-y-6">
            <!-- Recent Documents -->
            <UCard>
              <template #header>
                <div class="flex items-center justify-between">
                  <h3 class="font-semibold">Recent Documents</h3>
                  <UButton variant="ghost" color="neutral" size="sm" :to="'/documents'">
                    View All
                  </UButton>
                </div>
              </template>

              <div class="space-y-3">
                <div
                  v-for="doc in recentDocuments"
                  :key="doc.id"
                  class="flex items-center gap-3 p-3 rounded-lg hover:bg-elevated/50 transition-colors cursor-pointer"
                  @click="navigateTo(`/cases/${doc.case_id}/documents/${doc.id}`)"
                >
                  <UIcon name="i-lucide-file-text" class="size-5 text-muted flex-shrink-0" />
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium truncate">{{ doc.filename }}</p>
                    <div class="flex items-center gap-2 mt-1">
                      <NuxtLink
                        :to="`/cases/${doc.case_id}`"
                        class="text-xs text-primary hover:underline"
                        @click.stop
                      >
                        {{ doc.case_name || doc.case_number }}
                      </NuxtLink>
                      <span class="text-xs text-muted">•</span>
                      <span class="text-xs text-muted">{{ formatBytes(doc.size) }}</span>
                    </div>
                  </div>
                  <div class="text-right flex-shrink-0">
                    <p class="text-xs text-muted">{{ formatDate(doc.uploaded_at) }}</p>
                    <UBadge :color="getStatusColor(doc.status)" variant="subtle" size="xs" class="mt-1">
                      {{ doc.status }}
                    </UBadge>
                  </div>
                </div>

                <div v-if="!recentDocuments?.length" class="text-center py-8">
                  <UIcon name="i-lucide-file-text" class="size-12 text-muted mx-auto mb-3 opacity-50" />
                  <p class="text-sm font-medium mb-1">No documents yet</p>
                  <p class="text-xs text-muted mb-4">Upload your first document to get started</p>
                  <UButton size="sm" @click="showUploadDocModal = true">
                    Upload Document
                  </UButton>
                </div>
              </div>
            </UCard>

            <!-- Recent Transcriptions -->
            <UCard>
              <template #header>
                <div class="flex items-center justify-between">
                  <h3 class="font-semibold">Recent Transcriptions</h3>
                  <UButton variant="ghost" color="neutral" size="sm" :to="'/transcripts'">
                    View All
                  </UButton>
                </div>
              </template>

              <div class="space-y-3">
                <div
                  v-for="trans in recentTranscriptions"
                  :key="trans.id"
                  class="flex items-center gap-3 p-3 rounded-lg hover:bg-elevated/50 transition-colors cursor-pointer"
                  @click="navigateTo(`/transcripts/${trans.id}`)"
                >
                  <UIcon name="i-lucide-mic" class="size-5 text-muted flex-shrink-0" />
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium truncate">{{ trans.filename }}</p>
                    <div class="flex items-center gap-2 mt-1">
                      <NuxtLink
                        :to="`/cases/${trans.case_id}`"
                        class="text-xs text-primary hover:underline"
                        @click.stop
                      >
                        {{ trans.case_name || trans.case_number }}
                      </NuxtLink>
                      <span class="text-xs text-muted">•</span>
                      <span class="text-xs text-muted">{{ formatDuration(trans.duration) }}</span>
                      <template v-if="trans.speaker_count">
                        <span class="text-xs text-muted">•</span>
                        <span class="text-xs text-muted">{{ trans.speaker_count }} speakers</span>
                      </template>
                    </div>
                  </div>
                  <div class="text-right flex-shrink-0">
                    <p class="text-xs text-muted">{{ formatDate(trans.created_at) }}</p>
                    <UBadge :color="getStatusColor(trans.status)" variant="subtle" size="xs" class="mt-1">
                      {{ trans.status }}
                    </UBadge>
                  </div>
                </div>

                <div v-if="!recentTranscriptions?.length" class="text-center py-8">
                  <UIcon name="i-lucide-mic" class="size-12 text-muted mx-auto mb-3 opacity-50" />
                  <p class="text-sm font-medium mb-1">No transcriptions yet</p>
                  <p class="text-xs text-muted mb-4">Upload audio or video to transcribe</p>
                  <UButton size="sm" @click="showUploadAudioModal = true">
                    New Transcription
                  </UButton>
                </div>
              </div>
            </UCard>
          </div>

          <!-- Quick Actions Sidebar (1/3 width) -->
          <div class="space-y-6">
            <!-- Quick Actions Card -->
            <UCard>
              <template #header>
                <h3 class="font-semibold">Quick Actions</h3>
              </template>

              <div class="space-y-2">
                <UButton
                  block
                  color="primary"
                  icon="i-lucide-upload"
                  size="md"
                  @click="showUploadDocModal = true"
                >
                  Upload Document
                </UButton>
                <UButton
                  block
                  color="primary"
                  variant="outline"
                  icon="i-lucide-mic"
                  size="md"
                  @click="showUploadAudioModal = true"
                >
                  Upload Audio
                </UButton>
                <UButton
                  block
                  color="primary"
                  variant="outline"
                  icon="i-lucide-folder-plus"
                  size="md"
                  @click="showCreateCaseModal = true"
                >
                  Create New Case
                </UButton>
              </div>
            </UCard>

            <!-- Recent Cases -->
            <UCard>
              <template #header>
                <div class="flex items-center justify-between">
                  <h3 class="font-semibold">Recent Cases</h3>
                  <UButton variant="ghost" color="neutral" size="sm" :to="'/cases'">
                    View All
                  </UButton>
                </div>
              </template>

              <div class="space-y-2">
                <NuxtLink
                  v-for="caseItem in recentCases"
                  :key="caseItem.id"
                  :to="`/cases/${caseItem.id}`"
                  class="block p-3 rounded-lg hover:bg-elevated/50 transition-colors"
                >
                  <div class="flex items-start gap-2">
                    <UIcon name="i-lucide-folder" class="size-4 text-muted mt-0.5 flex-shrink-0" />
                    <div class="flex-1 min-w-0">
                      <p class="text-sm font-medium truncate">{{ caseItem.name }}</p>
                      <p class="text-xs text-muted truncate mt-0.5">{{ caseItem.case_number }}</p>
                      <div class="flex items-center gap-2 mt-1">
                        <UBadge :color="getStatusColor(caseItem.status)" variant="subtle" size="xs">
                          {{ caseItem.status }}
                        </UBadge>
                        <span class="text-xs text-muted">{{ caseItem.document_count || 0 }} docs</span>
                      </div>
                    </div>
                  </div>
                </NuxtLink>

                <div v-if="!recentCases?.length" class="text-center py-6">
                  <UIcon name="i-lucide-folder" class="size-10 text-muted mx-auto mb-2 opacity-50" />
                  <p class="text-xs text-muted mb-3">No cases yet</p>
                  <UButton size="xs" variant="outline" @click="showCreateCaseModal = true">
                    Create Case
                  </UButton>
                </div>
              </div>
            </UCard>

            <!-- Quick Links -->
            <UCard>
              <template #header>
                <h3 class="font-semibold">Quick Links</h3>
              </template>

              <div class="space-y-2">
                <NuxtLink
                  :to="'/search'"
                  class="flex items-center gap-3 p-2 rounded-lg hover:bg-elevated/50 transition-colors"
                >
                  <div class="p-2 bg-primary/10 rounded">
                    <UIcon name="i-lucide-search" class="size-4 text-primary" />
                  </div>
                  <div>
                    <p class="text-sm font-medium">Search Documents</p>
                    <p class="text-xs text-muted">Semantic search</p>
                  </div>
                </NuxtLink>

                <NuxtLink
                  :to="'/graph'"
                  class="flex items-center gap-3 p-2 rounded-lg hover:bg-elevated/50 transition-colors"
                >
                  <div class="p-2 bg-blue-500/10 rounded">
                    <UIcon name="i-lucide-network" class="size-4 text-blue-500" />
                  </div>
                  <div>
                    <p class="text-sm font-medium">Knowledge Graph</p>
                    <p class="text-xs text-muted">Explore entities</p>
                  </div>
                </NuxtLink>

                <NuxtLink
                  :to="'/analytics'"
                  class="flex items-center gap-3 p-2 rounded-lg hover:bg-elevated/50 transition-colors"
                >
                  <div class="p-2 bg-amber-500/10 rounded">
                    <UIcon name="i-lucide-bar-chart" class="size-4 text-amber-500" />
                  </div>
                  <div>
                    <p class="text-sm font-medium">Analytics</p>
                    <p class="text-xs text-muted">View insights</p>
                  </div>
                </NuxtLink>
              </div>
            </UCard>
          </div>
        </div>
      </div>
    </template>
  </UDashboardPanel>

  <!-- Upload Document Modal -->
  <ClientOnly>
    <UModal v-model:open="showUploadDocModal" title="Upload Documents" :ui="{ content: 'max-w-2xl' }">
      <template #body>
        <div class="space-y-4">
          <!-- File Upload Component -->
          <UFileUpload
            v-model="uploadingDocFiles"
            multiple
            accept=".pdf,.docx,.txt"
            label="Drop your documents here"
            description="PDF, DOCX, TXT (max 100MB each)"
            icon="i-lucide-upload-cloud"
            class="min-h-48"
          />

          <!-- Upload Progress -->
          <div v-if="uploadDocProgress > 0 && uploadDocProgress < 100" class="space-y-2">
            <div class="flex items-center justify-between text-sm">
              <span class="text-muted">Uploading...</span>
              <span class="font-medium text-highlighted">{{ uploadDocProgress }}%</span>
            </div>
            <div class="h-2 bg-muted/20 rounded-full overflow-hidden">
              <div
                class="h-full bg-primary transition-all duration-300"
                :style="{ width: `${uploadDocProgress}%` }"
              />
            </div>
          </div>
        </div>
      </template>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton
            label="Cancel"
            color="neutral"
            variant="ghost"
            @click="showUploadDocModal = false; uploadingDocFiles = null"
          />
          <UButton
            label="Upload"
            icon="i-lucide-upload"
            color="primary"
            :disabled="!uploadingDocFiles || uploadingDocFiles.length === 0"
            @click="uploadDocuments"
          />
        </div>
      </template>
    </UModal>
  </ClientOnly>

  <!-- Upload Audio Modal -->
  <ClientOnly>
    <UModal
      v-model:open="showUploadAudioModal"
      title="Upload Transcription"
      description="Upload audio or video files for AI transcription"
      :ui="{ content: 'max-w-5xl' }"
    >
      <template #body>
        <div class="space-y-6">
          <!-- Case Selection -->
          <UCard>
            <template #header>
              <div class="flex items-center gap-3">
                <div class="p-2 bg-primary/10 rounded-lg">
                  <UIcon name="i-lucide-folder" class="size-5 text-primary" />
                </div>
                <h3 class="font-semibold text-lg">Select Case</h3>
              </div>
            </template>

            <UFormField label="Associate with Case" name="case" required>
              <USelectMenu
                v-model="selectedCaseForUpload"
                :items="caseOptions"
                placeholder="Select a case..."
                size="lg"
                value-key="value"
              />
            </UFormField>
          </UCard>

          <!-- File Upload -->
          <UCard>
            <template #header>
              <div class="flex items-center gap-3">
                <div class="p-2 bg-primary/10 rounded-lg">
                  <UIcon name="i-lucide-file-audio" class="size-5 text-primary" />
                </div>
                <h3 class="font-semibold text-lg">Upload Files</h3>
              </div>
            </template>

            <div class="space-y-4">
              <!-- Drop Zone -->
              <div
                class="relative border-3 border-dashed border-primary/30 rounded-xl p-12 text-center bg-gradient-to-br from-primary/5 via-primary/3 to-transparent hover:border-primary hover:from-primary/10 hover:via-primary/5 transition-all duration-300 cursor-pointer group"
                @click="fileInputRef?.click()"
              >
                <div class="relative">
                  <div class="inline-flex items-center justify-center size-20 bg-gradient-to-br from-primary/20 to-primary/10 rounded-2xl mb-4 group-hover:scale-110 transition-transform duration-300">
                    <UIcon name="i-lucide-file-audio" class="size-10 text-primary" />
                  </div>
                  <h3 class="text-lg font-bold mb-2">Upload Audio/Video Files</h3>
                  <p class="text-sm text-muted mb-4">Drag and drop files here or click to browse</p>
                  <UButton icon="i-lucide-upload" label="Browse Files" color="primary" />
                  <div class="mt-4 flex flex-wrap items-center justify-center gap-2">
                    <UBadge color="primary" variant="subtle" size="sm">MP3</UBadge>
                    <UBadge color="primary" variant="subtle" size="sm">WAV</UBadge>
                    <UBadge color="primary" variant="subtle" size="sm">M4A</UBadge>
                    <UBadge color="primary" variant="subtle" size="sm">MP4</UBadge>
                    <UBadge color="primary" variant="subtle" size="sm">MOV</UBadge>
                    <UBadge color="primary" variant="subtle" size="sm">WebM</UBadge>
                  </div>
                  <p class="text-xs text-muted mt-3">Max 2GB per file</p>
                </div>
              </div>

              <input
                ref="fileInputRef"
                type="file"
                multiple
                accept=".mp3,.wav,.m4a,.aac,.flac,.ogg,.webm,.mp4,.mov,.avi,.mkv,audio/*,video/*"
                class="hidden"
                @change="handleAudioFilesSelected"
              />

              <!-- Selected Files -->
              <div v-if="uploadingAudioFiles.length > 0" class="space-y-3">
                <div class="flex items-center justify-between mb-3">
                  <p class="font-semibold">Selected Files ({{ uploadingAudioFiles.length }})</p>
                  <UButton
                    label="Clear All"
                    size="sm"
                    color="neutral"
                    variant="ghost"
                    icon="i-lucide-x"
                    @click="uploadingAudioFiles = []"
                  />
                </div>
                <UCard
                  v-for="(file, idx) in uploadingAudioFiles"
                  :key="idx"
                  class="border-l-4 border-primary"
                >
                  <div class="flex items-center justify-between gap-4">
                    <div class="flex items-center gap-3 flex-1 min-w-0">
                      <div class="p-2 bg-primary/10 rounded-lg shrink-0">
                        <UIcon name="i-lucide-file-audio" class="size-5 text-primary" />
                      </div>
                      <div class="flex-1 min-w-0">
                        <p class="font-medium truncate">{{ file.name }}</p>
                        <div class="flex items-center gap-2 mt-1">
                          <UBadge color="primary" variant="subtle" size="sm">{{ (file.size / 1024 / 1024).toFixed(2) }} MB</UBadge>
                          <UBadge color="success" variant="subtle" size="sm">Ready</UBadge>
                        </div>
                      </div>
                    </div>
                    <UButton
                      icon="i-lucide-x"
                      size="sm"
                      color="neutral"
                      variant="ghost"
                      @click="removeAudioFile(idx)"
                    />
                  </div>
                </UCard>
              </div>
            </div>
          </UCard>

          <!-- Transcription Options -->
          <TranscriptionOptions v-model="transcriptionOptions" />

          <!-- Error Alert -->
          <UAlert
            v-if="uploadAudioError"
            icon="i-lucide-alert-circle"
            color="error"
            variant="soft"
            :title="uploadAudioError"
            closable
            @close="uploadAudioError = null"
          />
        </div>
      </template>

      <template #footer>
        <div class="flex items-center justify-end gap-3">
          <UButton
            label="Cancel"
            color="neutral"
            variant="outline"
            @click="showUploadAudioModal = false"
            :disabled="isUploadingAudio"
          />
          <UButton
            label="Start Transcription"
            icon="i-lucide-sparkles"
            color="primary"
            :disabled="!selectedCaseForUpload || uploadingAudioFiles.length === 0 || isUploadingAudio"
            :loading="isUploadingAudio"
            @click="uploadAudioTranscript"
          />
        </div>
      </template>
    </UModal>
  </ClientOnly>

  <!-- Create Case Modal -->
  <ClientOnly>
    <CreateCaseModal v-model:open="showCreateCaseModal" @created="handleCaseCreated" />
  </ClientOnly>
</template>
