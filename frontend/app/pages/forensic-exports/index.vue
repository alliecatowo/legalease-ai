<script setup lang="ts">
import { ref, computed } from 'vue'

definePageMeta({
  layout: 'default'
})

const api = useApi()
const toast = useToast()

// View mode
const viewMode = ref<'list' | 'table'>('list')

// Multi-select state
const selectedExports = ref<number[]>([])
const isDeletingBulk = ref(false)

// Scan modal state
const showScanModal = ref(false)
const selectedCaseForScan = ref<number | null>(null)
const scanPath = ref('/data/forensic-exports')
const isScanning = ref(false)
const scanResults = ref<any>(null)

// Common paths for quick selection
const commonPaths = [
  { label: 'Forensic Exports (Default)', value: '/data/forensic-exports', icon: 'i-lucide-hard-drive' },
  { label: 'Root of mounted drive', value: '/data/forensic-exports/', icon: 'i-lucide-folder' }
]

// Directory picker
function openDirectoryPicker() {
  const input = document.createElement('input')
  input.type = 'file'
  input.webkitdirectory = true
  input.onchange = (e: any) => {
    if (e.target.files.length > 0) {
      // Get the full path from the first file
      const firstFile = e.target.files[0]
      // Extract the directory path by removing the filename
      let fullPath = firstFile.webkitRelativePath
      const pathParts = fullPath.split('/')
      pathParts.pop() // Remove filename
      const folderPath = '/' + pathParts.join('/')

      // Try to map local path to container path
      if (folderPath.includes('My Passport')) {
        // Map local removable media path to container path
        const relativePath = folderPath.split('My Passport')[1] || ''
        scanPath.value = '/data/forensic-exports' + relativePath
      } else {
        // Use the path as-is
        scanPath.value = folderPath
      }
    }
  }
  input.click()
}

// Filters
const searchQuery = ref('')
const selectedCase = ref<number | null>(null)
const selectedStatus = ref<string | null>(null)
const sortBy = ref<string>('recent')

// Fetch cases for filter
const { data: casesData } = await useAsyncData(
  'cases-forensic-exports',
  () => api.cases.list(),
  { default: () => ({ cases: [], total: 0, page: 1, page_size: 50 }) }
)

const caseOptions = computed(() => [
  { label: 'All Cases', value: null },
  ...(casesData.value?.cases || []).map((c: any) => ({
    label: c.name,
    value: c.id
  }))
])

// Fetch all forensic exports
const { data: exportsData, pending: loadingExports, refresh: refreshExports } = await useAsyncData(
  'all-forensic-exports',
  async () => {
    try {
      const response = await api.forensicExports.listAll()

      // Enrich with case names
      const enriched = (response.exports || []).map((exp: any) => {
        const caseItem = casesData.value?.cases?.find((c: any) => c.id === exp.case_id)
        return {
          ...exp,
          case_name: caseItem?.name || `Case ${exp.case_id}`
        }
      })

      return enriched
    } catch (error) {
      console.error('Error fetching forensic exports:', error)
      return []
    }
  },
  { default: () => [] }
)

