<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

definePageMeta({
  layout: 'default'
})

const api = useApi()
const toast = useToast()

// Initialize shared data cache
const { cases, transcriptions } = useSharedData()

// Load data on mount
await cases.get()
await transcriptions.get()

// View mode
const viewMode = ref<'grid' | 'list'>('grid')

// Upload modal state
const showUploadModal = ref(false)
const uploadingFiles = ref<File[]>([])
const selectedCaseForUpload = ref<number | null>(null)
const isUploading = ref(false)
const uploadError = ref<string | null>(null)
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

// Filters
const searchQuery = ref('')
const selectedStatus = ref<string | null>(null)
const selectedCase = ref<number | null>(null)
const selectedDateRange = ref<string>('all')
const sortBy = ref<string>('recent')

// Case options for filter dropdown
const caseOptions = computed(() => [
  { label: 'All Cases', value: null },
  ...(cases.data.value?.cases || []).map((c: any) => ({
    label: c.name,
    value: c.id
  }))
])

// Loading state from shared cache
const loadingTranscriptions = computed(() => transcriptions.loading.value)

// Transcriptions data from shared cache
const transcriptionsData = computed(() => transcriptions.data.value?.transcriptions || [])

// Refresh function that uses shared cache
const refreshTranscriptions = async () => {
  await transcriptions.refresh()
}

// Filtered and sorted transcriptions
const filteredTranscriptions = computed(() => {
  let result = transcriptionsData.value || []

  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter((t: any) =>
      t.title?.toLowerCase().includes(query) ||
      t.case_name?.toLowerCase().includes(query) ||
      t.filename?.toLowerCase().includes(query)
    )
  }

  // Status filter
  if (selectedStatus.value) {
    result = result.filter((t: any) => t.status === selectedStatus.value)
  }

  // Case filter
  if (selectedCase.value) {
    result = result.filter((t: any) => t.case_id === selectedCase.value)
  }

  // Date range filter
  if (selectedDateRange.value !== 'all') {
    const now = new Date()
    const cutoffDate = new Date()

    if (selectedDateRange.value === '7days') {
      cutoffDate.setDate(now.getDate() - 7)
    } else if (selectedDateRange.value === '30days') {
      cutoffDate.setDate(now.getDate() - 30)
    } else if (selectedDateRange.value === '90days') {
      cutoffDate.setDate(now.getDate() - 90)
    }

    result = result.filter((t: any) => new Date(t.created_at) >= cutoffDate)
  }

  // Sorting
  if (sortBy.value === 'recent') {
    result.sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  } else if (sortBy.value === 'oldest') {
    result.sort((a: any, b: any) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
  } else if (sortBy.value === 'duration-long') {
    result.sort((a: any, b: any) => (b.duration || 0) - (a.duration || 0))
  } else if (sortBy.value === 'duration-short') {
    result.sort((a: any, b: any) => (a.duration || 0) - (b.duration || 0))
  } else if (sortBy.value === 'name-az') {
    result.sort((a: any, b: any) => (a.title || a.filename || '').localeCompare(b.title || b.filename || ''))
  } else if (sortBy.value === 'name-za') {
    result.sort((a: any, b: any) => (b.title || b.filename || '').localeCompare(a.title || a.filename || ''))
  }

  return result
})

// Statistics
const stats = computed(() => {
  const data = transcriptionsData.value || []
  return {
    total: data.length || 0,
    completed: data.filter((t: any) => t.status === 'completed').length || 0,
    processing: data.filter((t: any) => t.status === 'processing' || t.status === 'queued').length || 0,
    totalDuration: data.reduce((acc: number, t: any) => acc + (t.duration || 0), 0) || 0
  }
})

// Status colors
const statusColors = {
  completed: 'success',
  processing: 'warning',
  failed: 'error',
  queued: 'info'
} as const

// Real-time polling for processing transcriptions
const processingTranscriptions = computed(() => {
  const data = transcriptionsData.value || []
  return data.filter((t: any) => t.status === 'processing' || t.status === 'queued')
})

