<script setup lang="ts">
const { data: stats } = await useFetch('/api/v1/stats/dashboard')
const { data: searchStats } = await useFetch('/api/v1/stats/search', { query: { days: 30 } })

const timeRange = ref('30d')

const timeRangeOptions = [
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
  { label: 'Last 90 days', value: '90d' },
  { label: 'Last year', value: '1y' }
]

// Mock data for charts - replace with real data from backend
const searchVolumeData = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  searches: Math.floor(Math.random() * 50) + 10
}))

const documentTypeData = [
  { type: 'Contracts', count: 127, percentage: 35 },
  { type: 'Transcripts', count: 89, percentage: 25 },
  { type: 'Court Filings', count: 76, percentage: 21 },
  { type: 'Agreements', count: 68, percentage: 19 }
]

const topSearchTerms = [
  { term: 'employment termination', count: 45 },
  { term: 'medical malpractice', count: 38 },
  { term: 'contract breach', count: 32 },
  { term: 'negligence', count: 28 },
  { term: 'confidentiality clause', count: 24 }
]
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Analytics">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #trailing>
          <USelectMenu v-model="timeRange" :items="timeRangeOptions" />
        </template>
      </UDashboardNavbar>
    </template>

    <div class="overflow-y-auto h-[calc(100vh-64px)]">
      <div class="max-w-7xl mx-auto p-6 space-y-6">
      <!-- Overview Stats -->
      <UPageGrid>
        <UPageCard
          title="Total Searches"
          :description="(searchStats?.total_searches || 247).toString()"
        >
          <template #icon>
            <UIcon name="i-lucide-search" class="size-5" />
          </template>
          <template #footer>
            <div class="text-xs text-green-500">
              +23% from last period
            </div>
          </template>
        </UPageCard>

        <UPageCard
          title="Avg. Response Time"
          description="1.2s"
        >
          <template #icon>
            <UIcon name="i-lucide-zap" class="size-5" />
          </template>
          <template #footer>
            <div class="text-xs text-green-500">
              -15% faster
            </div>
          </template>
        </UPageCard>

        <UPageCard
          title="Documents Processed"
          :description="(stats?.total_documents || 360).toString()"
        >
          <template #icon>
            <UIcon name="i-lucide-file-check" class="size-5" />
          </template>
          <template #footer>
            <div class="text-xs text-muted">
              {{ stats?.documents_this_month || 18 }} this month
            </div>
          </template>
        </UPageCard>

        <UPageCard
          title="Processing Queue"
          :description="((stats?.queue_documents || 0) + (stats?.queue_transcriptions || 0) + (stats?.queue_ai || 0)).toString()"
        >
          <template #icon>
            <UIcon name="i-lucide-loader" class="size-5" />
          </template>
          <template #footer>
            <div class="text-xs text-muted">
              Across all queues
            </div>
          </template>
        </UPageCard>
      </UPageGrid>

      <!-- Search Volume Chart -->
      <UCard>
        <template #header>
          <h3 class="font-semibold">Search Volume</h3>
        </template>

        <div class="h-64 flex items-center justify-center bg-muted/10 rounded-lg">
          <div class="text-center">
            <UIcon name="i-lucide-bar-chart-3" class="size-12 text-muted mx-auto mb-2" />
            <p class="text-sm text-muted">Chart visualization coming soon</p>
          </div>
        </div>
      </UCard>

      <!-- Document Types & Top Searches -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Document Types -->
        <UCard>
          <template #header>
            <h3 class="font-semibold">Documents by Type</h3>
          </template>

          <div class="space-y-4">
            <div v-for="item in documentTypeData" :key="item.type" class="space-y-2">
              <div class="flex items-center justify-between text-sm">
                <span>{{ item.type }}</span>
                <span class="font-medium">{{ item.count }}</span>
              </div>
              <UProgress :value="item.percentage" />
            </div>
          </div>
        </UCard>

        <!-- Top Search Terms -->
        <UCard>
          <template #header>
            <h3 class="font-semibold">Top Search Terms</h3>
          </template>

          <div class="space-y-3">
            <div
              v-for="(item, index) in topSearchTerms"
              :key="item.term"
              class="flex items-center justify-between p-3 rounded-lg hover:bg-elevated/50 transition-colors"
            >
              <div class="flex items-center gap-3">
                <div class="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-semibold text-primary">
                  {{ index + 1 }}
                </div>
                <span class="font-medium">{{ item.term }}</span>
              </div>
              <UBadge variant="subtle" color="neutral">
                {{ item.count }} searches
              </UBadge>
            </div>
          </div>
        </UCard>
      </div>

      <!-- Entity Statistics -->
      <UCard>
        <template #header>
          <h3 class="font-semibold">Entity Extraction Stats</h3>
        </template>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="text-center p-4 rounded-lg bg-blue-500/10">
            <div class="text-2xl font-bold text-blue-500">{{ stats?.total_entities?.toLocaleString() || '1,247' }}</div>
            <div class="text-sm text-muted mt-1">Total Entities</div>
          </div>
          <div class="text-center p-4 rounded-lg bg-purple-500/10">
            <div class="text-2xl font-bold text-purple-500">456</div>
            <div class="text-sm text-muted mt-1">Organizations</div>
          </div>
          <div class="text-center p-4 rounded-lg bg-amber-500/10">
            <div class="text-2xl font-bold text-amber-500">{{ stats?.graph_nodes || 234 }}</div>
            <div class="text-sm text-muted mt-1">Graph Nodes</div>
          </div>
          <div class="text-center p-4 rounded-lg bg-green-500/10">
            <div class="text-2xl font-bold text-green-500">89</div>
            <div class="text-sm text-muted mt-1">Citations</div>
          </div>
        </div>
      </UCard>

      <!-- System Performance -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <UCard>
          <template #header>
            <h4 class="text-sm font-semibold">Indexing Performance</h4>
          </template>
          <div class="text-2xl font-bold">{{ stats?.indexed_chunks?.toLocaleString() || '12,453' }}</div>
          <p class="text-sm text-muted mt-1">Indexed chunks</p>
        </UCard>

        <UCard>
          <template #header>
            <h4 class="text-sm font-semibold">Storage Usage</h4>
          </template>
          <div class="text-2xl font-bold">3.2 GB</div>
          <p class="text-sm text-muted mt-1">Of 100 GB available</p>
        </UCard>

        <UCard>
          <template #header>
            <h4 class="text-sm font-semibold">API Performance</h4>
          </template>
          <div class="text-2xl font-bold">99.8%</div>
          <p class="text-sm text-muted mt-1">Uptime</p>
        </UCard>
      </div>
      </div>
    </div>
  </UDashboardPanel>
</template>
