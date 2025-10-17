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

// Use shared data cache system
const { cases: casesCache } = useSharedData()

// Initialize shared data on page mount - only fetch if cache is stale
await casesCache.get()

// Access the cached cases data
const casesData = computed(() => casesCache.data.value || { cases: [], total: 0 })

// Transform backend data to frontend format
const cases = computed(() => {
  return (casesData.value?.cases || []).map((c: any) => ({
    id: String(c.id),
    name: c.name,
    caseNumber: c.case_number,
    type: c.matter_type || 'General',
    status: c.status.toLowerCase(),
    court: 'N/A', // TODO: Add to backend
    jurisdiction: 'N/A', // TODO: Add to backend
    openedDate: c.created_at,
    lastActivity: c.updated_at,
    parties: [c.client], // TODO: Add proper parties to backend
    documents: c.document_count || 0,
    deadlines: 0, // TODO: Add to backend
    description: c.matter_type ? `${c.matter_type} case` : 'Legal case',
    tags: c.matter_type ? [c.matter_type.toLowerCase()] : [],
    progress: c.status === 'ACTIVE' ? 50 : c.status === 'STAGING' ? 25 : c.status === 'UNLOADED' ? 100 : 0
  }))
})

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
  return cases.value.filter((c: any) => {
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
  active: cases.value.filter((c: any) => c.status === 'active').length,
  pending: cases.value.filter((c: any) => c.status === 'staging').length,
  closed: cases.value.filter((c: any) => c.status === 'unloaded').length,
  totalDocuments: cases.value.reduce((acc: number, c: any) => acc + c.documents, 0)
}))

const statusColors: Record<string, string> = {
  active: 'success',
  staging: 'warning',
  pending: 'warning',
  unloaded: 'neutral',
  closed: 'neutral'
}

