<script setup lang="ts">
const api = useApi()

// Fetch cases to compute stats
const { data: casesData } = await useAsyncData('dashboard-cases', () => api.cases.list(), {
  default: () => ({ cases: [], total: 0 })
})

// Compute stats from cases data
const stats = computed(() => {
  const cases = casesData.value?.cases || []
  const totalDocs = cases.reduce((sum: number, c: any) => sum + (c.document_count || 0), 0)

  return {
    total_cases: cases.length,
    active_cases: cases.filter((c: any) => c.status === 'ACTIVE').length,
    total_documents: totalDocs,
    documents_this_month: totalDocs, // TODO: Filter by month
    total_transcriptions: 0, // TODO: Add transcriptions API
    processing_transcriptions: 0,
    total_storage: totalDocs * 250000, // Rough estimate: 250KB per doc
    indexed_chunks: totalDocs * 10, // Rough estimate: 10 chunks per doc
    queue_documents: 0, // TODO: Add queue API
    queue_transcriptions: 0,
    queue_ai: 0,
    total_entities: 0, // TODO: Add entities API
    graph_nodes: 0,
    search_queries_30d: 0
  }
})

// TODO: Replace with actual recent activity API
const recentActivity = ref([])


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
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  })
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
      <div class="max-w-7xl mx-auto space-y-6">
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
                <p class="text-xs text-muted mt-1">{{ stats?.documents_this_month || 0 }} this month</p>
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
                <p class="text-sm text-muted">Storage</p>
                <p class="text-xs text-muted mt-1">{{ stats?.indexed_chunks || 0 }} indexed chunks</p>
              </div>
            </div>
          </UCard>
        </div>

        <!-- Quick Links -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <UCard :to="'/search'">
            <div class="flex items-center gap-4">
              <div class="p-3 bg-primary/10 rounded-lg">
                <UIcon name="i-lucide-search" class="size-6 text-primary" />
              </div>
              <div>
                <h3 class="font-semibold">Search Documents</h3>
                <p class="text-sm text-muted">Semantic search across all cases</p>
              </div>
            </div>
          </UCard>

          <UCard :to="'/documents'">
            <div class="flex items-center gap-4">
              <div class="p-3 bg-blue-500/10 rounded-lg">
                <UIcon name="i-lucide-upload" class="size-6 text-blue-500" />
              </div>
              <div>
                <h3 class="font-semibold">Upload Documents</h3>
                <p class="text-sm text-muted">Add new legal documents</p>
              </div>
            </div>
          </UCard>

          <UCard :to="'/transcripts'">
            <div class="flex items-center gap-4">
              <div class="p-3 bg-amber-500/10 rounded-lg">
                <UIcon name="i-lucide-mic" class="size-6 text-amber-500" />
              </div>
              <div>
                <h3 class="font-semibold">Transcribe Audio</h3>
                <p class="text-sm text-muted">Convert audio/video to text</p>
              </div>
            </div>
          </UCard>
        </div>

        <!-- Recent Activity -->
        <UCard>
          <template #header>
            <div class="flex items-center justify-between">
              <h3 class="font-semibold">Recent Activity</h3>
              <UButton variant="ghost" color="neutral" size="sm" :to="'/activity'">
                View All
              </UButton>
            </div>
          </template>

          <div class="space-y-3">
            <div
              v-for="activity in recentActivity?.slice(0, 5)"
              :key="activity.id"
              class="flex items-start gap-3 p-3 rounded-lg hover:bg-elevated/50 transition-colors"
            >
              <div class="flex-shrink-0 mt-0.5">
                <UIcon
                  :name="activity.icon || 'i-lucide-activity'"
                  class="size-5 text-muted"
                />
              </div>
              <div class="flex-1">
                <p class="text-sm">{{ activity.description }}</p>
                <p class="text-xs text-muted mt-1">{{ formatDate(activity.created_at) }}</p>
              </div>
            </div>

            <div v-if="!recentActivity?.length" class="text-center py-8">
              <UIcon name="i-lucide-activity" class="size-12 text-muted mx-auto mb-3 opacity-50" />
              <p class="text-sm font-medium mb-1">No recent activity</p>
              <p class="text-xs text-muted">Start by uploading documents or creating cases</p>
            </div>
          </div>
        </UCard>

        <!-- System Status -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <UCard>
            <template #header>
              <h3 class="font-semibold">Processing Queue</h3>
            </template>

            <div class="space-y-2 text-sm">
              <div class="flex items-center justify-between">
                <span class="text-muted">Documents</span>
                <span class="font-medium">{{ stats?.queue_documents || 0 }} pending</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted">Transcriptions</span>
                <span class="font-medium">{{ stats?.queue_transcriptions || 0 }} pending</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted">AI Tasks</span>
                <span class="font-medium">{{ stats?.queue_ai || 0 }} pending</span>
              </div>
            </div>
          </UCard>

          <UCard>
            <template #header>
              <h3 class="font-semibold">Quick Stats</h3>
            </template>

            <div class="space-y-2 text-sm">
              <div class="flex items-center justify-between">
                <span class="text-muted">Entities Extracted</span>
                <span class="font-medium">{{ stats?.total_entities?.toLocaleString() || 0 }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted">Knowledge Graph Nodes</span>
                <span class="font-medium">{{ stats?.graph_nodes || 0 }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted">Search Queries (30d)</span>
                <span class="font-medium">{{ stats?.search_queries_30d || 0 }}</span>
              </div>
            </div>
          </UCard>
        </div>
      </div>
    </template>
  </UDashboardPanel>
</template>
