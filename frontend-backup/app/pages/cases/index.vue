<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <UPageHeader
      title="Cases"
      description="Manage your legal cases and documents"
    >
      <template #links>
        <USelectMenu
          v-model="filterStatus"
          :options="statusOptions"
          placeholder="All Cases"
          class="w-40"
        />

        <UInput
          v-model="searchQuery"
          placeholder="Search cases..."
          size="sm"
          class="w-64"
        >
          <template #leading>
            <UIcon name="i-heroicons-magnifying-glass-20-solid" class="w-4 h-4 text-gray-400" />
          </template>
        </UInput>
      </template>

      <UButton
        color="primary"
        @click="createCase"
      >
        <UIcon name="i-heroicons-plus-20-solid" class="w-5 h-5 mr-2" />
        New Case
      </UButton>
    </UPageHeader>

    <!-- Cases Grid -->
    <div class="container mx-auto px-4 py-8">
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <UCard>
          <template #header>
            <div class="flex items-center">
              <div class="p-2 bg-blue-100 rounded-lg">
                <UIcon name="i-heroicons-folder-20-solid" class="w-6 h-6 text-blue-600" />
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-gray-600">Total Cases</p>
              </div>
            </div>
          </template>
          <p class="text-2xl font-bold text-gray-900">{{ stats.total }}</p>
        </UCard>

        <UCard>
          <template #header>
            <div class="flex items-center">
              <div class="p-2 bg-green-100 rounded-lg">
                <UIcon name="i-heroicons-play-20-solid" class="w-6 h-6 text-green-600" />
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-gray-600">Active Cases</p>
              </div>
            </div>
          </template>
          <p class="text-2xl font-bold text-gray-900">{{ stats.active }}</p>
        </UCard>

        <UCard>
          <template #header>
            <div class="flex items-center">
              <div class="p-2 bg-yellow-100 rounded-lg">
                <UIcon name="i-heroicons-pause-20-solid" class="w-6 h-6 text-yellow-600" />
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-gray-600">Unloaded Cases</p>
              </div>
            </div>
          </template>
          <p class="text-2xl font-bold text-gray-900">{{ stats.unloaded }}</p>
        </UCard>

        <UCard>
          <template #header>
            <div class="flex items-center">
              <div class="p-2 bg-purple-100 rounded-lg">
                <UIcon name="i-heroicons-document-20-solid" class="w-6 h-6 text-purple-600" />
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-gray-600">Total Documents</p>
              </div>
            </div>
          </template>
          <p class="text-2xl font-bold text-gray-900">{{ stats.totalDocuments }}</p>
        </UCard>
      </div>

      <!-- Cases Grid -->
      <div v-if="loading">
        <UPageGrid>
          <UCard v-for="n in 6" :key="n">
            <USkeleton class="h-48" />
          </UCard>
        </UPageGrid>
      </div>

      <UCard v-else-if="filteredCases.length === 0" class="text-center">
        <template #header>
          <UIcon name="i-heroicons-folder-open-20-solid" class="w-16 h-16 text-gray-300 mx-auto" />
        </template>
        <h3 class="text-lg font-medium text-gray-900 mb-2">No cases found</h3>
        <p class="text-gray-500 mb-6">
          {{ searchQuery ? 'Try adjusting your search terms' : 'Create your first case to get started' }}
        </p>
        <template #footer>
          <UButton
            v-if="!searchQuery"
            color="primary"
            @click="createCase"
          >
            <UIcon name="i-heroicons-plus-20-solid" class="w-5 h-5 mr-2" />
            Create Case
          </UButton>
        </template>
      </UCard>

      <UPageGrid v-else>
        <CaseCard
          v-for="caseItem in filteredCases"
          :key="caseItem.id"
          :case="caseItem"
          @load="loadCase"
          @unload="unloadCase"
          @archive="archiveCase"
          @delete="deleteCase"
        />
      </UPageGrid>

      <!-- Load More -->
      <div v-if="hasMore && !loading" class="text-center mt-8">
        <UButton
          variant="outline"
          @click="loadMore"
        >
          Load More Cases
        </UButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const { apiFetch } = useApi()

