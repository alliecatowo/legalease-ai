<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

definePageMeta({
  layout: 'default'
})

const route = useRoute()
const router = useRouter()
const api = useApi()
const toast = useToast()

const exportId = computed(() => parseInt(route.params.id as string))

// State
const exportData = ref<any>(null)
const isLoading = ref(true)
const error = ref<string | null>(null)
const isVerifying = ref(false)
const showDeleteConfirm = ref(false)
const isDeleting = ref(false)

// Load export data
async function loadExport() {
  isLoading.value = true
  error.value = null

  try {
    const response = await api.forensicExports.get(exportId.value)
    exportData.value = response
  } catch (err: any) {
    error.value = err.message || 'Failed to load export'
    console.error('Error loading export:', err)
  } finally {
    isLoading.value = false
  }
}

// Verify export exists
async function verifyExport() {
  if (!exportData.value) return

  isVerifying.value = true

  try {
    const response = await api.forensicExports.verify(exportId.value)

    if (response.exists) {
      toast.add({
        title: 'Export Verified',
        description: 'The export folder exists on disk',
        color: 'success'
      })
      // Update last verified timestamp
      exportData.value.last_verified_at = response.verified_at
    } else {
      toast.add({
        title: 'Export Not Found',
        description: 'The export folder no longer exists on disk',
        color: 'error'
      })
    }
  } catch (err: any) {
    toast.add({
      title: 'Verification Failed',
      description: err.message || 'Unable to verify export',
      color: 'error'
    })
  } finally {
    isVerifying.value = false
  }
}

// Delete export record
async function deleteExport() {
  if (!exportData.value) return

  isDeleting.value = true

  try {
    await api.forensicExports.delete(exportId.value)
    toast.add({
      title: 'Export Record Deleted',
      description: 'The database record has been removed (files remain on disk)',
      color: 'success'
    })
    router.push('/forensic-exports')
  } catch (err: any) {
    toast.add({
      title: 'Delete Failed',
      description: err.message || 'Unable to delete export',
      color: 'error'
    })
  } finally {
    isDeleting.value = false
    showDeleteConfirm.value = false
  }
}