// Filtered and sorted exports
const filteredExports = computed(() => {
  let result = exportsData.value || []

  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter((exp: any) =>
      exp.folder_name?.toLowerCase().includes(query) ||
      exp.case_name?.toLowerCase().includes(query) ||
      exp.export_uuid?.toLowerCase().includes(query)
    )
  }

  // Case filter
  if (selectedCase.value) {
    result = result.filter((exp: any) => exp.case_id === selectedCase.value)
  }

  // Status filter
  if (selectedStatus.value) {
    result = result.filter((exp: any) => exp.export_status === selectedStatus.value)
  }

  // Sorting
  if (sortBy.value === 'recent') {
    result.sort((a: any, b: any) => new Date(b.discovered_at).getTime() - new Date(a.discovered_at).getTime())
  } else if (sortBy.value === 'oldest') {
    result.sort((a: any, b: any) => new Date(a.discovered_at).getTime() - new Date(b.discovered_at).getTime())
  } else if (sortBy.value === 'name-az') {
    result.sort((a: any, b: any) => (a.folder_name || '').localeCompare(b.folder_name || ''))
  } else if (sortBy.value === 'name-za') {
    result.sort((a: any, b: any) => (b.folder_name || '').localeCompare(a.folder_name || ''))
  } else if (sortBy.value === 'size-large') {
    result.sort((a: any, b: any) => (b.size_bytes || 0) - (a.size_bytes || 0))
  } else if (sortBy.value === 'size-small') {
    result.sort((a: any, b: any) => (a.size_bytes || 0) - (b.size_bytes || 0))
  } else if (sortBy.value === 'records-high') {
    result.sort((a: any, b: any) => (b.total_records || 0) - (a.total_records || 0))
  } else if (sortBy.value === 'records-low') {
    result.sort((a: any, b: any) => (a.total_records || 0) - (b.total_records || 0))
  }

  return result
})

// Statistics
const stats = computed(() => ({
  total: exportsData.value?.length || 0,
  totalRecords: exportsData.value?.reduce((acc: number, exp: any) => acc + (exp.total_records || 0), 0) || 0,
  totalAttachments: exportsData.value?.reduce((acc: number, exp: any) => acc + (exp.num_attachments || 0), 0) || 0,
  totalSize: exportsData.value?.reduce((acc: number, exp: any) => acc + (exp.size_bytes || 0), 0) || 0
}))

// Utility functions
function formatBytes(bytes: number) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
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

function formatNumber(num: number) {
  if (!num) return '0'
  return num.toLocaleString('en-US')
}

// Scan location
async function scanLocation() {
  if (!selectedCaseForScan.value || !scanPath.value) {
    toast.add({
      title: 'Missing Information',
      description: 'Please select a case and enter a path to scan',
      color: 'error'
    })
    return
  }

  isScanning.value = true
  scanResults.value = null

  try {
    const response = await api.forensicExports.scan(selectedCaseForScan.value, scanPath.value)

    scanResults.value = response

    const foundCount = response.found?.length || 0
    const existingCount = response.existing?.length || 0
    const errorCount = response.errors?.length || 0

    toast.add({
      title: 'Scan Complete',
      description: `Found ${foundCount} new export(s), ${existingCount} existing, ${errorCount} error(s)`,
      color: foundCount > 0 ? 'success' : 'info'
    })

    // Refresh the list if new exports were found
    if (foundCount > 0) {
      await refreshExports()
    }
  } catch (error: any) {
    toast.add({
      title: 'Scan Failed',
      description: error.message || 'An error occurred during scanning',
      color: 'error'
    })
  } finally {
    isScanning.value = false
  }
}

function closeScanModal() {
  showScanModal.value = false
  selectedCaseForScan.value = null
  scanPath.value = '/data/forensic-exports'
  scanResults.value = null
}

// Delete export
async function deleteExport(id: number) {
  if (!confirm('Delete this export record? (Files will remain on disk)')) {
    return
  }

  try {
    await api.forensicExports.delete(id)
    toast.add({
      title: 'Success',
      description: 'Export record deleted successfully',
      color: 'success'
    })
    await refreshExports()
  } catch (error: any) {
    toast.add({
      title: 'Error',
      description: error.message || 'Failed to delete export',
      color: 'error'
    })
  }
}

// Verify export
async function verifyExport(id: number) {
  try {
    const response = await api.forensicExports.verify(id)
    toast.add({
      title: response.exists ? 'Export Verified' : 'Export Not Found',
      description: response.exists ? 'Export folder exists on disk' : 'Export folder not found on disk',
      color: response.exists ? 'success' : 'warning'
    })

    if (response.exists) {
      await refreshExports()
    }
  } catch (error: any) {
    toast.add({
      title: 'Verification Failed',
      description: error.message || 'Failed to verify export',
      color: 'error'
    })
  }
}

