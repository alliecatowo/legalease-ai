<script setup lang="ts">
import { ref, computed } from 'vue'

definePageMeta({
  layout: 'default'
})

const showCreateModal = ref(false)
const viewMode = ref<'grid' | 'list'>('grid')
const searchQuery = ref('')
const selectedStatus = ref('all')
const selectedType = ref('all')

// Mock cases data - TODO: Replace with API call
const cases = ref([
  {
    id: '1',
    name: 'Acme Corp v. Global Tech Inc',
    caseNumber: '2024-CV-12345',
    type: 'Civil Litigation',
    status: 'active',
    court: 'Superior Court of California',
    jurisdiction: 'California',
    openedDate: '2024-01-15',
    lastActivity: '2024-03-10',
    parties: ['Acme Corporation', 'Global Tech Inc'],
    documents: 47,
    deadlines: 3,
    description: 'Breach of contract dispute involving software licensing agreements',
    tags: ['contract', 'software', 'licensing'],
    progress: 65
  },
  {
    id: '2',
    name: 'Smith v. Johnson Employment Dispute',
    caseNumber: '2024-EMP-5678',
    type: 'Employment',
    status: 'active',
    court: 'Federal District Court',
    jurisdiction: 'Federal',
    openedDate: '2024-02-01',
    lastActivity: '2024-03-12',
    parties: ['John Smith', 'ABC Corporation'],
    documents: 23,
    deadlines: 1,
    description: 'Wrongful termination and discrimination claim',
    tags: ['employment', 'discrimination'],
    progress: 40
  },
  {
    id: '3',
    name: 'Patent Infringement - Tech Innovations LLC',
    caseNumber: '2024-PAT-9012',
    type: 'Patent',
    status: 'pending',
    court: 'US District Court',
    jurisdiction: 'Federal',
    openedDate: '2023-11-20',
    lastActivity: '2024-03-08',
    parties: ['Tech Innovations LLC', 'MegaCorp Inc'],
    documents: 89,
    deadlines: 5,
    description: 'Patent infringement case involving mobile technology patents',
    tags: ['patent', 'technology', 'intellectual property'],
    progress: 80
  },
  {
    id: '4',
    name: 'Estate of Williams - Probate',
    caseNumber: '2024-PRO-3456',
    type: 'Estate',
    status: 'closed',
    court: 'Probate Court',
    jurisdiction: 'New York',
    openedDate: '2023-08-10',
    lastActivity: '2024-02-15',
    closedDate: '2024-02-15',
    parties: ['Estate of Robert Williams', 'Multiple Heirs'],
    documents: 34,
    deadlines: 0,
    description: 'Estate distribution and will contest matter',
    tags: ['probate', 'estate', 'will'],
    progress: 100
  }
])

const statusOptions = [
  { label: 'All Status', value: 'all' },
  { label: 'Active', value: 'active' },
  { label: 'Pending', value: 'pending' },
  { label: 'Closed', value: 'closed' }
]

const typeOptions = [
  { label: 'All Types', value: 'all' },
  { label: 'Civil Litigation', value: 'Civil Litigation' },
  { label: 'Employment', value: 'Employment' },
  { label: 'Patent', value: 'Patent' },
  { label: 'Corporate', value: 'Corporate' },
  { label: 'Real Estate', value: 'Real Estate' }
]

const filteredCases = computed(() => {
  return cases.value.filter(c => {
    const matchesSearch = !searchQuery.value ||
      c.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      c.caseNumber.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesStatus = selectedStatus.value === 'all' || c.status === selectedStatus.value
    const matchesType = selectedType.value === 'all' || c.type === selectedType.value
    return matchesSearch && matchesStatus && matchesType
  })
})

const stats = computed(() => ({
  total: cases.value.length,
  active: cases.value.filter(c => c.status === 'active').length,
  pending: cases.value.filter(c => c.status === 'pending').length,
  closed: cases.value.filter(c => c.status === 'closed').length
}))

const statusColors: Record<string, string> = {
  active: 'success',
  pending: 'warning',
  closed: 'neutral'
}

