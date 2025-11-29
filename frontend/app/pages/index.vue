<script setup lang="ts">
const { cases, listCases } = useCases()
const { documents, listDocuments } = useDocuments()

const showCreateCaseModal = ref(false)

// Fetch data
await Promise.all([listCases(), listDocuments()])

// Stats computed from Firestore data
const stats = computed(() => {
  const totalCases = cases.value?.length || 0
  const activeCases = (cases.value || []).filter(c => c.status === 'active').length || 0
  const totalDocs = documents.value?.length || 0
  const totalStorage = documents.value?.reduce((sum, d) => sum + (d.fileSize || 0), 0) || 0
  return { totalCases, activeCases, totalDocs, totalStorage }
})

const recentCases = computed(() => (cases.value || []).slice(0, 5))
const recentDocuments = computed(() => (documents.value || []).slice(0, 8))

function formatBytes(bytes: number) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function formatDate(date: any) {
  const d = date?.toDate?.() || new Date(date)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const statusColors: Record<string, string> = {
  active: 'success',
  staging: 'warning',
  unloaded: 'neutral',
  archived: 'neutral'
}
</script>

<template>
  <UDashboardPanel id="home">
    <template #header>
      <UDashboardNavbar title="Dashboard">
        <template #trailing>
          <UButton label="New Case" icon="i-lucide-plus" @click="showCreateCaseModal = true" />
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <div class="p-6 space-y-6 max-w-7xl mx-auto">
        <!-- Welcome -->
        <div>
          <h1 class="text-2xl font-bold">Welcome to LegalEase</h1>
          <p class="text-muted mt-1">AI-powered legal document management</p>
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-folder" class="size-8 text-primary" />
              <div>
                <p class="text-2xl font-bold">{{ stats.totalCases }}</p>
                <p class="text-sm text-muted">Cases</p>
              </div>
            </div>
          </UCard>

          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-briefcase" class="size-8 text-success" />
              <div>
                <p class="text-2xl font-bold">{{ stats.activeCases }}</p>
                <p class="text-sm text-muted">Active</p>
              </div>
            </div>
          </UCard>

          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-file-text" class="size-8 text-info" />
              <div>
                <p class="text-2xl font-bold">{{ stats.totalDocs }}</p>
                <p class="text-sm text-muted">Documents</p>
              </div>
            </div>
          </UCard>

          <UCard :ui="{ body: 'p-4' }">
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-hard-drive" class="size-8 text-warning" />
              <div>
                <p class="text-2xl font-bold">{{ formatBytes(stats.totalStorage) }}</p>
                <p class="text-sm text-muted">Storage</p>
              </div>
            </div>
          </UCard>
        </div>

        <!-- Main Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- Recent Documents -->
          <div class="lg:col-span-2">
            <UCard>
              <template #header>
                <div class="flex items-center justify-between">
                  <h3 class="font-semibold">Recent Documents</h3>
                  <UButton variant="ghost" color="neutral" size="sm" to="/documents">View All</UButton>
                </div>
              </template>

              <div v-if="recentDocuments && recentDocuments.length" class="space-y-2">
                <NuxtLink
                  v-for="doc in recentDocuments"
                  :key="doc.id"
                  :to="`/documents/${doc.id}`"
                  class="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <UIcon name="i-lucide-file-text" class="size-5 text-muted" />
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium truncate">{{ doc.title || doc.filename }}</p>
                    <p class="text-xs text-muted">{{ formatBytes(doc.fileSize) }}</p>
                  </div>
                  <span class="text-xs text-muted">{{ formatDate(doc.createdAt) }}</span>
                </NuxtLink>
              </div>

              <div v-else class="text-center py-8">
                <UIcon name="i-lucide-file-text" class="size-12 text-muted mx-auto mb-3 opacity-50" />
                <p class="text-sm text-muted">No documents yet</p>
              </div>
            </UCard>
          </div>

          <!-- Recent Cases -->
          <div>
            <UCard>
              <template #header>
                <div class="flex items-center justify-between">
                  <h3 class="font-semibold">Recent Cases</h3>
                  <UButton variant="ghost" color="neutral" size="sm" to="/cases">View All</UButton>
                </div>
              </template>

              <div v-if="recentCases && recentCases.length" class="space-y-2">
                <NuxtLink
                  v-for="c in recentCases"
                  :key="c.id"
                  :to="`/cases/${c.id}`"
                  class="block p-3 rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div class="flex items-start gap-2">
                    <UIcon name="i-lucide-folder" class="size-4 text-muted mt-0.5" />
                    <div class="flex-1 min-w-0">
                      <p class="text-sm font-medium truncate">{{ c.name }}</p>
                      <p class="text-xs text-muted truncate">{{ c.caseNumber }}</p>
                      <div class="flex items-center gap-2 mt-1">
                        <UBadge :color="statusColors[c.status]" variant="subtle" size="xs">
                          {{ c.status }}
                        </UBadge>
                        <span class="text-xs text-muted">{{ c.documentCount || 0 }} docs</span>
                      </div>
                    </div>
                  </div>
                </NuxtLink>
              </div>

              <div v-else class="text-center py-8">
                <UIcon name="i-lucide-folder" class="size-12 text-muted mx-auto mb-3 opacity-50" />
                <p class="text-sm text-muted mb-3">No cases yet</p>
                <UButton size="sm" @click="showCreateCaseModal = true">Create Case</UButton>
              </div>
            </UCard>

            <!-- Quick Links -->
            <UCard class="mt-4">
              <template #header>
                <h3 class="font-semibold">Quick Links</h3>
              </template>

              <div class="space-y-2">
                <NuxtLink to="/search" class="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors">
                  <div class="p-2 bg-primary/10 rounded">
                    <UIcon name="i-lucide-search" class="size-4 text-primary" />
                  </div>
                  <div>
                    <p class="text-sm font-medium">Search</p>
                    <p class="text-xs text-muted">Find documents</p>
                  </div>
                </NuxtLink>

                <NuxtLink to="/cases" class="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors">
                  <div class="p-2 bg-success/10 rounded">
                    <UIcon name="i-lucide-folder" class="size-4 text-success" />
                  </div>
                  <div>
                    <p class="text-sm font-medium">Cases</p>
                    <p class="text-xs text-muted">Manage cases</p>
                  </div>
                </NuxtLink>
              </div>
            </UCard>
          </div>
        </div>
      </div>
    </template>
  </UDashboardPanel>

  <ClientOnly>
    <LazyModalsCreateCaseModal v-if="showCreateCaseModal" v-model:open="showCreateCaseModal" />
  </ClientOnly>
</template>