// Types
interface CaseItem {
  id: string
  name: string
  case_number?: string
  client?: string
  matter_type?: string
  status: string
  created_at: string
  last_activity?: string
  document_count?: number
  total_size?: number
  entity_count?: number
  progress?: number
}

interface CasesResponse {
  cases: CaseItem[]
  has_more: boolean
}

interface StatsResponse {
  stats: {
    total: number
    active: number
    unloaded: number
    archived: number
    totalDocuments: number
  }
}

// Reactive state
const cases = ref<CaseItem[]>([])
const loading = ref(true)
const searchQuery = ref('')
const filterStatus = ref('')
const currentPage = ref(0)
const hasMore = ref(false)

// Modal instances
const overlay = useOverlay()
const archiveModal = overlay.create(() => import('~/components/modals/ArchiveCaseModal.vue'))
const deleteModal = overlay.create(() => import('~/components/modals/DeleteCaseModal.vue'))

// Stats
const stats = ref({
  total: 0,
  active: 0,
  unloaded: 0,
  archived: 0,
  totalDocuments: 0
})

// Options
const statusOptions = [
  { label: 'All Cases', value: '' },
  { label: 'Active', value: 'active' },
  { label: 'Unloaded', value: 'unloaded' },
  { label: 'Archived', value: 'archived' }
]

// Computed
const filteredCases = computed(() => {
  let filtered = cases.value

  // Filter by status
  if (filterStatus.value) {
    filtered = filtered.filter((caseItem: any) => caseItem.status === filterStatus.value)
  }

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter((caseItem: any) =>
      caseItem.name.toLowerCase().includes(query) ||
      caseItem.case_number?.toLowerCase().includes(query) ||
      caseItem.client?.toLowerCase().includes(query)
    )
  }

  return filtered
})

// Methods
async function loadCases() {
  loading.value = true
  try {
    const response = await apiFetch('/cases', {
      params: {
        page: currentPage.value,
        limit: 20
      }
    }) as CasesResponse

    if (currentPage.value === 0) {
      cases.value = response.cases || []
    } else {
      cases.value.push(...(response.cases || []))
    }

    hasMore.value = response.has_more || false

  } catch (error) {
    console.error('Failed to load cases:', error)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const response = await apiFetch('/cases/stats') as StatsResponse
    stats.value = response.stats || stats.value
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

function createCase() {
  navigateTo('/cases/new')
}


async function loadCase(caseItem: any) {
  try {
    await apiFetch(`/cases/${caseItem.id}/load`, {
      method: 'POST'
    })
    caseItem.status = 'active'
    await loadStats() // Refresh stats
  } catch (error) {
    console.error('Failed to load case:', error)
  }
}

async function unloadCase(caseItem: any) {
  try {
    await apiFetch(`/cases/${caseItem.id}/unload`, {
      method: 'POST'
    })
    caseItem.status = 'unloaded'
    await loadStats() // Refresh stats
  } catch (error) {
    console.error('Failed to unload case:', error)
  }
}

async function archiveCase(caseItem: any) {
  const instance = archiveModal.open({ case: caseItem })
  const confirmed = await instance.result

  if (confirmed) {
    try {
      await apiFetch(`/cases/${caseItem.id}/archive`, {
        method: 'POST'
      })
      caseItem.status = 'archived'
      await loadStats() // Refresh stats
    } catch (error) {
      console.error('Failed to archive case:', error)
    }
  }
}

async function deleteCase(caseItem: any) {
  const instance = deleteModal.open({ case: caseItem })
  const confirmed = await instance.result

  if (confirmed) {
    try {
      await apiFetch(`/cases/${caseItem.id}`, {
        method: 'DELETE'
      })

      // Remove from local list
      const index = cases.value.findIndex((c: any) => c.id === caseItem.id)
      if (index > -1) {
        cases.value.splice(index, 1)
      }

      await loadStats() // Refresh stats
    } catch (error) {
      console.error('Failed to delete case:', error)
    }
  }
}

function loadMore() {
  currentPage.value++
  loadCases()
}


// Lifecycle
onMounted(async () => {
  await Promise.all([loadCases(), loadStats()])
})
</script>