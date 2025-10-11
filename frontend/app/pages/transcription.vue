<script setup lang="ts">
import { ref, computed } from 'vue'

definePageMeta({
  layout: 'default'
})

const activeTab = ref('upload')
const selectedCase = ref('')
const selectedFiles = ref<File[]>([])
const uploadOptions = ref({
  autoCategorize: true,
  enableDiarization: true,
  autoDetectTimestamps: true,
  processSequentially: false
})

// Mock data - TODO: Replace with API
const cases = ref([
  { label: 'Acme Corp v. Global Tech Inc (Active)', value: '1' },
  { label: 'Smith v. Johnson Employment (Active)', value: '2' },
  { label: 'Patent Case - Tech Innovations (Pending)', value: '3' }
])

const recentTranscriptions = ref([
  {
    id: '1',
    title: 'Deposition - John Johnson',
    case_name: 'Acme Corp v. Global Tech Inc',
    created_at: '2024-03-10T10:30:00Z',
    duration: 3620,
    status: 'completed',
    speakers: 3,
    segments: 142
  },
  {
    id: '2',
    title: 'Client Interview - Jane Smith',
    case_name: 'Smith v. Johnson Employment',
    created_at: '2024-03-09T14:15:00Z',
    duration: 1820,
    status: 'completed',
    speakers: 2,
    segments: 87
  },
  {
    id: '3',
    title: 'Expert Testimony - Dr. Williams',
    case_name: 'Patent Case - Tech Innovations',
    created_at: '2024-03-08T09:00:00Z',
    duration: 5400,
    status: 'processing',
    speakers: 4,
    segments: 0
  }
])

const fileInputRef = ref<HTMLInputElement>()

function handleFilesSelected(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files) {
    selectedFiles.value = Array.from(target.files)
  }
}

function removeFile(index: number) {
  selectedFiles.value.splice(index, 1)
}

async function startTranscription() {
  if (!selectedCase.value || selectedFiles.value.length === 0) return

  // TODO: Implement actual upload
  console.log('Starting transcription...', {
    case: selectedCase.value,
    files: selectedFiles.value,
    options: uploadOptions.value
  })
}

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

const statusColors = {
  completed: 'success',
  processing: 'warning',
  failed: 'error',
  queued: 'info'
} as const