async function onCaseCreated(caseData: any) {
  console.log('Case created:', caseData)
  await casesCache.refresh() // Refresh the cached cases list
  showCreateModal.value = false
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

    <template #body>
      <div class="max-w-7xl mx-auto space-y-6">
        <!-- Stats Cards -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-primary/10 rounded-lg">
                <UIcon name="i-lucide-folder" class="size-5 text-primary" />
              </div>
              <div>
                <p class="text-xs text-muted">Total Cases</p>
                <p class="text-2xl font-bold">{{ stats.total }}</p>
              </div>
            </div>
          </UCard>

          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-success/10 rounded-lg">
                <UIcon name="i-lucide-briefcase" class="size-5 text-success" />
              </div>
              <div>
                <p class="text-xs text-muted">Active</p>
                <p class="text-2xl font-bold">{{ stats.active }}</p>
              </div>
            </div>
          </UCard>

          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-warning/10 rounded-lg">
                <UIcon name="i-lucide-clock" class="size-5 text-warning" />
              </div>
              <div>
                <p class="text-xs text-muted">Pending</p>
                <p class="text-2xl font-bold">{{ stats.pending }}</p>
              </div>
            </div>
          </UCard>

          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-neutral/10 rounded-lg">
                <UIcon name="i-lucide-check-circle" class="size-5 text-neutral" />
              </div>
              <div>
                <p class="text-xs text-muted">Closed</p>
                <p class="text-2xl font-bold">{{ stats.closed }}</p>
              </div>
            </div>
          </UCard>

          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-info/10 rounded-lg">
                <UIcon name="i-lucide-files" class="size-5 text-info" />
              </div>
              <div>
                <p class="text-xs text-muted">Documents</p>
                <p class="text-2xl font-bold">{{ stats.totalDocuments }}</p>
              </div>
            </div>
          </UCard>
        </div>

        <!-- Filters & Controls -->
        <div class="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div class="flex-1 w-full sm:max-w-md">
            <UInput
              v-model="searchQuery"
              icon="i-lucide-search"
              placeholder="Search cases by name or number..."
              size="md"
            />
          </div>
          <div class="flex items-center gap-3 w-full sm:w-auto">
            <USelectMenu
              v-model="selectedStatus"
              :items="statusOptions"
              class="w-full sm:w-auto"
              size="md"
            />
            <USelectMenu
              v-model="selectedType"
              :items="typeOptions"
              class="w-full sm:w-auto"
              size="md"
            />
            <UFieldGroup size="md">
              <UTooltip text="Grid view">
                <UButton
                  icon="i-lucide-layout-grid"
                  :variant="viewMode === 'grid' ? 'soft' : 'ghost'"
                  color="primary"
                  @click="viewMode = 'grid'"
                />
              </UTooltip>
              <UTooltip text="List view">
                <UButton
                  icon="i-lucide-list"
                  :variant="viewMode === 'list' ? 'soft' : 'ghost'"
                  color="primary"
                  @click="viewMode = 'list'"
                />
              </UTooltip>
            </UFieldGroup>
          </div>
        </div>

        <!-- Cases Grid/List -->
        <div>
          <!-- Grid View -->
          <div v-if="viewMode === 'grid' && filteredCases.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <NuxtLink
              v-for="case_ in filteredCases"
              :key="case_.id"
              :to="`/cases/${case_.id}`"
              class="block group"
            >
              <UCard
                class="hover:shadow-lg transition-all h-full hover:border-primary/50"
                :ui="{ body: 'space-y-3 p-4' }"
              >
                <div class="flex items-start justify-between gap-2 mb-3">
                  <div class="flex-1 min-w-0">
                    <h3 class="font-bold text-base truncate mb-1 group-hover:text-primary transition-colors">
                      {{ case_.name }}
                    </h3>
                    <p class="text-xs text-muted">{{ case_.caseNumber }}</p>
                  </div>
                  <UBadge
                    :label="case_.status"
                    :color="statusColors[case_.status]"
                    variant="soft"
                    size="sm"
                    class="capitalize"
                  />
                </div>

                <p class="text-sm text-muted line-clamp-2">{{ case_.description }}</p>

                <div class="flex flex-wrap gap-1.5">
                  <UBadge
                    v-for="tag in case_.tags.slice(0, 3)"
                    :key="tag"
                    :label="tag"
                    size="sm"
                    variant="outline"
                  />
                  <UBadge
                    v-if="case_.tags.length > 3"
                    :label="`+${case_.tags.length - 3}`"
                    size="sm"
                    variant="soft"
                    color="primary"
                  />
                </div>

                <div class="flex items-center justify-between pt-3 border-t border-default">
                  <div class="flex items-center gap-2 text-sm text-muted">
                    <UIcon name="i-lucide-file-text" class="size-4" />
                    <span>{{ case_.documents }} docs</span>
                  </div>
                  <div class="flex items-center gap-2 text-xs text-muted">
                    <UIcon name="i-lucide-clock" class="size-3.5" />
                    <span>{{ new Date(case_.lastActivity).toLocaleDateString() }}</span>
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
              class="block group"
            >
              <UCard
                class="hover:shadow-lg transition-all hover:border-primary/50"
                :ui="{ body: 'p-4' }"
              >
                <div class="flex items-center gap-4">
                  <div class="flex-shrink-0">
                    <div class="p-3 bg-primary/10 rounded-lg">
                      <UIcon name="i-lucide-folder" class="size-6 text-primary" />
                    </div>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-3 mb-1">
                      <h3 class="font-bold text-base group-hover:text-primary transition-colors">{{ case_.name }}</h3>
                      <UBadge
                        :label="case_.status"
                        :color="statusColors[case_.status]"
                        variant="soft"
                        size="sm"
                        class="capitalize"
                      />
                      <span class="text-xs text-muted">{{ case_.caseNumber }}</span>
                    </div>
                    <p class="text-sm text-muted line-clamp-1 mb-2">{{ case_.description }}</p>
                    <div class="flex items-center gap-4 text-sm">
                      <span class="flex items-center gap-1.5 text-muted">
                        <UIcon name="i-lucide-file-text" class="size-4" />
                        {{ case_.documents }} docs
                      </span>
                      <span class="flex items-center gap-1.5 text-muted">
                        <UIcon name="i-lucide-clock" class="size-4" />
                        {{ new Date(case_.lastActivity).toLocaleDateString() }}
                      </span>
                    </div>
                  </div>
                  <div class="flex items-center gap-2 flex-shrink-0">
                    <UIcon name="i-lucide-chevron-right" class="size-5 text-muted group-hover:text-primary transition-colors" />
                  </div>
                </div>
              </UCard>
            </NuxtLink>
          </div>

          <!-- Empty State -->
          <div v-else class="text-center py-20">
            <div class="rounded-xl p-12 max-w-lg mx-auto">
              <div class="p-4 bg-muted/10 rounded-lg w-fit mx-auto mb-6">
                <UIcon name="i-lucide-folder-open" class="size-16 text-muted" />
              </div>
              <h3 class="text-2xl font-bold mb-3">
                {{ searchQuery || selectedStatus !== 'all' || selectedType !== 'all' ? 'No cases found' : 'No cases yet' }}
              </h3>
              <p class="text-muted mb-6">
                {{ searchQuery || selectedStatus !== 'all' || selectedType !== 'all'
                  ? 'Try adjusting your filters or search query'
                  : 'Get started by creating your first case' }}
              </p>
              <UButton
                v-if="!searchQuery && selectedStatus === 'all' && selectedType === 'all'"
                label="Create New Case"
                icon="i-lucide-plus"
                color="primary"
                @click="showCreateModal = true"
              />
            </div>
          </div>
        </div>

        <!-- Create Case Modal -->
        <LazyModalsCreateCaseModal v-if="showCreateModal" v-model:open="showCreateModal" @created="onCaseCreated" />
      </div>
    </template>
  </UDashboardPanel>
</template>
