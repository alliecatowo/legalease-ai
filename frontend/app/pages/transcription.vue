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

const fileInputRef = ref<HTMLInputElement | null>(null)

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
          <UButtonGroup>
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
          </UButtonGroup>
        </template>
      </UDashboardNavbar>
    </template>

    <UDashboardPanelContent>
    <!-- Stats Bar -->
    <div class="bg-default p-4 mb-6">
      <div class="p-4">
        <div class="grid grid-cols-4 gap-4">
          <div class="text-center">
            <p class="text-2xl font-bold text-primary">{{ stats.total }}</p>
            <p class="text-xs text-muted">Total Transcriptions</p>
          </div>
          <div class="text-center">
            <p class="text-2xl font-bold text-success">{{ stats.completed }}</p>
            <p class="text-xs text-muted">Completed</p>
          </div>
          <div class="text-center">
            <p class="text-2xl font-bold text-warning">{{ stats.processing }}</p>
            <p class="text-xs text-muted">Processing</p>
          </div>
          <div class="text-center">
            <p class="text-2xl font-bold text-info">{{ formatDuration(stats.totalDuration) }}</p>
            <p class="text-xs text-muted">Total Duration</p>
          </div>
        </div>
      </div>
    </div>

    <div class="p-6">
      <UContainer>
        <!-- Upload Tab -->
        <div v-if="activeTab === 'upload'" class="max-w-4xl mx-auto space-y-6">
          <div class="text-center mb-8">
            <div class="inline-flex items-center justify-center size-16 bg-primary/10 rounded-full mb-4">
              <UIcon name="i-lucide-mic" class="size-8 text-primary" />
            </div>
            <h2 class="text-2xl font-bold mb-2">Upload Audio/Video for Transcription</h2>
            <p class="text-muted">AI-powered transcription with speaker identification and timestamps</p>
          </div>

          <!-- Case Selection -->
          <UCard>
            <template #header>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-folder" class="size-5 text-primary" />
                <h3 class="font-semibold">Select Case</h3>
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
          <UCard>
            <template #header>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-upload" class="size-5 text-primary" />
                <h3 class="font-semibold">Upload Files</h3>
              </div>
            </template>

            <div class="space-y-4">
              <!-- Drop Zone -->
              <div
                class="border-2 border-dashed border-default rounded-lg p-12 text-center hover:border-primary hover:bg-primary/5 transition-colors cursor-pointer"
                @click="fileInputRef?.click()"
              >
                <UIcon name="i-lucide-file-audio" class="size-16 text-muted mx-auto mb-4" />
                <h3 class="font-semibold mb-2">Upload Audio/Video Files</h3>
                <p class="text-sm text-muted mb-4">Drag and drop files here or click to browse</p>
                <UButton icon="i-lucide-upload" label="Browse Files" color="primary" />
                <p class="text-xs text-dimmed mt-4">
                  Supported: MP3, WAV, M4A, MP4, MOV, WebM • Max 2GB per file
                </p>
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
              <div v-if="selectedFiles.length > 0" class="space-y-2">
                <div class="flex items-center justify-between mb-3">
                  <p class="font-medium">Selected Files ({{ selectedFiles.length }})</p>
                  <UButton
                    label="Clear All"
                    size="xs"
                    color="neutral"
                    variant="ghost"
                    @click="selectedFiles = []"
                  />
                </div>
                <UCard
                  v-for="(file, idx) in selectedFiles"
                  :key="idx"
                  :ui="{ body: 'p-3' }"
                >
                  <div class="flex items-center justify-between gap-3">
                    <div class="flex items-center gap-3 flex-1 min-w-0">
                      <UIcon name="i-lucide-file-audio" class="size-5 text-primary shrink-0" />
                      <div class="flex-1 min-w-0">
                        <p class="font-medium truncate">{{ file.name }}</p>
                        <p class="text-xs text-muted">{{ (file.size / 1024 / 1024).toFixed(2) }} MB</p>
                      </div>
                    </div>
                    <UButton
                      icon="i-lucide-x"
                      size="xs"
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
          <UCard>
            <template #header>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-settings" class="size-5 text-primary" />
                <h3 class="font-semibold">Transcription Options</h3>
              </div>
            </template>

            <div class="grid grid-cols-2 gap-4">
              <UCheckboxGroup class="space-y-3">
                <div class="flex items-start gap-3">
                  <UCheckbox v-model="uploadOptions.autoCategorize" />
                  <div>
                    <p class="text-sm font-medium">Auto-categorize by filename</p>
                    <p class="text-xs text-muted">Automatically detect content type from file names</p>
                  </div>
                </div>
                <div class="flex items-start gap-3">
                  <UCheckbox v-model="uploadOptions.enableDiarization" />
                  <div>
                    <p class="text-sm font-medium">Speaker identification</p>
                    <p class="text-xs text-muted">Detect and identify different speakers</p>
                  </div>
                </div>
              </UCheckboxGroup>

              <UCheckboxGroup class="space-y-3">
                <div class="flex items-start gap-3">
                  <UCheckbox v-model="uploadOptions.autoDetectTimestamps" />
                  <div>
                    <p class="text-sm font-medium">Auto-detect timestamps</p>
                    <p class="text-xs text-muted">Identify time references in speech</p>
                  </div>
                </div>
                <div class="flex items-start gap-3">
                  <UCheckbox v-model="uploadOptions.processSequentially" />
                  <div>
                    <p class="text-sm font-medium">Process sequentially</p>
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
          />

          <!-- Start Button -->
          <UButton
            label="Start Transcription"
            icon="i-lucide-sparkles"
            color="primary"
            size="lg"
            block
            :disabled="!selectedCase || selectedFiles.length === 0"
            @click="startTranscription"
          >
            <template #leading>
              <UIcon name="i-lucide-sparkles" class="animate-pulse" />
            </template>
          </UButton>
        </div>

        <!-- Recent Transcriptions Tab -->
        <div v-else-if="activeTab === 'recent'" class="space-y-4">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h2 class="text-2xl font-bold">Recent Transcriptions</h2>
              <p class="text-muted">View and manage your transcription history</p>
            </div>
            <UButton
              icon="i-lucide-upload"
              label="New Transcription"
              color="primary"
              @click="activeTab = 'upload'"
            />
          </div>

          <!-- Transcriptions Grid -->
          <div v-if="recentTranscriptions.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <NuxtLink
              v-for="trans in recentTranscriptions"
              :key="trans.id"
              :to="`/transcriptions/${trans.id}`"
              class="block"
            >
              <UCard class="hover:shadow-lg transition-all hover:scale-[1.02] h-full" :ui="{ body: 'space-y-4' }">
                <template #header>
                  <div class="flex items-start gap-3">
                    <div class="p-2 bg-primary/10 rounded-lg">
                      <UIcon name="i-lucide-mic" class="size-6 text-primary" />
                    </div>
                    <div class="flex-1 min-w-0">
                      <h3 class="font-semibold truncate mb-1">{{ trans.title }}</h3>
                      <p class="text-xs text-muted truncate">{{ trans.case_name }}</p>
                    </div>
                  </div>
                </template>

                <div class="space-y-3">
                  <div class="flex items-center justify-between text-sm">
                    <span class="text-muted">Status</span>
                    <UBadge
                      :label="trans.status"
                      :color="statusColors[trans.status]"
                      variant="soft"
                      class="capitalize"
                    />
                  </div>

                  <div class="grid grid-cols-3 gap-2 text-center py-2 border-y border-default">
                    <div>
                      <p class="text-xs text-muted">Duration</p>
                      <p class="font-semibold text-sm">{{ formatDuration(trans.duration) }}</p>
                    </div>
                    <div>
                      <p class="text-xs text-muted">Speakers</p>
                      <p class="font-semibold text-sm">{{ trans.speakers }}</p>
                    </div>
                    <div>
                      <p class="text-xs text-muted">Segments</p>
                      <p class="font-semibold text-sm">{{ trans.segments }}</p>
                    </div>
                  </div>

                  <div class="text-xs text-dimmed">
                    <UIcon name="i-lucide-clock" class="size-3 inline mr-1" />
                    {{ formatDate(trans.created_at) }}
                  </div>
                </div>
              </UCard>
            </NuxtLink>
          </div>

          <!-- Empty State -->
          <div v-else class="text-center py-20">
            <UIcon name="i-lucide-mic" class="size-20 text-muted mx-auto mb-6 opacity-30" />
            <h3 class="text-2xl font-semibold mb-3">No transcriptions yet</h3>
            <p class="text-muted mb-6 max-w-md mx-auto">
              Upload your first audio or video file to get started with AI-powered transcription
            </p>
            <UButton
              label="Upload First File"
              icon="i-lucide-upload"
              color="primary"
              size="lg"
              @click="activeTab = 'upload'"
            />
          </div>
        </div>
      </UContainer>
    </div>
    </UDashboardPanelContent>
  </UDashboardPanel>
</template>
