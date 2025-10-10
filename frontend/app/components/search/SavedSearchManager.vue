<script setup lang="ts">
import { ref } from 'vue'

interface SavedSearch {
  id: string
  name: string
  query: string
  filters: Record<string, any>
  createdAt: string
  alertsEnabled: boolean
  resultCount?: number
}

const savedSearches = ref<SavedSearch[]>([
  {
    id: '1',
    name: 'IBM Contracts 2024',
    query: 'contract IBM 2024',
    filters: { documentTypes: ['contract'], parties: ['IBM'] },
    createdAt: '2024-01-15',
    alertsEnabled: true,
    resultCount: 234
  },
  {
    id: '2',
    name: 'Patent Litigation CA',
    query: 'patent litigation',
    filters: { jurisdictions: ['ca'], documentTypes: ['court_filing'] },
    createdAt: '2024-01-10',
    alertsEnabled: false,
    resultCount: 156
  }
])

const showSaveModal = ref(false)
const showDeleteModal = ref(false)
const selectedSearch = ref<SavedSearch | null>(null)
const newSearchName = ref('')

const emit = defineEmits<{
  'apply': [search: SavedSearch]
  'save': [name: string]
}>()

function applySearch(search: SavedSearch) {
  emit('apply', search)
}

function saveCurrentSearch() {
  showSaveModal.value = true
}

function confirmSave() {
  if (newSearchName.value.trim()) {
    emit('save', newSearchName.value)
    showSaveModal.value = false
    newSearchName.value = ''
  }
}

function deleteSearch(search: SavedSearch) {
  selectedSearch.value = search
  showDeleteModal.value = true
}

function confirmDelete() {
  if (selectedSearch.value) {
    savedSearches.value = savedSearches.value.filter(s => s.id !== selectedSearch.value!.id)
    // TODO: Call API to delete saved search
    showDeleteModal.value = false
    selectedSearch.value = null
  }
}

function toggleAlerts(search: SavedSearch) {
  search.alertsEnabled = !search.alertsEnabled
  // TODO: Call API to update alert settings
}
</script>

<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-bookmark" class="size-5 text-primary" />
        <h3 class="font-semibold text-highlighted">
          Saved Searches
        </h3>
        <UBadge :label="String(savedSearches.length)" size="sm" variant="soft" />
      </div>
      <UButton
        label="Save Current"
        icon="i-lucide-plus"
        color="primary"
        size="sm"
        @click="saveCurrentSearch"
      />
    </div>

    <!-- Saved Searches List -->
    <div v-if="savedSearches.length" class="space-y-2">
      <UCard
        v-for="search in savedSearches"
        :key="search.id"
        class="hover:bg-elevated/50 transition-colors cursor-pointer"
        :ui="{ body: 'p-3' }"
        @click="applySearch(search)"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <h4 class="font-medium text-highlighted truncate">
                {{ search.name }}
              </h4>
              <UBadge
                v-if="search.alertsEnabled"
                label="Alerts On"
                color="success"
                variant="soft"
                size="xs"
              >
                <template #leading>
                  <UIcon name="i-lucide-bell" class="size-3" />
                </template>
              </UBadge>
            </div>
            <p class="text-sm text-dimmed truncate mb-2">
              {{ search.query }}
            </p>
            <div class="flex items-center gap-3 text-xs text-muted">
              <span>{{ new Date(search.createdAt).toLocaleDateString() }}</span>
              <span v-if="search.resultCount">•</span>
              <span v-if="search.resultCount">{{ search.resultCount }} results</span>
            </div>
          </div>
          <div class="flex items-center gap-1">
            <UTooltip :text="search.alertsEnabled ? 'Disable alerts' : 'Enable alerts'">
              <UButton
                :icon="search.alertsEnabled ? 'i-lucide-bell' : 'i-lucide-bell-off'"
                :color="search.alertsEnabled ? 'success' : 'neutral'"
                variant="ghost"
                size="sm"
                @click.stop="toggleAlerts(search)"
              />
            </UTooltip>
            <UTooltip text="Delete search">
              <UButton
                icon="i-lucide-trash-2"
                color="error"
                variant="ghost"
                size="sm"
                @click.stop="deleteSearch(search)"
              />
            </UTooltip>
          </div>
        </div>
      </UCard>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-8">
      <UIcon name="i-lucide-bookmark-x" class="size-12 text-muted mx-auto mb-3 opacity-50" />
      <h4 class="text-sm font-medium text-highlighted mb-1">
        No saved searches yet
      </h4>
      <p class="text-sm text-muted mb-4">
        Save searches to quickly access them later
      </p>
      <UButton
        label="Save Your First Search"
        icon="i-lucide-plus"
        color="primary"
        size="sm"
        @click="saveCurrentSearch"
      />
    </div>

    <!-- Save Modal -->
    <UModal v-model:open="showSaveModal" title="Save Search">
      <template #body>
        <UFormField label="Search Name" name="name" required>
          <UInput
            v-model="newSearchName"
            placeholder="e.g., IBM Contracts 2024"
            autofocus
          />
        </UFormField>
      </template>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <UButton
            label="Cancel"
            color="neutral"
            variant="outline"
            @click="showSaveModal = false"
          />
          <UButton
            label="Save"
            color="primary"
            :disabled="!newSearchName.trim()"
            @click="confirmSave"
          />
        </div>
      </template>
    </UModal>

    <!-- Delete Confirmation Modal -->
    <UModal v-model:open="showDeleteModal" title="Delete Saved Search">
      <template #body>
        <p class="text-default">
          Are you sure you want to delete <strong class="text-highlighted">{{ selectedSearch?.name }}</strong>?
          This action cannot be undone.
        </p>
      </template>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <UButton
            label="Cancel"
            color="neutral"
            variant="outline"
            @click="showDeleteModal = false"
          />
          <UButton
            label="Delete"
            color="error"
            icon="i-lucide-trash-2"
            @click="confirmDelete"
          />
        </div>
      </template>
    </UModal>
  </div>
</template>