// Table columns for UTable
const columns = [
  { accessorKey: 'folder_name', header: 'Folder Name' },
  { accessorKey: 'case_name', header: 'Case' },
  { accessorKey: 'total_records', header: 'Total Records' },
  { accessorKey: 'num_attachments', header: 'Attachments' },
  { accessorKey: 'size_bytes', header: 'Size' },
  { accessorKey: 'export_status', header: 'Status' },
  { accessorKey: 'discovered_at', header: 'Discovered' },
  { accessorKey: 'actions', header: 'Actions' }
]

// Status badge colors
const statusColors: Record<string, string> = {
  'Completed': 'success',
  'Completed with Problems': 'warning',
  'Failed': 'error',
  'In Progress': 'info'
}

// Multi-select functions
const allSelected = computed(() =>
  filteredExports.value.length > 0 &&
  selectedExports.value.length === filteredExports.value.length
)

const someSelected = computed(() =>
  selectedExports.value.length > 0 &&
  selectedExports.value.length < filteredExports.value.length
)

function toggleSelectAll() {
  if (allSelected.value) {
    selectedExports.value = []
  } else {
    selectedExports.value = filteredExports.value.map((exp: any) => exp.id)
  }
}

function toggleSelect(id: number) {
  const index = selectedExports.value.indexOf(id)
  if (index > -1) {
    selectedExports.value.splice(index, 1)
  } else {
    selectedExports.value.push(id)
  }
}

function isSelected(id: number) {
  return selectedExports.value.includes(id)
}

