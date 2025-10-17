<script setup lang="ts">
const api = useApi()

// Fetch all data in parallel for better performance
const [
  { data: casesData },
  { data: documentsData },
  { data: transcriptionsData }
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

// Compute stats from real data
const stats = computed(() => {
  const cases = casesData.value?.cases || []
  const documents = documentsData.value?.documents || []
  const transcriptions = transcriptionsData.value?.transcriptions || []

  // Calculate total storage from actual document sizes
  const totalStorage = documents.reduce((sum: number, doc: any) => sum + (doc.size || 0), 0)

  // Count active/processing items
  const activeCases = cases.filter((c: any) => c.status === 'ACTIVE').length
  const processingTranscriptions = transcriptions.filter((t: any) =>
    t.status === 'processing' || t.status === 'queued'
  ).length

  return {
    total_cases: cases.length,
    active_cases: activeCases,
    total_documents: documents.length,
    total_transcriptions: transcriptions.length,
    processing_transcriptions: processingTranscriptions,
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
  to: '/documents'
}, {
  label: 'New Transcription',
  icon: 'i-lucide-mic',
  to: '/transcripts'
}, {
  label: 'Create Case',
  icon: 'i-lucide-folder-plus',
  to: '/cases'
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
    'completed': 'success',
    'processing': 'primary',
    'queued': 'warning',
    'failed': 'error',
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
                <p class="text-xs text-muted mt-1">{{ stats?.processing_transcriptions || 0 }} processing</p>
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
                  <UButton :to="'/documents'" size="sm">
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
                  <UButton :to="'/transcripts'" size="sm">
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
                  :to="'/documents'"
                  block
                  color="primary"
                  icon="i-lucide-upload"
                  size="md"
                >
                  Upload Document
                </UButton>
                <UButton
                  :to="'/transcripts'"
                  block
                  color="primary"
                  variant="outline"
                  icon="i-lucide-mic"
                  size="md"
                >
                  Upload Audio
                </UButton>
                <UButton
                  :to="'/cases'"
                  block
                  color="primary"
                  variant="outline"
                  icon="i-lucide-folder-plus"
                  size="md"
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
                  <UButton :to="'/cases'" size="xs" variant="outline">
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
</template>
