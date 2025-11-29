<script setup lang="ts">
definePageMeta({ layout: 'default' })

const route = useRoute()
const router = useRouter()
const toast = useToast()

const documentId = computed(() => route.params.id as string)
const { getDocument, deleteDocument } = useDocuments()
const { getCase } = useCases()

// Fetch document
const loading = ref(true)
const error = ref<string | null>(null)
const document = ref<any>(null)
const caseData = ref<any>(null)
const showDeleteModal = ref(false)
const isDeleting = ref(false)

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    document.value = await getDocument(documentId.value)
    if (!document.value) {
      error.value = 'Document not found'
      return
    }
    if (document.value.caseId) {
      caseData.value = await getCase(document.value.caseId)
    }
  } catch (err: any) {
    error.value = err?.message || 'Failed to load document'
  } finally {
    loading.value = false
  }
}

await fetchData()

// Helpers
function formatBytes(bytes: number) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function formatDate(date: any) {
  const d = date?.toDate?.() || new Date(date)
  return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
}

const statusColors: Record<string, string> = {
  uploading: 'warning',
  processing: 'info',
  indexed: 'success',
  completed: 'success',
  failed: 'error'
}

// Actions
async function handleDownload() {
  if (!document.value?.downloadUrl) return
  window.open(document.value.downloadUrl, '_blank')
}

async function handleDelete() {
  if (!document.value) return
  isDeleting.value = true
  try {
    await deleteDocument(documentId.value)
    toast.add({ title: 'Deleted', description: 'Document deleted successfully', color: 'success' })
    router.push('/documents')
  } catch (err) {
    toast.add({ title: 'Error', description: 'Failed to delete document', color: 'error' })
    isDeleting.value = false
  }
}

function handleShare() {
  navigator.clipboard.writeText(window.location.href)
  toast.add({ title: 'Copied', description: 'Link copied to clipboard', color: 'success' })
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar>
        <template #leading>
          <div class="flex items-center gap-3">
            <UButton icon="i-lucide-arrow-left" color="neutral" variant="ghost" @click="router.back()" />
            <USeparator orientation="vertical" class="h-6" />
            <UBreadcrumb :items="[
              { label: 'Documents', to: '/documents', icon: 'i-lucide-folder' },
              { label: document?.filename || 'Document', icon: 'i-lucide-file-text' }
            ]" />
          </div>
        </template>
        <template #trailing>
          <div class="flex items-center gap-2">
            <UButton icon="i-lucide-download" color="neutral" variant="ghost" @click="handleDownload" />
            <UButton icon="i-lucide-share" color="neutral" variant="ghost" @click="handleShare" />
            <UButton icon="i-lucide-trash" color="error" variant="ghost" @click="showDeleteModal = true" />
          </div>
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <UIcon name="i-lucide-loader-circle" class="size-12 text-primary animate-spin" />
      </div>

      <!-- Error -->
      <div v-else-if="error || !document" class="text-center py-20">
        <UIcon name="i-lucide-alert-circle" class="size-16 text-error mx-auto mb-4 opacity-50" />
        <h3 class="text-xl font-semibold mb-2">Document Not Found</h3>
        <p class="text-muted mb-6">{{ error || 'The document you are looking for does not exist.' }}</p>
        <UButton label="Back to Documents" icon="i-lucide-arrow-left" to="/documents" />
      </div>

      <!-- Document Content -->
      <div v-else class="max-w-5xl mx-auto p-6 space-y-6">
        <!-- Header -->
        <div class="flex items-start gap-6 p-6 bg-muted/10 rounded-xl border border-default">
          <div class="p-4 bg-primary/10 rounded-xl">
            <UIcon name="i-lucide-file-text" class="size-12 text-primary" />
          </div>
          <div class="flex-1 min-w-0">
            <h1 class="text-2xl font-bold mb-2">{{ document.title || document.filename }}</h1>
            <div class="flex items-center gap-3 flex-wrap">
              <UBadge :label="document.status || 'pending'" :color="statusColors[document.status] || 'neutral'" variant="soft" />
              <span class="text-sm text-muted">{{ formatBytes(document.fileSize) }}</span>
              <span class="text-sm text-muted">{{ document.mimeType }}</span>
            </div>
            <div v-if="caseData" class="mt-3 flex items-center gap-2 text-sm">
              <UIcon name="i-lucide-briefcase" class="size-4 text-muted" />
              <NuxtLink :to="`/cases/${caseData.id}`" class="text-primary hover:underline">
                {{ caseData.name }}
              </NuxtLink>
            </div>
          </div>
        </div>

        <!-- Info Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <UCard :ui="{ body: 'p-4' }">
            <p class="text-xs text-muted mb-1">Filename</p>
            <p class="font-medium truncate">{{ document.filename }}</p>
          </UCard>
          <UCard :ui="{ body: 'p-4' }">
            <p class="text-xs text-muted mb-1">Uploaded</p>
            <p class="font-medium">{{ formatDate(document.createdAt) }}</p>
          </UCard>
          <UCard :ui="{ body: 'p-4' }">
            <p class="text-xs text-muted mb-1">Type</p>
            <p class="font-medium capitalize">{{ document.documentType || 'General' }}</p>
          </UCard>
          <UCard :ui="{ body: 'p-4' }">
            <p class="text-xs text-muted mb-1">Size</p>
            <p class="font-medium">{{ formatBytes(document.fileSize) }}</p>
          </UCard>
        </div>

        <!-- Summary -->
        <UCard v-if="document.summary">
          <template #header>
            <h3 class="font-semibold">Summary</h3>
          </template>
          <p class="text-muted">{{ document.summary }}</p>
        </UCard>

        <!-- Actions -->
        <UCard>
          <template #header>
            <h3 class="font-semibold">Actions</h3>
          </template>
          <div class="space-y-2">
            <UButton label="Download Document" icon="i-lucide-download" block variant="soft" @click="handleDownload" />
            <UButton label="View in Case" icon="i-lucide-folder" block variant="outline" :to="`/cases/${document.caseId}`" v-if="document.caseId" />
          </div>
        </UCard>
      </div>
    </template>
  </UDashboardPanel>

  <!-- Delete Modal -->
  <ClientOnly>
    <UModal v-model:open="showDeleteModal" title="Delete Document">
      <template #body>
        <p class="text-muted">
          Are you sure you want to delete <strong>{{ document?.filename }}</strong>? This cannot be undone.
        </p>
      </template>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton label="Cancel" variant="ghost" @click="showDeleteModal = false" />
          <UButton label="Delete" color="error" :loading="isDeleting" @click="handleDelete" />
        </div>
      </template>
    </UModal>
  </ClientOnly>
</template>