async function deleteBulk() {
  if (selectedExports.value.length === 0) return

  const count = selectedExports.value.length
  if (!confirm(`Delete ${count} export record${count > 1 ? 's' : ''}? (Files will remain on disk)`)) {
    return
  }

  isDeletingBulk.value = true

  try {
    // Delete all selected exports
    await Promise.all(
      selectedExports.value.map(id => api.forensicExports.delete(id))
    )

    toast.add({
      title: 'Success',
      description: `${count} export record${count > 1 ? 's' : ''} deleted successfully`,
      color: 'success'
    })

    selectedExports.value = []
    await refreshExports()
  } catch (error: any) {
    toast.add({
      title: 'Error',
      description: error.message || 'Failed to delete exports',
      color: 'error'
    })
  } finally {
    isDeletingBulk.value = false
  }
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Forensic Exports">
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
              :loading="loadingExports"
              @click="refreshExports"
            />
            <UButton
              icon="i-lucide-scan"
              color="primary"
              label="Scan Location"
              @click="showScanModal = true"
            />
          </UFieldGroup>
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <div class="max-w-7xl mx-auto space-y-6">

        <!-- Stats Bar -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <!-- Total Exports -->
          <div class="bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 rounded-xl p-6 hover:shadow-lg transition-all duration-200">
            <div class="flex items-start justify-between mb-4">
              <div class="p-3 bg-primary/10 rounded-lg">
                <UIcon name="i-lucide-database" class="size-8 text-primary" />
              </div>
              <UBadge color="primary" variant="subtle" size="sm">Total</UBadge>
            </div>
            <div>
              <p class="text-3xl font-bold text-primary mb-1">{{ stats.total }}</p>
              <p class="text-sm font-medium text-muted">Total Exports</p>
            </div>
          </div>

          <!-- Total Records -->
          <div class="bg-gradient-to-br from-success/10 to-success/5 border border-success/20 rounded-xl p-6 hover:shadow-lg transition-all duration-200">
            <div class="flex items-start justify-between mb-4">
              <div class="p-3 bg-success/10 rounded-lg">
                <UIcon name="i-lucide-file-text" class="size-8 text-success" />
              </div>
              <UBadge color="success" variant="subtle" size="sm">Records</UBadge>
            </div>
            <div>
              <p class="text-3xl font-bold text-success mb-1">{{ formatNumber(stats.totalRecords) }}</p>
              <p class="text-sm font-medium text-muted">Total Records</p>
            </div>
          </div>

          <!-- Total Attachments -->
          <div class="bg-gradient-to-br from-warning/10 to-warning/5 border border-warning/20 rounded-xl p-6 hover:shadow-lg transition-all duration-200">
            <div class="flex items-start justify-between mb-4">
              <div class="p-3 bg-warning/10 rounded-lg">
                <UIcon name="i-lucide-paperclip" class="size-8 text-warning" />
              </div>
              <UBadge color="warning" variant="subtle" size="sm">Files</UBadge>
            </div>
            <div>
              <p class="text-3xl font-bold text-warning mb-1">{{ formatNumber(stats.totalAttachments) }}</p>
              <p class="text-sm font-medium text-muted">Attachments</p>
            </div>
          </div>

          <!-- Total Size -->
          <div class="bg-gradient-to-br from-info/10 to-info/5 border border-info/20 rounded-xl p-6 hover:shadow-lg transition-all duration-200">
            <div class="flex items-start justify-between mb-4">
              <div class="p-3 bg-info/10 rounded-lg">
                <UIcon name="i-lucide-hard-drive" class="size-8 text-info" />
              </div>
              <UBadge color="info" variant="subtle" size="sm">Storage</UBadge>
            </div>
            <div>
              <p class="text-3xl font-bold text-info mb-1">{{ formatBytes(stats.totalSize) }}</p>
              <p class="text-sm font-medium text-muted">Total Size</p>
            </div>
          </div>
        </div>

        <!-- Bulk Actions Toolbar -->
        <div v-if="selectedExports.length > 0" class="bg-primary/10 border border-primary/20 rounded-xl p-4">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-check-circle" class="size-5 text-primary" />
              <span class="font-semibold text-highlighted">
                {{ selectedExports.length }} export{{ selectedExports.length > 1 ? 's' : '' }} selected
              </span>
            </div>
            <UFieldGroup>
              <UButton
                label="Deselect All"
                icon="i-lucide-x"
                color="neutral"
                variant="outline"
                @click="selectedExports = []"
              />
              <UButton
                label="Delete Selected"
                icon="i-lucide-trash-2"
                color="error"
                variant="soft"
                :loading="isDeletingBulk"
                @click="deleteBulk"
              />
            </UFieldGroup>
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
                  placeholder="Search exports by name, case, or UUID..."
                  size="lg"
                />
              </div>

              <!-- View Mode Toggle -->
              <UFieldGroup>
                <UButton
                  :icon="viewMode === 'table' ? 'i-lucide-table-2' : 'i-lucide-table'"
                  :color="viewMode === 'table' ? 'primary' : 'neutral'"
                  :variant="viewMode === 'table' ? 'soft' : 'ghost'"
                  @click="viewMode = 'table'"
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
              <!-- Case Filter -->
              <USelectMenu
                v-model="selectedCase"
                :items="caseOptions"
                placeholder="Filter by case"
                value-key="value"
                class="w-full md:w-64"
              />

              <!-- Status Filter -->
              <USelectMenu
                v-model="selectedStatus"
                :items="[
                  { label: 'All Status', value: null },
                  { label: 'Completed', value: 'Completed' },
                  { label: 'Completed with Problems', value: 'Completed with Problems' },
                  { label: 'Failed', value: 'Failed' },
                  { label: 'In Progress', value: 'In Progress' }
                ]"
                placeholder="Filter by status"
                value-key="value"
                class="w-full md:w-56"
              />

              <!-- Sort -->
              <USelectMenu
                v-model="sortBy"
                :items="[
                  { label: 'Most Recent', value: 'recent' },
                  { label: 'Oldest First', value: 'oldest' },
                  { label: 'Name (A-Z)', value: 'name-az' },
                  { label: 'Name (Z-A)', value: 'name-za' },
                  { label: 'Size (Largest)', value: 'size-large' },
                  { label: 'Size (Smallest)', value: 'size-small' },
                  { label: 'Records (Most)', value: 'records-high' },
                  { label: 'Records (Least)', value: 'records-low' }
                ]"
                placeholder="Sort by"
                value-key="value"
                class="w-full md:w-56"
              />
            </div>

            <!-- Active Filters -->
            <div v-if="searchQuery || selectedCase || selectedStatus" class="flex flex-wrap gap-2">
              <UBadge v-if="searchQuery" color="primary" variant="soft">
                Search: {{ searchQuery }}
                <UButton icon="i-lucide-x" size="xs" color="primary" variant="ghost" @click="searchQuery = ''" />
              </UBadge>
              <UBadge v-if="selectedCase" color="primary" variant="soft">
                Case: {{ caseOptions.find(c => c.value === selectedCase)?.label }}
                <UButton icon="i-lucide-x" size="xs" color="primary" variant="ghost" @click="selectedCase = null" />
              </UBadge>
              <UBadge v-if="selectedStatus" color="primary" variant="soft">
                Status: {{ selectedStatus }}
                <UButton icon="i-lucide-x" size="xs" color="primary" variant="ghost" @click="selectedStatus = null" />
              </UBadge>
            </div>

            <!-- Results Count & Select All -->
            <div class="flex items-center justify-between">
              <div class="text-sm text-muted">
                Showing {{ filteredExports.length }} of {{ stats.total }} exports
              </div>
              <UButton
                v-if="filteredExports.length > 0"
                :label="allSelected ? 'Deselect All' : 'Select All'"
                :icon="allSelected ? 'i-lucide-check-square' : (someSelected ? 'i-lucide-minus-square' : 'i-lucide-square')"
                color="primary"
                variant="ghost"
                size="sm"
                @click="toggleSelectAll"
              />
            </div>
          </div>
        </UCard>

        <!-- Table View -->
        <div v-if="viewMode === 'table' && filteredExports.length > 0">
          <UTable
            :data="filteredExports"
            :columns="columns"
            class="w-full"
            @select="(row: any) => navigateTo(`/forensic-exports/${row.id}`)"
          >
            <template #folder_name-data="{ row }">
              <div class="font-semibold truncate max-w-xs">
                {{ row.folder_name || 'Unnamed Export' }}
              </div>
            </template>

            <template #case_name-data="{ row }">
              <UBadge color="neutral" variant="subtle" size="sm">
                {{ row.case_name }}
              </UBadge>
            </template>

            <template #total_records-data="{ row }">
              <div class="text-sm">
                {{ formatNumber(row.total_records || 0) }}
              </div>
            </template>

            <template #num_attachments-data="{ row }">
              <div class="text-sm">
                {{ formatNumber(row.num_attachments || 0) }}
              </div>
            </template>

            <template #size_bytes-data="{ row }">
              <div class="text-sm font-medium">
                {{ formatBytes(row.size_bytes || 0) }}
              </div>
            </template>

            <template #export_status-data="{ row }">
              <UBadge
                v-if="row.export_status"
                :color="statusColors[row.export_status] || 'neutral'"
                variant="soft"
                size="sm"
                class="capitalize"
              >
                {{ row.export_status }}
              </UBadge>
              <span v-else class="text-sm text-muted">Unknown</span>
            </template>

            <template #discovered_at-data="{ row }">
              <div class="text-sm text-muted">
                {{ formatDate(row.discovered_at) }}
              </div>
            </template>

            <template #actions-data="{ row }">
              <div class="flex items-center gap-1" @click.stop>
                <UTooltip text="Verify Export">
                  <UButton
                    icon="i-lucide-shield-check"
                    variant="ghost"
                    color="neutral"
                    size="sm"
                    @click="verifyExport(row.id)"
                  />
                </UTooltip>
                <UDropdownMenu
                  :items="[
                    [
                      { label: 'View Details', icon: 'i-lucide-eye', click: () => navigateTo(`/forensic-exports/${row.id}`) },
                      { label: 'Verify', icon: 'i-lucide-shield-check', click: () => verifyExport(row.id) }
                    ],
                    [
                      { label: 'Delete Record', icon: 'i-lucide-trash', color: 'error', click: () => deleteExport(row.id) }
                    ]
                  ]"
                >
                  <UButton
                    icon="i-lucide-more-vertical"
                    variant="ghost"
                    color="neutral"
                    size="sm"
                  />
                </UDropdownMenu>
              </div>
            </template>
          </UTable>
        </div>

        <!-- List View -->
        <div v-if="viewMode === 'list' && filteredExports.length > 0" class="space-y-3">
          <UCard
            v-for="exp in filteredExports"
            :key="exp.id"
            :class="[
              'hover:shadow-md transition-all',
              isSelected(exp.id) ? 'ring-2 ring-primary bg-primary/5' : ''
            ]"
          >
            <div class="flex items-start gap-4">
              <!-- Checkbox -->
              <div class="flex-shrink-0 pt-3">
                <UCheckbox
                  :model-value="isSelected(exp.id)"
                  @update:model-value="toggleSelect(exp.id)"
                  @click.stop
                />
              </div>

              <!-- Icon -->
              <div
                class="flex-shrink-0 p-3 bg-primary/10 rounded-lg cursor-pointer"
                @click="navigateTo(`/forensic-exports/${exp.id}`)"
              >
                <UIcon name="i-lucide-database" class="size-6 text-primary" />
              </div>

              <!-- Content -->
              <div
                class="flex-1 min-w-0 cursor-pointer"
                @click="navigateTo(`/forensic-exports/${exp.id}`)"
              >
                <div class="flex items-start justify-between gap-4">
                  <div class="flex-1 min-w-0">
                    <h3 class="font-semibold text-base truncate">
                      {{ exp.folder_name || 'Unnamed Export' }}
                    </h3>
                    <div class="flex items-center gap-3 mt-1 text-sm text-muted flex-wrap">
                      <UBadge color="neutral" variant="subtle" size="sm">
                        {{ exp.case_name }}
                      </UBadge>
                      <span>{{ formatNumber(exp.total_records || 0) }} records</span>
                      <span>•</span>
                      <span>{{ formatNumber(exp.num_attachments || 0) }} attachments</span>
                      <span>•</span>
                      <span>{{ formatBytes(exp.size_bytes || 0) }}</span>
                      <UBadge
                        v-if="exp.export_status"
                        :color="statusColors[exp.export_status] || 'neutral'"
                        variant="subtle"
                        size="sm"
                      >
                        {{ exp.export_status }}
                      </UBadge>
                    </div>
                    <p class="text-sm text-muted mt-2">
                      Discovered: {{ formatDate(exp.discovered_at) }}
                    </p>
                  </div>

                  <!-- Actions -->
                  <ClientOnly>
                    <div class="flex items-center gap-1">
                      <UTooltip text="View Details">
                        <UButton
                          icon="i-lucide-eye"
                          variant="ghost"
                          color="neutral"
                          size="sm"
                          @click.stop="navigateTo(`/forensic-exports/${exp.id}`)"
                        />
                      </UTooltip>
                      <UTooltip text="Verify Export">
                        <UButton
                          icon="i-lucide-shield-check"
                          variant="ghost"
                          color="neutral"
                          size="sm"
                          @click.stop="verifyExport(exp.id)"
                        />
                      </UTooltip>
                      <UDropdownMenu
                        :items="[
                          [
                            { label: 'View Details', icon: 'i-lucide-eye', click: () => navigateTo(`/forensic-exports/${exp.id}`) },
                            { label: 'Verify', icon: 'i-lucide-shield-check', click: () => verifyExport(exp.id) }
                          ],
                          [
                            { label: 'Delete Record', icon: 'i-lucide-trash', color: 'error', click: () => deleteExport(exp.id) }
                          ]
                        ]"
                      >
                        <UButton
                          icon="i-lucide-more-vertical"
                          variant="ghost"
                          color="neutral"
                          size="sm"
                          @click.stop
                        />
                      </UDropdownMenu>
                    </div>
                  </ClientOnly>
                </div>
              </div>
            </div>
          </UCard>
        </div>

        <!-- Empty State -->
        <div v-if="filteredExports.length === 0 && !loadingExports" class="text-center py-24">
          <div class="inline-flex items-center justify-center size-32 bg-gradient-to-br from-primary/20 to-primary/5 rounded-full mb-8">
            <UIcon name="i-lucide-database" class="size-16 text-primary/50" />
          </div>
          <h3 class="text-3xl font-bold mb-4">
            {{ searchQuery || selectedCase || selectedStatus ? 'No exports found' : 'No forensic exports yet' }}
          </h3>
          <p class="text-lg text-muted mb-8 max-w-md mx-auto">
            {{ searchQuery || selectedCase || selectedStatus
              ? 'Try adjusting your filters to see more results'
              : 'Scan a location to discover and register forensic exports from AXIOM'
            }}
          </p>
          <UButton
            v-if="!searchQuery && !selectedCase && !selectedStatus"
            label="Scan Location"
            icon="i-lucide-scan"
            color="primary"
            size="xl"
            @click="showScanModal = true"
          />
          <UButton
            v-else
            label="Clear Filters"
            icon="i-lucide-x"
            color="neutral"
            size="xl"
            @click="searchQuery = ''; selectedCase = null; selectedStatus = null"
          />
        </div>

        <!-- Loading State -->
        <div v-if="loadingExports" class="text-center py-24">
          <UIcon name="i-lucide-loader-2" class="size-16 text-primary animate-spin mb-4" />
          <p class="text-lg text-muted">Loading forensic exports...</p>
        </div>
      </div>
    </template>
  </UDashboardPanel>

  <!-- Scan Location Modal -->
  <ClientOnly>
    <UModal
      v-model:open="showScanModal"
      title="Scan Location for Forensic Exports"
      description="Recursively scan a directory for AXIOM forensic export folders"
      :ui="{ content: 'max-w-3xl' }"
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

            <UFormField label="Associate exports with case" name="case" required>
              <USelectMenu
                v-model="selectedCaseForScan"
                :items="caseOptions.filter(c => c.value !== null)"
                placeholder="Select a case..."
                size="lg"
                value-key="value"
              />
            </UFormField>
          </UCard>

          <!-- Path Input -->
          <UCard>
            <template #header>
              <div class="flex items-center gap-3">
                <div class="p-2 bg-primary/10 rounded-lg">
                  <UIcon name="i-lucide-hard-drive" class="size-5 text-primary" />
                </div>
                <h3 class="font-semibold text-lg">Scan Path</h3>
              </div>
            </template>

            <div class="space-y-4">
              <!-- Quick Path Selection -->
              <div>
                <label class="text-sm font-medium text-highlighted mb-2 block">Quick Select</label>
                <div class="flex flex-wrap gap-2">
                  <UButton
                    v-for="path in commonPaths"
                    :key="path.value"
                    :label="path.label"
                    :icon="path.icon"
                    size="sm"
                    :color="scanPath === path.value ? 'primary' : 'neutral'"
                    :variant="scanPath === path.value ? 'soft' : 'outline'"
                    @click="scanPath = path.value"
                  />
                </div>
              </div>

              <!-- Manual Path Input -->
              <UFormField
                label="Or enter custom path"
                name="path"
                required
                description="The path will be accessed inside the Docker container at /data/forensic-exports (configured via FORENSIC_EXPORTS_PATH env variable)"
              >
                <div class="flex gap-2">
                  <UInput
                    v-model="scanPath"
                    icon="i-lucide-folder-open"
                    placeholder="/data/forensic-exports"
                    size="lg"
                    class="flex-1"
                  />
                  <UButton
                    label="Browse"
                    icon="i-lucide-folder-search"
                    color="neutral"
                    variant="outline"
                    size="lg"
                    @click="openDirectoryPicker"
                  />
                </div>
              </UFormField>

              <!-- Help Info -->
              <div class="p-4 bg-info/10 border border-info/20 rounded-lg">
                <div class="flex items-start gap-3">
                  <UIcon name="i-lucide-info" class="size-5 text-info flex-shrink-0 mt-0.5" />
                  <div class="text-sm text-muted">
                    <p class="font-medium text-highlighted mb-2">How it works:</p>
                    <ul class="space-y-1 list-disc list-inside">
                      <li>Your removable drive is mounted to <code class="px-1.5 py-0.5 bg-default rounded text-xs font-mono">/data/forensic-exports</code></li>
                      <li>Scans recursively for folders containing <code class="px-1.5 py-0.5 bg-default rounded text-xs font-mono">ExportSummary.json</code> and <code class="px-1.5 py-0.5 bg-default rounded text-xs font-mono">Report.html</code></li>
                      <li>Registers new exports and skips existing ones</li>
                      <li>Stops recursing once an export is found (performance optimization)</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </UCard>

          <!-- Scan Results -->
          <UCard v-if="scanResults">
            <template #header>
              <div class="flex items-center gap-3">
                <div class="p-2 bg-success/10 rounded-lg">
                  <UIcon name="i-lucide-check-circle" class="size-5 text-success" />
                </div>
                <h3 class="font-semibold text-lg">Scan Results</h3>
              </div>
            </template>

            <div class="space-y-4">
              <!-- Found -->
              <div v-if="scanResults.found?.length > 0">
                <p class="font-medium text-success mb-2">
                  <UIcon name="i-lucide-plus-circle" class="size-4 inline mr-1" />
                  Found {{ scanResults.found.length }} new export(s)
                </p>
                <div class="space-y-2">
                  <div
                    v-for="item in scanResults.found"
                    :key="item.id"
                    class="p-3 bg-success/10 border border-success/20 rounded-lg text-sm"
                  >
                    <p class="font-medium">{{ item.name }}</p>
                    <p class="text-xs text-muted mt-1">{{ item.path }}</p>
                  </div>
                </div>
              </div>

              <!-- Existing -->
              <div v-if="scanResults.existing?.length > 0">
                <p class="font-medium text-info mb-2">
                  <UIcon name="i-lucide-check" class="size-4 inline mr-1" />
                  Skipped {{ scanResults.existing.length }} existing export(s)
                </p>
                <div class="max-h-32 overflow-y-auto space-y-1">
                  <div
                    v-for="(path, idx) in scanResults.existing"
                    :key="idx"
                    class="p-2 bg-info/10 border border-info/20 rounded text-xs text-muted"
                  >
                    {{ path }}
                  </div>
                </div>
              </div>

              <!-- Errors -->
              <div v-if="scanResults.errors?.length > 0">
                <p class="font-medium text-error mb-2">
                  <UIcon name="i-lucide-alert-circle" class="size-4 inline mr-1" />
                  {{ scanResults.errors.length }} error(s)
                </p>
                <div class="max-h-32 overflow-y-auto space-y-2">
                  <div
                    v-for="(err, idx) in scanResults.errors"
                    :key="idx"
                    class="p-3 bg-error/10 border border-error/20 rounded-lg text-sm"
                  >
                    <p class="font-medium text-error">{{ err.error }}</p>
                    <p class="text-xs text-muted mt-1">{{ err.path }}</p>
                  </div>
                </div>
              </div>

              <!-- No results -->
              <div v-if="!scanResults.found?.length && !scanResults.existing?.length && !scanResults.errors?.length">
                <p class="text-muted text-center py-4">No forensic exports found in the scanned location</p>
              </div>
            </div>
          </UCard>
        </div>
      </template>

      <template #footer>
        <div class="flex items-center justify-end gap-3">
          <UButton
            label="Close"
            color="neutral"
            variant="outline"
            @click="closeScanModal"
            :disabled="isScanning"
          />
          <UButton
            label="Start Scan"
            icon="i-lucide-scan"
            color="primary"
            :disabled="!selectedCaseForScan || !scanPath || isScanning"
            :loading="isScanning"
            @click="scanLocation"
          />
        </div>
      </template>
    </UModal>
  </ClientOnly>
</template>