let pollInterval: NodeJS.Timeout | null = null

onMounted(() => {
  if (processingTranscriptions.value.length > 0) {
    pollInterval = setInterval(refreshTranscriptions, 5000)
  }
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
})

watch(processingTranscriptions, (current) => {
  if (current.length === 0 && pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  } else if (current.length > 0 && !pollInterval) {
    pollInterval = setInterval(refreshTranscriptions, 5000)
  }
})

// Utility functions
function formatDuration(seconds: number) {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m ${s}s`
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Delete transcription
async function deleteTranscription(id: number) {
  try {
    await api.transcriptions.delete(id)
    toast.add({
      title: 'Success',
      description: 'Transcription deleted successfully',
      color: 'success'
    })
    await refreshTranscriptions()
  } catch (error: any) {
    toast.add({
      title: 'Error',
      description: error.message || 'Failed to delete transcription',
      color: 'error'
    })
  }
}

// Download transcription
async function downloadTranscription(id: number, format: 'docx' | 'srt' | 'vtt' | 'txt' | 'json') {
  try {
    const response = await api.transcriptions.download(id, format)
    // Handle download
    toast.add({
      title: 'Success',
      description: `Downloading transcription as ${format.toUpperCase()}`,
      color: 'success'
    })
  } catch (error: any) {
    toast.add({
      title: 'Error',
      description: error.message || 'Failed to download transcription',
      color: 'error'
    })
  }
}

// Upload modal functions
function handleFilesSelected(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files) {
    uploadingFiles.value = Array.from(target.files)
  }
}

function removeFile(index: number) {
  uploadingFiles.value.splice(index, 1)
}

async function uploadTranscript() {
  if (!selectedCaseForUpload.value || uploadingFiles.value.length === 0) {
    toast.add({
      title: 'Missing Information',
      description: 'Please select a case and at least one file',
      color: 'error'
    })
    return
  }

  isUploading.value = true
  uploadError.value = null

  try {
    // Upload files one by one with transcription options
    for (const file of uploadingFiles.value) {
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

    // Reset and refresh
    showUploadModal.value = false
    uploadingFiles.value = []
    selectedCaseForUpload.value = null
    uploadError.value = null
    await refreshTranscriptions()
  } catch (error: any) {
    uploadError.value = error.message || 'Upload failed'
    toast.add({
      title: 'Upload Failed',
      description: error.message || 'An error occurred during upload',
      color: 'error'
    })
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Transcriptions">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #trailing>
          <UFieldGroup>
            <UButton
              icon="i-lucide-refresh-cw"
              color="neutral"
              variant="ghost"
              label="Refresh"
              :loading="loadingTranscriptions"
              @click="refreshTranscriptions"
            />
            <UButton
              icon="i-lucide-upload"
              color="primary"
              label="New Transcription"
              @click="showUploadModal = true"
            />
          </UFieldGroup>
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <div class="max-w-7xl mx-auto space-y-6">

        <!-- Stats Bar -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <!-- Total -->
          <div class="bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 rounded-xl p-6 hover:shadow-lg transition-all duration-200">
            <div class="flex items-start justify-between mb-4">
              <div class="p-3 bg-primary/10 rounded-lg">
                <UIcon name="i-lucide-file-audio" class="size-8 text-primary" />
              </div>
              <UBadge color="primary" variant="subtle" size="sm">All</UBadge>
            </div>
            <div>
              <p class="text-3xl font-bold text-primary mb-1">{{ stats.total }}</p>
              <p class="text-sm font-medium text-muted">Total Transcriptions</p>
            </div>
          </div>

          <!-- Completed -->
          <div class="bg-gradient-to-br from-success/10 to-success/5 border border-success/20 rounded-xl p-6 hover:shadow-lg transition-all duration-200">
            <div class="flex items-start justify-between mb-4">
              <div class="p-3 bg-success/10 rounded-lg">
                <UIcon name="i-lucide-check-circle-2" class="size-8 text-success" />
              </div>
              <UBadge color="success" variant="subtle" size="sm">Ready</UBadge>
            </div>
            <div>
              <p class="text-3xl font-bold text-success mb-1">{{ stats.completed }}</p>
              <p class="text-sm font-medium text-muted">Completed</p>
            </div>
          </div>

          <!-- Processing -->
          <div class="bg-gradient-to-br from-warning/10 to-warning/5 border border-warning/20 rounded-xl p-6 hover:shadow-lg transition-all duration-200">
            <div class="flex items-start justify-between mb-4">
              <div class="p-3 bg-warning/10 rounded-lg">
                <UIcon name="i-lucide-loader-2" class="size-8 text-warning" :class="{'animate-spin': stats.processing > 0}" />
              </div>
              <UBadge color="warning" variant="subtle" size="sm">Active</UBadge>
            </div>
            <div>
              <p class="text-3xl font-bold text-warning mb-1">{{ stats.processing }}</p>
              <p class="text-sm font-medium text-muted">Processing</p>
            </div>
          </div>

          <!-- Total Duration -->
          <div class="bg-gradient-to-br from-info/10 to-info/5 border border-info/20 rounded-xl p-6 hover:shadow-lg transition-all duration-200">
            <div class="flex items-start justify-between mb-4">
              <div class="p-3 bg-info/10 rounded-lg">
                <UIcon name="i-lucide-clock" class="size-8 text-info" />
              </div>
              <UBadge color="info" variant="subtle" size="sm">Total</UBadge>
            </div>
            <div>
              <p class="text-3xl font-bold text-info mb-1">{{ formatDuration(stats.totalDuration) }}</p>
              <p class="text-sm font-medium text-muted">Total Duration</p>
            </div>
          </div>
        </div>

        <!-- Filters Bar -->
        <UCard>
          <div class="space-y-4">
            <div class="flex flex-col md:flex-row gap-4">
              <!-- Search -->
              <div class="flex-1">
                <UInput
                  v-model="searchQuery"
                  icon="i-lucide-search"
                  placeholder="Search transcriptions..."
                  size="lg"
                />
              </div>

              <!-- View Mode Toggle -->
              <UFieldGroup>
                <UButton
                  :icon="viewMode === 'grid' ? 'i-lucide-grid-3x3' : 'i-lucide-layout-grid'"
                  :color="viewMode === 'grid' ? 'primary' : 'neutral'"
                  :variant="viewMode === 'grid' ? 'soft' : 'ghost'"
                  @click="viewMode = 'grid'"
                />
                <UButton
                  :icon="viewMode === 'list' ? 'i-lucide-list' : 'i-lucide-list'"
                  :color="viewMode === 'list' ? 'primary' : 'neutral'"
                  :variant="viewMode === 'list' ? 'soft' : 'ghost'"
                  @click="viewMode = 'list'"
                />
              </UFieldGroup>
            </div>

            <div class="flex flex-col md:flex-row gap-4">
              <!-- Status Filter -->
              <USelectMenu
                v-model="selectedStatus"
                :items="[
                  { label: 'All Status', value: null },
                  { label: 'Completed', value: 'completed' },
                  { label: 'Processing', value: 'processing' },
                  { label: 'Queued', value: 'queued' },
                  { label: 'Failed', value: 'failed' }
                ]"
                placeholder="Filter by status"
                value-key="value"
                class="w-full md:w-48"
              />

              <!-- Case Filter -->
              <USelectMenu
                v-model="selectedCase"
                :items="caseOptions"
                placeholder="Filter by case"
                value-key="value"
                class="w-full md:w-64"
              />

              <!-- Date Range -->
              <USelectMenu
                v-model="selectedDateRange"
                :items="[
                  { label: 'All Time', value: 'all' },
                  { label: 'Last 7 Days', value: '7days' },
                  { label: 'Last 30 Days', value: '30days' },
                  { label: 'Last 90 Days', value: '90days' }
                ]"
                placeholder="Date range"
                value-key="value"
                class="w-full md:w-48"
              />

              <!-- Sort -->
              <USelectMenu
                v-model="sortBy"
                :items="[
                  { label: 'Most Recent', value: 'recent' },
                  { label: 'Oldest First', value: 'oldest' },
                  { label: 'Longest Duration', value: 'duration-long' },
                  { label: 'Shortest Duration', value: 'duration-short' },
                  { label: 'Name (A-Z)', value: 'name-az' },
                  { label: 'Name (Z-A)', value: 'name-za' }
                ]"
                placeholder="Sort by"
                value-key="value"
                class="w-full md:w-48"
              />
            </div>

            <!-- Active Filters -->
            <div v-if="searchQuery || selectedStatus || selectedCase || selectedDateRange !== 'all'" class="flex flex-wrap gap-2">
              <UBadge v-if="searchQuery" color="primary" variant="soft">
                Search: {{ searchQuery }}
                <UButton icon="i-lucide-x" size="xs" color="primary" variant="ghost" @click="searchQuery = ''" />
              </UBadge>
              <UBadge v-if="selectedStatus" color="primary" variant="soft">
                Status: {{ selectedStatus }}
                <UButton icon="i-lucide-x" size="xs" color="primary" variant="ghost" @click="selectedStatus = null" />
              </UBadge>
              <UBadge v-if="selectedCase" color="primary" variant="soft">
                Case: {{ caseOptions.find(c => c.value === selectedCase)?.label }}
                <UButton icon="i-lucide-x" size="xs" color="primary" variant="ghost" @click="selectedCase = null" />
              </UBadge>
              <UBadge v-if="selectedDateRange !== 'all'" color="primary" variant="soft">
                {{ selectedDateRange === '7days' ? 'Last 7 Days' : selectedDateRange === '30days' ? 'Last 30 Days' : 'Last 90 Days' }}
                <UButton icon="i-lucide-x" size="xs" color="primary" variant="ghost" @click="selectedDateRange = 'all'" />
              </UBadge>
            </div>

            <!-- Results Count -->
            <div class="text-sm text-muted">
              Showing {{ filteredTranscriptions.length }} of {{ stats.total }} transcriptions
            </div>
          </div>
        </UCard>

        <!-- Grid View -->
        <div v-if="viewMode === 'grid' && filteredTranscriptions.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <UCard
            v-for="trans in filteredTranscriptions"
            :key="trans.id"
            class="h-full shadow-md hover:shadow-xl transition-all duration-300 border-l-4 group cursor-pointer"
            :class="{
              'border-success bg-gradient-to-br from-success/5 to-transparent': trans.status === 'completed',
              'border-warning bg-gradient-to-br from-warning/5 to-transparent': trans.status === 'processing',
              'border-error bg-gradient-to-br from-error/5 to-transparent': trans.status === 'failed',
              'border-info bg-gradient-to-br from-info/5 to-transparent': trans.status === 'queued'
            }"
            @click="$router.push(`/transcripts/${trans.id}`)"
          >
            <template #header>
              <div class="flex items-start gap-3">
                <div
                  class="p-3 rounded-xl"
                  :class="{
                    'bg-gradient-to-br from-success/20 to-success/10': trans.status === 'completed',
                    'bg-gradient-to-br from-warning/20 to-warning/10': trans.status === 'processing',
                    'bg-gradient-to-br from-error/20 to-error/10': trans.status === 'failed',
                    'bg-gradient-to-br from-info/20 to-info/10': trans.status === 'queued'
                  }"
                >
                  <UIcon
                    :name="trans.status === 'processing' || trans.status === 'queued' ? 'i-lucide-loader-2' : 'i-lucide-mic'"
                    class="size-6"
                    :class="{
                      'text-success': trans.status === 'completed',
                      'text-warning animate-spin': trans.status === 'processing' || trans.status === 'queued',
                      'text-error': trans.status === 'failed',
                      'text-info': trans.status === 'queued'
                    }"
                  />
                </div>
                <div class="flex-1 min-w-0">
                  <h3 class="font-bold text-lg truncate mb-1 group-hover:text-primary transition-colors">
                    {{ trans.title || trans.filename }}
                  </h3>
                  <UBadge color="neutral" variant="soft" size="sm">
                    {{ trans.case_name }}
                  </UBadge>
                </div>
                <UTooltip text="Delete Transcription">
                  <UButton
                    icon="i-lucide-trash-2"
                    color="error"
                    variant="ghost"
                    size="sm"
                    @click.stop="deleteTranscription(trans.id)"
                  />
                </UTooltip>
              </div>
            </template>

              <div class="space-y-4">
                <div class="flex items-center justify-between">
                  <span class="text-sm font-medium text-muted">Status</span>
                  <UBadge
                    :label="trans.status"
                    :color="statusColors[trans.status as keyof typeof statusColors]"
                    variant="soft"
                    size="md"
                    class="capitalize font-semibold"
                    :class="{'animate-pulse': trans.status === 'processing' || trans.status === 'queued'}"
                  />
                </div>

                <div class="grid grid-cols-3 gap-3 p-4 bg-default/50 rounded-lg">
                  <div class="text-center">
                    <UIcon name="i-lucide-clock" class="size-4 mx-auto mb-1 text-muted" />
                    <p class="text-xs text-muted mb-1">Duration</p>
                    <p class="font-bold text-sm">{{ formatDuration(trans.duration || 0) }}</p>
                  </div>
                  <div class="text-center">
                    <UIcon name="i-lucide-users" class="size-4 mx-auto mb-1 text-muted" />
                    <p class="text-xs text-muted mb-1">Speakers</p>
                    <p class="font-bold text-sm">{{ trans.speaker_count || 0 }}</p>
                  </div>
                  <div class="text-center">
                    <UIcon name="i-lucide-list" class="size-4 mx-auto mb-1 text-muted" />
                    <p class="text-xs text-muted mb-1">Segments</p>
                    <p class="font-bold text-sm">{{ trans.segment_count || 0 }}</p>
                  </div>
                </div>

                <div class="flex items-center gap-2 text-sm text-dimmed pt-2 border-t border-default">
                  <UIcon name="i-lucide-calendar" class="size-4" />
                  <span>{{ formatDate(trans.created_at) }}</span>
                </div>
              </div>
            </UCard>
        </div>

        <!-- List View -->
        <div v-if="viewMode === 'list' && filteredTranscriptions.length > 0" class="space-y-2">
          <UCard
            v-for="trans in filteredTranscriptions"
            :key="trans.id"
            class="hover:shadow-md transition-shadow duration-200 cursor-pointer"
            @click="$router.push(`/transcripts/${trans.id}`)"
          >
            <div class="flex items-center gap-4">
              <div
                class="p-2 rounded-lg"
                :class="{
                  'bg-success/10': trans.status === 'completed',
                  'bg-warning/10': trans.status === 'processing',
                  'bg-error/10': trans.status === 'failed',
                  'bg-info/10': trans.status === 'queued'
                }"
              >
                <UIcon
                  :name="trans.status === 'processing' || trans.status === 'queued' ? 'i-lucide-loader-2' : 'i-lucide-mic'"
                  class="size-5"
                  :class="{
                    'text-success': trans.status === 'completed',
                    'text-warning animate-spin': trans.status === 'processing' || trans.status === 'queued',
                    'text-error': trans.status === 'failed',
                    'text-info': trans.status === 'queued'
                  }"
                />
              </div>

              <div class="flex-1 min-w-0">
                <h3 class="font-semibold truncate">{{ trans.title || trans.filename }}</h3>
                <div class="flex items-center gap-2 text-sm text-muted">
                  <span>{{ trans.case_name }}</span>
                  <span>•</span>
                  <span>{{ formatDuration(trans.duration || 0) }}</span>
                  <span>•</span>
                  <span>{{ trans.speaker_count || 0 }} speakers</span>
                  <span>•</span>
                  <span>{{ trans.segment_count || 0 }} segments</span>
                </div>
              </div>

              <UBadge
                :label="trans.status"
                :color="statusColors[trans.status as keyof typeof statusColors]"
                variant="soft"
                class="capitalize"
                :class="{'animate-pulse': trans.status === 'processing' || trans.status === 'queued'}"
              />

              <span class="text-sm text-muted">{{ formatDate(trans.created_at) }}</span>

              <UTooltip text="Delete Transcription">
                <UButton
                  icon="i-lucide-trash-2"
                  color="error"
                  variant="ghost"
                  size="sm"
                  @click.stop="deleteTranscription(trans.id)"
                />
              </UTooltip>
            </div>
          </UCard>
        </div>

        <!-- Empty State -->
        <div v-if="filteredTranscriptions.length === 0 && !loadingTranscriptions" class="text-center py-24">
          <div class="inline-flex items-center justify-center size-32 bg-gradient-to-br from-primary/20 to-primary/5 rounded-full mb-8">
            <UIcon name="i-lucide-mic" class="size-16 text-primary/50" />
          </div>
          <h3 class="text-3xl font-bold mb-4">
            {{ searchQuery || selectedStatus || selectedCase ? 'No transcriptions found' : 'No transcriptions yet' }}
          </h3>
          <p class="text-lg text-muted mb-8 max-w-md mx-auto">
            {{ searchQuery || selectedStatus || selectedCase
              ? 'Try adjusting your filters to see more results'
              : 'Upload your first audio or video file to get started with AI-powered transcription'
            }}
          </p>
          <UButton
            v-if="!searchQuery && !selectedStatus && !selectedCase"
            label="Upload First File"
            icon="i-lucide-upload"
            color="primary"
            size="xl"
            @click="showUploadModal = true"
          />
          <UButton
            v-else
            label="Clear Filters"
            icon="i-lucide-x"
            color="neutral"
            size="xl"
            @click="searchQuery = ''; selectedStatus = null; selectedCase = null; selectedDateRange = 'all'"
          />
        </div>

        <!-- Loading State -->
        <div v-if="loadingTranscriptions" class="text-center py-24">
          <UIcon name="i-lucide-loader-2" class="size-16 text-primary animate-spin mb-4" />
          <p class="text-lg text-muted">Loading transcriptions...</p>
        </div>
      </div>
    </template>
  </UDashboardPanel>

  <!-- Upload Modal -->
  <UModal
    v-model:open="showUploadModal"
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
                @change="handleFilesSelected"
              />

              <!-- Selected Files -->
              <div v-if="uploadingFiles.length > 0" class="space-y-3">
                <div class="flex items-center justify-between mb-3">
                  <p class="font-semibold">Selected Files ({{ uploadingFiles.length }})</p>
                  <UButton
                    label="Clear All"
                    size="sm"
                    color="neutral"
                    variant="ghost"
                    icon="i-lucide-x"
                    @click="uploadingFiles = []"
                  />
                </div>
                <UCard
                  v-for="(file, idx) in uploadingFiles"
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
                      @click="removeFile(idx)"
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
            v-if="uploadError"
            icon="i-lucide-alert-circle"
            color="error"
            variant="soft"
            :title="uploadError"
            closable
            @close="uploadError = null"
          />
        </div>
      </template>

      <template #footer>
        <div class="flex items-center justify-end gap-3">
          <UButton
            label="Cancel"
            color="neutral"
            variant="outline"
            @click="showUploadModal = false"
            :disabled="isUploading"
          />
          <UButton
            label="Start Transcription"
            icon="i-lucide-sparkles"
            color="primary"
            :disabled="!selectedCaseForUpload || uploadingFiles.length === 0 || isUploading"
            :loading="isUploading"
            @click="uploadTranscript"
          />
        </div>
      </template>
  </UModal>
</template>