const stats = computed(() => ({
  total: recentTranscriptions.value.length,
  completed: recentTranscriptions.value.filter(t => t.status === 'completed').length,
  processing: recentTranscriptions.value.filter(t => t.status === 'processing').length,
  totalDuration: recentTranscriptions.value.reduce((acc, t) => acc + t.duration, 0)
}))
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Audio/Video Transcription">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #trailing>
          <UFieldGroup>
            <UButton
              icon="i-lucide-history"
              color="neutral"
              variant="ghost"
              label="History"
              @click="activeTab = 'recent'"
            />
            <UButton
              icon="i-lucide-upload"
              color="primary"
              label="New Transcription"
              @click="activeTab = 'upload'"
            />
          </UFieldGroup>
        </template>
      </UDashboardNavbar>
    </template>

    <div class="overflow-y-auto h-[calc(100vh-64px)]">
      <div class="max-w-7xl mx-auto p-6 space-y-6">
    <!-- Stats Bar with Gradients and Better Design -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <!-- Total Transcriptions -->
      <div class="bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 rounded-xl p-6 hover:shadow-lg hover:scale-102 transition-all duration-200">
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
      <div class="bg-gradient-to-br from-success/10 to-success/5 border border-success/20 rounded-xl p-6 hover:shadow-lg hover:scale-102 transition-all duration-200">
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
      <div class="bg-gradient-to-br from-warning/10 to-warning/5 border border-warning/20 rounded-xl p-6 hover:shadow-lg hover:scale-102 transition-all duration-200">
        <div class="flex items-start justify-between mb-4">
          <div class="p-3 bg-warning/10 rounded-lg">
            <UIcon name="i-lucide-loader-2" class="size-8 text-warning animate-spin" />
          </div>
          <UBadge color="warning" variant="subtle" size="sm">Active</UBadge>
        </div>
        <div>
          <p class="text-3xl font-bold text-warning mb-1">{{ stats.processing }}</p>
          <p class="text-sm font-medium text-muted">Processing</p>
        </div>
      </div>

      <!-- Total Duration -->
      <div class="bg-gradient-to-br from-info/10 to-info/5 border border-info/20 rounded-xl p-6 hover:shadow-lg hover:scale-102 transition-all duration-200">
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

    <div class="p-6">
      <UContainer>
        <!-- Upload Tab -->
        <div v-if="activeTab === 'upload'" class="max-w-4xl mx-auto space-y-6">
          <div class="text-center mb-8">
            <div class="inline-flex items-center justify-center size-20 bg-gradient-to-br from-primary to-primary/70 rounded-2xl mb-4 shadow-lg">
              <UIcon name="i-lucide-mic" class="size-10 text-white" />
            </div>
            <h2 class="text-3xl font-bold mb-2">Upload Audio/Video for Transcription</h2>
            <p class="text-lg text-muted">AI-powered transcription with speaker identification and timestamps</p>
          </div>

          <!-- Case Selection -->
          <UCard class="shadow-md hover:shadow-lg transition-shadow duration-200">
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
                v-model="selectedCase"
                :items="cases"
                placeholder="Select a case..."
                size="lg"
              />
            </UFormField>
          </UCard>

          <!-- File Upload -->
          <UCard class="shadow-md hover:shadow-lg transition-shadow duration-200">
            <template #header>
              <div class="flex items-center gap-3">
                <div class="p-2 bg-primary/10 rounded-lg">
                  <UIcon name="i-lucide-upload" class="size-5 text-primary" />
                </div>
                <h3 class="font-semibold text-lg">Upload Files</h3>
              </div>
            </template>

            <div class="space-y-4">
              <!-- Drop Zone with Gradient -->
              <div
                class="relative border-3 border-dashed border-primary/30 rounded-xl p-16 text-center bg-gradient-to-br from-primary/5 via-primary/3 to-transparent hover:border-primary hover:from-primary/10 hover:via-primary/5 transition-all duration-300 cursor-pointer group"
                @click="fileInputRef?.click()"
              >
                <div class="absolute inset-0 bg-gradient-to-br from-primary/0 to-primary/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl" />
                <div class="relative">
                  <div class="inline-flex items-center justify-center size-24 bg-gradient-to-br from-primary/20 to-primary/10 rounded-2xl mb-6 group-hover:scale-110 transition-transform duration-300">
                    <UIcon name="i-lucide-file-audio" class="size-12 text-primary" />
                  </div>
                  <h3 class="text-xl font-bold mb-3">Upload Audio/Video Files</h3>
                  <p class="text-base text-muted mb-6">Drag and drop files here or click to browse</p>
                  <UButton icon="i-lucide-upload" label="Browse Files" color="primary" size="lg" />
                  <div class="mt-6 flex flex-wrap items-center justify-center gap-2">
                    <UBadge color="primary" variant="subtle">MP3</UBadge>
                    <UBadge color="primary" variant="subtle">WAV</UBadge>
                    <UBadge color="primary" variant="subtle">M4A</UBadge>
                    <UBadge color="primary" variant="subtle">MP4</UBadge>
                    <UBadge color="primary" variant="subtle">MOV</UBadge>
                    <UBadge color="primary" variant="subtle">WebM</UBadge>
                  </div>
                  <p class="text-sm text-muted mt-4">Max 2GB per file</p>
                </div>
              </div>

              <input
                ref="fileInputRef"
                type="file"
                multiple
                accept="audio/*,video/*"
                class="hidden"
                @change="handleFilesSelected"
              />

              <!-- Selected Files -->
              <div v-if="selectedFiles.length > 0" class="space-y-3">
                <div class="flex items-center justify-between mb-3">
                  <p class="font-semibold text-lg">Selected Files ({{ selectedFiles.length }})</p>
                  <UButton
                    label="Clear All"
                    size="sm"
                    color="neutral"
                    variant="ghost"
                    icon="i-lucide-x"
                    @click="selectedFiles = []"
                  />
                </div>
                <UCard
                  v-for="(file, idx) in selectedFiles"
                  :key="idx"
                  class="border-l-4 border-primary hover:shadow-md transition-shadow duration-200"
                  :ui="{ body: 'p-4' }"
                >
                  <div class="flex items-center justify-between gap-4">
                    <div class="flex items-center gap-4 flex-1 min-w-0">
                      <div class="p-2 bg-primary/10 rounded-lg shrink-0">
                        <UIcon name="i-lucide-file-audio" class="size-6 text-primary" />
                      </div>
                      <div class="flex-1 min-w-0">
                        <p class="font-semibold truncate text-base">{{ file.name }}</p>
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

          <!-- Options -->
          <UCard class="shadow-md hover:shadow-lg transition-shadow duration-200">
            <template #header>
              <div class="flex items-center gap-3">
                <div class="p-2 bg-primary/10 rounded-lg">
                  <UIcon name="i-lucide-settings" class="size-5 text-primary" />
                </div>
                <h3 class="font-semibold text-lg">Transcription Options</h3>
              </div>
            </template>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <UCheckboxGroup class="space-y-4">
                <div class="flex items-start gap-3 p-3 rounded-lg hover:bg-primary/5 transition-colors">
                  <UCheckbox v-model="uploadOptions.autoCategorize" class="mt-1" />
                  <div>
                    <p class="text-sm font-semibold">Auto-categorize by filename</p>
                    <p class="text-xs text-muted">Automatically detect content type from file names</p>
                  </div>
                </div>
                <div class="flex items-start gap-3 p-3 rounded-lg hover:bg-primary/5 transition-colors">
                  <UCheckbox v-model="uploadOptions.enableDiarization" class="mt-1" />
                  <div>
                    <p class="text-sm font-semibold">Speaker identification</p>
                    <p class="text-xs text-muted">Detect and identify different speakers</p>
                  </div>
                </div>
              </UCheckboxGroup>

              <UCheckboxGroup class="space-y-4">
                <div class="flex items-start gap-3 p-3 rounded-lg hover:bg-primary/5 transition-colors">
                  <UCheckbox v-model="uploadOptions.autoDetectTimestamps" class="mt-1" />
                  <div>
                    <p class="text-sm font-semibold">Auto-detect timestamps</p>
                    <p class="text-xs text-muted">Identify time references in speech</p>
                  </div>
                </div>
                <div class="flex items-start gap-3 p-3 rounded-lg hover:bg-primary/5 transition-colors">
                  <UCheckbox v-model="uploadOptions.processSequentially" class="mt-1" />
                  <div>
                    <p class="text-sm font-semibold">Process sequentially</p>
                    <p class="text-xs text-muted">Slower but more reliable for large batches</p>
                  </div>
                </div>
              </UCheckboxGroup>
            </div>
          </UCard>

          <UAlert
            icon="i-lucide-lightbulb"
            color="info"
            variant="soft"
            title="Pro Tip"
            description="Name files with descriptive names like 'deposition_witness1.mp3' for automatic categorization and better organization."
            class="border-l-4 border-info"
          />

          <!-- Start Button with Gradient -->
          <div class="relative group">
            <div class="absolute -inset-1 bg-gradient-to-r from-primary to-primary/70 rounded-xl opacity-75 group-hover:opacity-100 blur transition duration-300" />
            <UButton
              label="Start Transcription"
              icon="i-lucide-sparkles"
              color="primary"
              size="xl"
              block
              :disabled="!selectedCase || selectedFiles.length === 0"
              @click="startTranscription"
              class="relative"
            >
              <template #leading>
                <UIcon name="i-lucide-sparkles" class="animate-pulse" />
              </template>
            </UButton>
          </div>
        </div>

        <!-- Recent Transcriptions Tab -->
        <div v-else-if="activeTab === 'recent'" class="space-y-6">
          <div class="flex items-center justify-between mb-8">
            <div>
              <h2 class="text-3xl font-bold mb-2">Recent Transcriptions</h2>
              <p class="text-lg text-muted">View and manage your transcription history</p>
            </div>
            <UButton
              icon="i-lucide-upload"
              label="New Transcription"
              color="primary"
              size="lg"
              @click="activeTab = 'upload'"
            />
          </div>

          <!-- Transcriptions Grid -->
          <div v-if="recentTranscriptions.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <NuxtLink
              v-for="trans in recentTranscriptions"
              :key="trans.id"
              :to="`/transcriptions/${trans.id}`"
              class="block group"
            >
              <UCard
                class="h-full shadow-md hover:shadow-xl transition-all duration-300 hover:-translate-y-1 border-l-4"
                :class="{
                  'border-success bg-gradient-to-br from-success/5 to-transparent': trans.status === 'completed',
                  'border-warning bg-gradient-to-br from-warning/5 to-transparent': trans.status === 'processing',
                  'border-error bg-gradient-to-br from-error/5 to-transparent': trans.status === 'failed',
                  'border-info bg-gradient-to-br from-info/5 to-transparent': trans.status === 'queued'
                }"
                :ui="{ body: 'space-y-4' }"
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
                        :name="trans.status === 'processing' ? 'i-lucide-loader-2' : 'i-lucide-mic'"
                        class="size-6"
                        :class="{
                          'text-success': trans.status === 'completed',
                          'text-warning animate-spin': trans.status === 'processing',
                          'text-error': trans.status === 'failed',
                          'text-info': trans.status === 'queued'
                        }"
                      />
                    </div>
                    <div class="flex-1 min-w-0">
                      <h3 class="font-bold text-lg truncate mb-1 group-hover:text-primary transition-colors">{{ trans.title }}</h3>
                      <p class="text-sm text-muted truncate">{{ trans.case_name }}</p>
                    </div>
                  </div>
                </template>

                <div class="space-y-4">
                  <div class="flex items-center justify-between">
                    <span class="text-sm font-medium text-muted">Status</span>
                    <UBadge
                      :label="trans.status"
                      :color="statusColors[trans.status]"
                      variant="soft"
                      size="md"
                      class="capitalize font-semibold"
                      :class="{'animate-pulse': trans.status === 'processing'}"
                    />
                  </div>

                  <div class="grid grid-cols-3 gap-3 p-4 bg-default/50 rounded-lg">
                    <div class="text-center">
                      <UIcon name="i-lucide-clock" class="size-4 mx-auto mb-1 text-muted" />
                      <p class="text-xs text-muted mb-1">Duration</p>
                      <p class="font-bold text-sm">{{ formatDuration(trans.duration) }}</p>
                    </div>
                    <div class="text-center">
                      <UIcon name="i-lucide-users" class="size-4 mx-auto mb-1 text-muted" />
                      <p class="text-xs text-muted mb-1">Speakers</p>
                      <p class="font-bold text-sm">{{ trans.speakers }}</p>
                    </div>
                    <div class="text-center">
                      <UIcon name="i-lucide-list" class="size-4 mx-auto mb-1 text-muted" />
                      <p class="text-xs text-muted mb-1">Segments</p>
                      <p class="font-bold text-sm">{{ trans.segments || '-' }}</p>
                    </div>
                  </div>

                  <div class="flex items-center gap-2 text-sm text-dimmed pt-2 border-t border-default">
                    <UIcon name="i-lucide-calendar" class="size-4" />
                    <span>{{ formatDate(trans.created_at) }}</span>
                  </div>
                </div>
              </UCard>
            </NuxtLink>
          </div>

          <!-- Empty State -->
          <div v-else class="text-center py-24">
            <div class="inline-flex items-center justify-center size-32 bg-gradient-to-br from-primary/20 to-primary/5 rounded-full mb-8">
              <UIcon name="i-lucide-mic" class="size-16 text-primary/50" />
            </div>
            <h3 class="text-3xl font-bold mb-4">No transcriptions yet</h3>
            <p class="text-lg text-muted mb-8 max-w-md mx-auto">
              Upload your first audio or video file to get started with AI-powered transcription and speaker identification
            </p>
            <div class="flex flex-col sm:flex-row gap-4 items-center justify-center">
              <UButton
                label="Upload First File"
                icon="i-lucide-upload"
                color="primary"
                size="xl"
                @click="activeTab = 'upload'"
              />
              <UButton
                label="Learn More"
                icon="i-lucide-help-circle"
                color="neutral"
                variant="ghost"
                size="xl"
              />
            </div>
            <div class="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl mx-auto text-left">
              <div class="p-6 bg-gradient-to-br from-primary/5 to-transparent rounded-xl border border-primary/10">
                <div class="p-3 bg-primary/10 rounded-lg w-fit mb-4">
                  <UIcon name="i-lucide-mic" class="size-6 text-primary" />
                </div>
                <h4 class="font-bold mb-2">AI Transcription</h4>
                <p class="text-sm text-muted">Advanced AI converts audio to text with high accuracy</p>
              </div>
              <div class="p-6 bg-gradient-to-br from-success/5 to-transparent rounded-xl border border-success/10">
                <div class="p-3 bg-success/10 rounded-lg w-fit mb-4">
                  <UIcon name="i-lucide-users" class="size-6 text-success" />
                </div>
                <h4 class="font-bold mb-2">Speaker ID</h4>
                <p class="text-sm text-muted">Automatically identify and label different speakers</p>
              </div>
              <div class="p-6 bg-gradient-to-br from-info/5 to-transparent rounded-xl border border-info/10">
                <div class="p-3 bg-info/10 rounded-lg w-fit mb-4">
                  <UIcon name="i-lucide-clock" class="size-6 text-info" />
                </div>
                <h4 class="font-bold mb-2">Timestamps</h4>
                <p class="text-sm text-muted">Precise timestamps for every segment and speaker</p>
              </div>
            </div>
          </div>
        </div>
      </UContainer>
    </div>
      </div>
    </div>
  </UDashboardPanel>
</template>