function onCaseCreated(caseData: any) {
  console.log('Case created:', caseData)
  // TODO: Add case to list and navigate to it
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Cases">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #trailing>
          <UButton
            label="New Case"
            icon="i-lucide-plus"
            color="primary"
            @click="showCreateModal = true"
          />
        </template>
      </UDashboardNavbar>
    </template>

    <UDashboardPanelContent>
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
      <UCard :ui="{ body: 'space-y-2' }">
        <div class="flex items-center justify-between">
          <UIcon name="i-lucide-folder" class="size-8 text-primary" />
          <UBadge :label="String(stats.total)" size="lg" variant="soft" color="primary" />
        </div>
        <div>
          <p class="text-sm text-muted">Total Cases</p>
          <p class="text-2xl font-bold">{{ stats.total }}</p>
        </div>
      </UCard>

      <UCard :ui="{ body: 'space-y-2' }">
        <div class="flex items-center justify-between">
          <UIcon name="i-lucide-briefcase" class="size-8 text-success" />
          <UBadge :label="String(stats.active)" size="lg" variant="soft" color="success" />
        </div>
        <div>
          <p class="text-sm text-muted">Active</p>
          <p class="text-2xl font-bold">{{ stats.active }}</p>
        </div>
      </UCard>

      <UCard :ui="{ body: 'space-y-2' }">
        <div class="flex items-center justify-between">
          <UIcon name="i-lucide-clock" class="size-8 text-warning" />
          <UBadge :label="String(stats.pending)" size="lg" variant="soft" color="warning" />
        </div>
        <div>
          <p class="text-sm text-muted">Pending</p>
          <p class="text-2xl font-bold">{{ stats.pending }}</p>
        </div>
      </UCard>

      <UCard :ui="{ body: 'space-y-2' }">
        <div class="flex items-center justify-between">
          <UIcon name="i-lucide-check-circle" class="size-8 text-neutral" />
          <UBadge :label="String(stats.closed)" size="lg" variant="soft" color="neutral" />
        </div>
        <div>
          <p class="text-sm text-muted">Closed</p>
          <p class="text-2xl font-bold">{{ stats.closed }}</p>
        </div>
      </UCard>

      <UCard :ui="{ body: 'space-y-2' }">
        <div class="flex items-center justify-between">
          <UIcon name="i-lucide-files" class="size-8 text-info" />
          <UBadge label="+12%" size="sm" variant="soft" color="info" />
        </div>
        <div>
          <p class="text-sm text-muted">Total Documents</p>
          <p class="text-2xl font-bold">{{ cases.reduce((acc, c) => acc + c.documents, 0) }}</p>
        </div>
      </UCard>
    </div>

    <!-- Quick Insights -->
    <div class="bg-muted/5 p-6">
      <UContainer>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-start gap-3">
              <div class="p-2 bg-error/10 rounded-lg">
                <UIcon name="i-lucide-alert-circle" class="size-5 text-error" />
              </div>
              <div class="flex-1">
                <p class="font-semibold mb-1">5 Upcoming Deadlines</p>
                <p class="text-sm text-muted">Next deadline in 3 days</p>
              </div>
              <UButton
                icon="i-lucide-arrow-right"
                size="xs"
                color="neutral"
                variant="ghost"
                to="/deadlines"
              />
            </div>
          </UCard>

          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-start gap-3">
              <div class="p-2 bg-primary/10 rounded-lg">
                <UIcon name="i-lucide-trending-up" class="size-5 text-primary" />
              </div>
              <div class="flex-1">
                <p class="font-semibold mb-1">Activity Trend</p>
                <p class="text-sm text-muted">+23% vs last month</p>
              </div>
              <UButton
                icon="i-lucide-arrow-right"
                size="xs"
                color="neutral"
                variant="ghost"
                to="/analytics"
              />
            </div>
          </UCard>

          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-start gap-3">
              <div class="p-2 bg-success/10 rounded-lg">
                <UIcon name="i-lucide-sparkles" class="size-5 text-success" />
              </div>
              <div class="flex-1">
                <p class="font-semibold mb-1">AI Insights Ready</p>
                <p class="text-sm text-muted">3 cases have new insights</p>
              </div>
              <UButton
                icon="i-lucide-arrow-right"
                size="xs"
                color="neutral"
                variant="ghost"
              />
            </div>
          </UCard>
        </div>
      </UContainer>
    </div>

    <!-- Filters & Controls -->
    <div class="p-6">
      <div class="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div class="flex-1 w-full sm:max-w-md">
          <UInput
            v-model="searchQuery"
            icon="i-lucide-search"
            placeholder="Search cases by name or number..."
          />
        </div>
        <div class="flex items-center gap-2 w-full sm:w-auto">
          <USelectMenu
            v-model="selectedStatus"
            :items="statusOptions"
            class="w-full sm:w-auto"
          />
          <USelectMenu
            v-model="selectedType"
            :items="typeOptions"
            class="w-full sm:w-auto"
          />
          <UButtonGroup>
            <UTooltip text="Grid view">
              <UButton
                icon="i-lucide-layout-grid"
                :variant="viewMode === 'grid' ? 'soft' : 'ghost'"
                color="neutral"
                @click="viewMode = 'grid'"
              />
            </UTooltip>
            <UTooltip text="List view">
              <UButton
                icon="i-lucide-list"
                :variant="viewMode === 'list' ? 'soft' : 'ghost'"
                color="neutral"
                @click="viewMode = 'list'"
              />
            </UTooltip>
          </UButtonGroup>
        </div>
      </div>
    </div>

    <!-- Cases Grid/List -->
    <div class="p-6">
      <UContainer>
        <!-- Grid View -->
        <div v-if="viewMode === 'grid' && filteredCases.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <NuxtLink
            v-for="case_ in filteredCases"
            :key="case_.id"
            :to="`/cases/${case_.id}`"
            class="block"
          >
            <UCard class="hover:shadow-lg transition-all hover:scale-[1.02] h-full" :ui="{ body: 'space-y-4' }">
              <template #header>
                <div class="flex items-start justify-between gap-2">
                  <div class="flex-1 min-w-0">
                    <h3 class="font-semibold text-highlighted truncate mb-1">
                      {{ case_.name }}
                    </h3>
                    <p class="text-sm text-dimmed">{{ case_.caseNumber }}</p>
                  </div>
                  <UBadge
                    :label="case_.status"
                    :color="statusColors[case_.status]"
                    variant="soft"
                    class="capitalize"
                  />
                </div>
              </template>

              <div class="space-y-3">
                <p class="text-sm text-muted line-clamp-2">{{ case_.description }}</p>

                <div class="flex flex-wrap gap-1">
                  <UBadge v-for="tag in case_.tags.slice(0, 3)" :key="tag" :label="tag" size="sm" variant="outline" />
                  <UBadge v-if="case_.tags.length > 3" :label="`+${case_.tags.length - 3}`" size="sm" variant="soft" />
                </div>

                <div class="grid grid-cols-3 gap-2 text-center py-2 border-y border-default">
                  <div>
                    <p class="text-xs text-muted">Documents</p>
                    <p class="font-semibold">{{ case_.documents }}</p>
                  </div>
                  <div>
                    <p class="text-xs text-muted">Parties</p>
                    <p class="font-semibold">{{ case_.parties.length }}</p>
                  </div>
                  <div>
                    <p class="text-xs text-muted">Deadlines</p>
                    <p class="font-semibold">{{ case_.deadlines }}</p>
                  </div>
                </div>

                <div class="space-y-1">
                  <div class="flex items-center justify-between text-xs">
                    <span class="text-muted">Progress</span>
                    <span class="font-medium">{{ case_.progress }}%</span>
                  </div>
                  <UProgress :value="case_.progress" :color="case_.progress === 100 ? 'success' : 'primary'" />
                </div>

                <div class="text-xs text-dimmed">
                  Last activity: {{ new Date(case_.lastActivity).toLocaleDateString() }}
                </div>
              </div>
            </UCard>
          </NuxtLink>
        </div>

        <!-- List View -->
        <div v-else-if="viewMode === 'list' && filteredCases.length" class="space-y-3">
          <NuxtLink
            v-for="case_ in filteredCases"
            :key="case_.id"
            :to="`/cases/${case_.id}`"
            class="block"
          >
            <UCard class="hover:shadow-md transition-shadow" :ui="{ body: 'p-4' }">
              <div class="flex items-center gap-4">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-3 mb-2">
                    <h3 class="font-semibold text-highlighted">{{ case_.name }}</h3>
                    <UBadge :label="case_.status" :color="statusColors[case_.status]" variant="soft" size="sm" class="capitalize" />
                    <span class="text-sm text-dimmed">{{ case_.caseNumber }}</span>
                  </div>
                  <p class="text-sm text-muted line-clamp-1 mb-2">{{ case_.description }}</p>
                  <div class="flex items-center gap-4 text-xs text-dimmed">
                    <span class="flex items-center gap-1">
                      <UIcon name="i-lucide-file-text" class="size-3" />
                      {{ case_.documents }} docs
                    </span>
                    <span class="flex items-center gap-1">
                      <UIcon name="i-lucide-users" class="size-3" />
                      {{ case_.parties.length }} parties
                    </span>
                    <span class="flex items-center gap-1">
                      <UIcon name="i-lucide-calendar" class="size-3" />
                      {{ case_.deadlines }} deadlines
                    </span>
                    <span class="flex items-center gap-1">
                      <UIcon name="i-lucide-clock" class="size-3" />
                      {{ new Date(case_.lastActivity).toLocaleDateString() }}
                    </span>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <div class="w-24">
                    <UProgress :value="case_.progress" :color="case_.progress === 100 ? 'success' : 'primary'" />
                  </div>
                  <UIcon name="i-lucide-chevron-right" class="size-5 text-muted" />
                </div>
              </div>
            </UCard>
          </NuxtLink>
        </div>

        <!-- Empty State -->
        <div v-else class="text-center py-16">
          <UIcon name="i-lucide-folder-open" class="size-20 text-muted mx-auto mb-6 opacity-30" />
          <h3 class="text-2xl font-semibold mb-3 text-highlighted">
            {{ searchQuery || selectedStatus !== 'all' || selectedType !== 'all' ? 'No cases found' : 'No cases yet' }}
          </h3>
          <p class="text-muted mb-6 max-w-md mx-auto">
            {{ searchQuery || selectedStatus !== 'all' || selectedType !== 'all'
              ? 'Try adjusting your filters or search query'
              : 'Get started by creating your first case' }}
          </p>
          <UButton
            label="Create New Case"
            icon="i-lucide-plus"
            color="primary"
            size="lg"
            @click="showCreateModal = true"
          />
        </div>
      </UContainer>
    </div>

    <!-- Create Case Modal -->
    <CreateCaseModal v-model:open="showCreateModal" @created="onCaseCreated" />
    </UDashboardPanelContent>
  </UDashboardPanel>
</template>