// Utility functions
function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDateShort(dateStr: string | null): string {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

function getRelativeTime(dateStr: string | null): string {
  if (!dateStr) return 'Never'
  const date = new Date(dateStr)
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diffInSeconds < 60) return 'just now'
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} days ago`

  return formatDateShort(dateStr)
}

// Computed properties
const statusColor = computed(() => {
  const status = exportData.value?.export_status?.toLowerCase()
  if (status === 'completed') return 'success'
  if (status === 'partial') return 'warning'
  if (status === 'failed') return 'error'
  return 'neutral'
})

const hasProblems = computed(() => {
  return exportData.value?.problems_json && exportData.value.problems_json.length > 0
})

const exportOptionsTableColumns = [
  { accessorKey: 'name', header: 'Option' },
  { accessorKey: 'value', header: 'Value' }
]

onMounted(() => {
  loadExport()
})
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar :title="exportData?.folder_name || 'Forensic Export'">
        <template #leading>
          <UButton
            icon="i-lucide-arrow-left"
            color="neutral"
            variant="ghost"
            @click="router.push('/forensic-exports')"
          />
        </template>
        <template #trailing>
          <div v-if="exportData" class="flex items-center gap-2">
            <UButton
              label="Verify Export"
              icon="i-lucide-check-circle"
              color="success"
              variant="soft"
              :loading="isVerifying"
              @click="verifyExport"
            />
            <UButton
              label="Delete Record"
              icon="i-lucide-trash-2"
              color="error"
              variant="soft"
              @click="showDeleteConfirm = true"
            />
          </div>
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <div class="max-w-7xl mx-auto space-y-6">
        <!-- Loading State -->
        <div v-if="isLoading" class="flex items-center justify-center py-20">
          <div class="text-center space-y-4">
            <UIcon name="i-lucide-loader-circle" class="size-12 text-primary animate-spin mx-auto" />
            <div>
              <h3 class="text-lg font-semibold">Loading export...</h3>
              <p class="text-sm text-muted">Please wait while we fetch the export details</p>
            </div>
          </div>
        </div>

        <!-- Error State -->
        <div v-else-if="error || !exportData" class="flex items-center justify-center h-full">
          <UCard class="max-w-md">
            <div class="text-center space-y-4">
              <UIcon name="i-lucide-alert-circle" class="size-16 text-error mx-auto" />
              <div>
                <h3 class="text-xl font-bold text-highlighted mb-2">Error Loading Export</h3>
                <p class="text-muted">{{ error || 'Export not found' }}</p>
              </div>
              <UButton
                label="Back to Exports"
                icon="i-lucide-arrow-left"
                color="primary"
                @click="router.push('/forensic-exports')"
              />
            </div>
          </UCard>
        </div>

        <!-- Export Content -->
        <template v-else-if="exportData">
          <!-- Hero Section with Key Stats -->
          <div class="bg-gradient-to-br from-primary/10 via-secondary/5 to-transparent rounded-xl p-8 border border-default">
            <div class="flex items-start justify-between gap-6 flex-wrap mb-6">
              <div class="flex items-start gap-4 flex-1 min-w-0">
                <div class="p-4 bg-primary/20 rounded-xl">
                  <UIcon name="i-lucide-hard-drive" class="size-10 text-primary" />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-3 flex-wrap mb-2">
                    <h1 class="text-3xl font-bold text-highlighted">{{ exportData.folder_name || 'Unknown Export' }}</h1>
                    <UBadge
                      v-if="exportData.export_status"
                      :label="exportData.export_status"
                      :color="statusColor"
                      variant="soft"
                      size="lg"
                      class="capitalize"
                    />
                  </div>
                  <div class="flex items-center gap-4 text-muted mb-3 flex-wrap">
                    <div v-if="exportData.export_uuid" class="flex items-center gap-2">
                      <UIcon name="i-lucide-fingerprint" class="size-4" />
                      <span class="font-mono text-xs">{{ exportData.export_uuid }}</span>
                    </div>
                  </div>
                  <p class="text-base text-muted max-w-3xl">
                    Forensic export discovered {{ getRelativeTime(exportData.discovered_at) }}
                    <span v-if="exportData.last_verified_at"> • Last verified {{ getRelativeTime(exportData.last_verified_at) }}</span>
                  </p>
                </div>
              </div>
            </div>

            <!-- Key Stats Grid -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <UCard :ui="{ body: 'p-4 space-y-2' }">
                <div class="flex items-center justify-between">
                  <UIcon name="i-lucide-database" class="size-8 text-primary" />
                </div>
                <div>
                  <p class="text-sm text-muted">Total Records</p>
                  <p class="text-2xl font-bold">{{ exportData.total_records?.toLocaleString() || 'N/A' }}</p>
                </div>
              </UCard>

              <UCard :ui="{ body: 'p-4 space-y-2' }">
                <div class="flex items-center justify-between">
                  <UIcon name="i-lucide-file-output" class="size-8 text-info" />
                </div>
                <div>
                  <p class="text-sm text-muted">Exported Records</p>
                  <p class="text-2xl font-bold">{{ exportData.exported_records?.toLocaleString() || 'N/A' }}</p>
                </div>
              </UCard>

              <UCard :ui="{ body: 'p-4 space-y-2' }">
                <div class="flex items-center justify-between">
                  <UIcon name="i-lucide-paperclip" class="size-8 text-success" />
                </div>
                <div>
                  <p class="text-sm text-muted">Attachments</p>
                  <p class="text-2xl font-bold">{{ exportData.num_attachments?.toLocaleString() || '0' }}</p>
                </div>
              </UCard>

              <UCard :ui="{ body: 'p-4 space-y-2' }">
                <div class="flex items-center justify-between">
                  <UIcon name="i-lucide-hard-drive" class="size-8 text-warning" />
                </div>
                <div>
                  <p class="text-sm text-muted">Total Size</p>
                  <p class="text-2xl font-bold">{{ formatBytes(exportData.size_bytes) }}</p>
                </div>
              </UCard>
            </div>
          </div>

          <!-- Main Content Grid -->
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Left Column - Export Details -->
            <div class="lg:col-span-2 space-y-6">
              <!-- Export Information -->
              <UCard>
                <template #header>
                  <h2 class="text-xl font-semibold text-highlighted flex items-center gap-2">
                    <UIcon name="i-lucide-info" class="size-5" />
                    Export Information
                  </h2>
                </template>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div class="space-y-1">
                    <div class="flex items-center gap-2 text-sm text-muted">
                      <UIcon name="i-lucide-tag" class="size-4" />
                      <span>AXIOM Version</span>
                    </div>
                    <p class="font-medium text-highlighted">{{ exportData.axiom_version || 'N/A' }}</p>
                  </div>

                  <div class="space-y-1">
                    <div class="flex items-center gap-2 text-sm text-muted">
                      <UIcon name="i-lucide-clock" class="size-4" />
                      <span>Duration</span>
                    </div>
                    <p class="font-medium text-highlighted">{{ exportData.export_duration || 'N/A' }}</p>
                  </div>

                  <div class="space-y-1">
                    <div class="flex items-center gap-2 text-sm text-muted">
                      <UIcon name="i-lucide-calendar-plus" class="size-4" />
                      <span>Export Started</span>
                    </div>
                    <p class="font-medium text-highlighted">{{ formatDate(exportData.export_start_date) }}</p>
                  </div>

                  <div class="space-y-1">
                    <div class="flex items-center gap-2 text-sm text-muted">
                      <UIcon name="i-lucide-calendar-check" class="size-4" />
                      <span>Export Completed</span>
                    </div>
                    <p class="font-medium text-highlighted">{{ formatDate(exportData.export_end_date) }}</p>
                  </div>

                  <div v-if="exportData.case_directory" class="space-y-1 sm:col-span-2">
                    <div class="flex items-center gap-2 text-sm text-muted">
                      <UIcon name="i-lucide-folder" class="size-4" />
                      <span>Case Directory</span>
                    </div>
                    <p class="font-medium text-highlighted font-mono text-sm break-all">{{ exportData.case_directory }}</p>
                  </div>

                  <div v-if="exportData.case_storage_location" class="space-y-1 sm:col-span-2">
                    <div class="flex items-center gap-2 text-sm text-muted">
                      <UIcon name="i-lucide-database" class="size-4" />
                      <span>Storage Location</span>
                    </div>
                    <p class="font-medium text-highlighted font-mono text-sm break-all">{{ exportData.case_storage_location }}</p>
                  </div>
                </div>
              </UCard>

              <!-- Export Options Table -->
              <UCard v-if="exportData.export_options_json && exportData.export_options_json.length > 0">
                <template #header>
                  <h2 class="text-xl font-semibold text-highlighted flex items-center gap-2">
                    <UIcon name="i-lucide-settings" class="size-5" />
                    Export Options
                    <UBadge :label="String(exportData.export_options_json.length)" variant="soft" color="primary" />
                  </h2>
                </template>

                <UTable
                  :columns="exportOptionsTableColumns"
                  :data="exportData.export_options_json"
                  :ui="{
                    td: { base: 'max-w-0 truncate' }
                  }"
                >
                  <template #name-data="{ row }">
                    <span class="font-medium text-highlighted">{{ row.name }}</span>
                  </template>
                  <template #value-data="{ row }">
                    <span class="text-muted font-mono text-sm">{{ row.value }}</span>
                  </template>
                </UTable>
              </UCard>

              <!-- Summary Fields -->
              <UCard v-if="exportData.summary_json && exportData.summary_json.length > 0">
                <template #header>
                  <h2 class="text-xl font-semibold text-highlighted flex items-center gap-2">
                    <UIcon name="i-lucide-list" class="size-5" />
                    Export Summary
                    <UBadge :label="String(exportData.summary_json.length)" variant="soft" color="primary" />
                  </h2>
                </template>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div
                    v-for="(field, idx) in exportData.summary_json"
                    :key="idx"
                    class="p-3 bg-muted/5 rounded-lg"
                  >
                    <p class="text-xs text-muted mb-1">{{ field.name }}</p>
                    <p class="font-medium text-highlighted break-words">{{ field.value }}</p>
                  </div>
                </div>
              </UCard>

              <!-- Problems Section -->
              <UCard v-if="hasProblems">
                <template #header>
                  <h2 class="text-xl font-semibold text-highlighted flex items-center gap-2">
                    <UIcon name="i-lucide-alert-triangle" class="size-5 text-error" />
                    Problems
                    <UBadge :label="String(exportData.problems_json.length)" variant="soft" color="error" />
                  </h2>
                </template>

                <div class="space-y-3">
                  <UAlert
                    v-for="(problem, idx) in exportData.problems_json"
                    :key="idx"
                    color="error"
                    variant="soft"
                    icon="i-lucide-alert-circle"
                    :title="problem.title || `Problem ${idx + 1}`"
                    :description="problem.description || JSON.stringify(problem)"
                  />
                </div>
              </UCard>
            </div>

            <!-- Right Column - System Information -->
            <div class="space-y-6">
              <!-- System Information -->
              <UCard>
                <template #header>
                  <h2 class="text-xl font-semibold text-highlighted flex items-center gap-2">
                    <UIcon name="i-lucide-server" class="size-5" />
                    System Information
                  </h2>
                </template>

                <div class="space-y-4">
                  <div>
                    <p class="text-xs text-muted mb-2">Folder Path</p>
                    <div class="p-3 bg-muted/10 rounded-lg">
                      <p class="font-mono text-sm text-highlighted break-all">{{ exportData.folder_path }}</p>
                    </div>
                  </div>

                  <div>
                    <p class="text-xs text-muted mb-1">Discovered</p>
                    <p class="font-medium text-highlighted">{{ formatDate(exportData.discovered_at) }}</p>
                    <p class="text-xs text-muted mt-1">{{ getRelativeTime(exportData.discovered_at) }}</p>
                  </div>

                  <div>
                    <p class="text-xs text-muted mb-1">Last Verified</p>
                    <p class="font-medium text-highlighted">{{ formatDate(exportData.last_verified_at) }}</p>
                    <p class="text-xs text-muted mt-1">{{ getRelativeTime(exportData.last_verified_at) }}</p>
                  </div>

                  <div class="pt-4 border-t border-default">
                    <UButton
                      label="Verify Export Exists"
                      icon="i-lucide-check-circle"
                      color="success"
                      variant="outline"
                      block
                      :loading="isVerifying"
                      @click="verifyExport"
                    />
                  </div>
                </div>
              </UCard>

              <!-- Quick Actions -->
              <UCard>
                <template #header>
                  <h2 class="text-xl font-semibold text-highlighted flex items-center gap-2">
                    <UIcon name="i-lucide-zap" class="size-5" />
                    Quick Actions
                  </h2>
                </template>

                <div class="space-y-2">
                  <UButton
                    label="View in File Browser"
                    icon="i-lucide-folder-open"
                    color="neutral"
                    variant="outline"
                    block
                    disabled
                  />
                  <UButton
                    label="Open Report.html"
                    icon="i-lucide-file-text"
                    color="neutral"
                    variant="outline"
                    block
                    disabled
                  />
                  <UButton
                    label="Delete Record"
                    icon="i-lucide-trash-2"
                    color="error"
                    variant="outline"
                    block
                    @click="showDeleteConfirm = true"
                  />
                </div>
              </UCard>

              <!-- Export Metadata -->
              <UCard v-if="exportData.export_uuid">
                <template #header>
                  <h2 class="text-xl font-semibold text-highlighted flex items-center gap-2">
                    <UIcon name="i-lucide-file-json" class="size-5" />
                    Metadata
                  </h2>
                </template>

                <div class="space-y-3">
                  <div>
                    <p class="text-xs text-muted mb-1">Export UUID</p>
                    <div class="p-2 bg-muted/10 rounded font-mono text-xs break-all">
                      {{ exportData.export_uuid }}
                    </div>
                  </div>
                  <div>
                    <p class="text-xs text-muted mb-1">Database ID</p>
                    <p class="font-medium text-highlighted">{{ exportData.id }}</p>
                  </div>
                  <div>
                    <p class="text-xs text-muted mb-1">Case ID</p>
                    <p class="font-medium text-highlighted">{{ exportData.case_id }}</p>
                  </div>
                </div>
              </UCard>
            </div>
          </div>
        </template>
      </div>
    </template>
  </UDashboardPanel>

  <!-- Delete Confirmation Modal -->
  <ClientOnly>
    <UModal
      v-model:open="showDeleteConfirm"
      title="Delete Export Record"
      icon="i-lucide-trash-2"
    >
      <template #body>
        <div class="space-y-4">
          <p class="text-muted">
            Are you sure you want to delete this export record? This action cannot be undone.
          </p>

          <UAlert
            color="warning"
            variant="soft"
            icon="i-lucide-alert-triangle"
            title="Files will remain on disk"
            description="Deleting this record only removes it from the database. The export folder and all its files will remain on your filesystem."
          />

          <div class="p-3 bg-muted/10 rounded-lg">
            <p class="text-xs text-muted mb-1">Export Folder</p>
            <p class="font-mono text-sm break-all">{{ exportData?.folder_path }}</p>
          </div>
        </div>
      </template>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton
            label="Cancel"
            color="neutral"
            variant="ghost"
            @click="showDeleteConfirm = false"
          />
          <UButton
            label="Delete Record"
            icon="i-lucide-trash-2"
            color="error"
            :loading="isDeleting"
            @click="deleteExport"
          />
        </div>
      </template>
    </UModal>
  </ClientOnly>
</template>
