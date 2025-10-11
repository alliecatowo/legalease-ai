<script setup lang="ts">
interface Case {
  id: number
  name: string
  case_number: string
}
const props = defineProps<{
  selectedCases: number[]
  selectedDocumentTypes: string[]
  selectedChunkTypes?: string[]
  availableCases: Case[]
  isCompact?: boolean
  showChunkTypes?: boolean
}>()

const emit = defineEmits<{
  'update:selectedCases': [value: number[]]
  'update:selectedDocumentTypes': [value: string[]]
  'update:selectedChunkTypes': [value: string[]]
  'clear': []
}>()

const localCases = computed({
  get: () => {
    // Convert IDs back to objects for USelectMenu
    return props.availableCases.filter(c => props.selectedCases.includes(c.id))
  },
  set: (value) => {
    // Extract IDs from selected objects
    const ids = Array.isArray(value) ? value.map(c => c.id).filter(id => id != null) : []
    emit('update:selectedCases', ids)
  }
})

const localDocTypes = computed({
  get: () => props.selectedDocumentTypes,
  set: (value) => emit('update:selectedDocumentTypes', value)
})

const localChunkTypes = computed({
  get: () => props.selectedChunkTypes || [],
  set: (value) => emit('update:selectedChunkTypes', value)
})

const documentTypeOptions = [
  { value: 'contract', label: 'Contracts', icon: 'i-lucide-file-text' },
  { value: 'court_filing', label: 'Court Filings', icon: 'i-lucide-gavel' },
  { value: 'transcript', label: 'Transcripts', icon: 'i-lucide-mic' },
  { value: 'brief', label: 'Briefs', icon: 'i-lucide-file-pen' },
  { value: 'motion', label: 'Motions', icon: 'i-lucide-file-check' },
  { value: 'correspondence', label: 'Correspondence', icon: 'i-lucide-mail' }
]

const chunkTypeOptions = [
  { value: 'summary', label: 'Summaries', icon: 'i-lucide-sparkles' },
  { value: 'section', label: 'Sections', icon: 'i-lucide-layout' },
  { value: 'microblock', label: 'Microblocks', icon: 'i-lucide-component' },
  { value: 'paragraph', label: 'Paragraphs', icon: 'i-lucide-text' },
  { value: 'page', label: 'Pages', icon: 'i-lucide-file' }
]

const hasActiveFilters = computed(() =>
  props.selectedCases.length > 0 ||
  props.selectedDocumentTypes.length > 0 ||
  (props.selectedChunkTypes && props.selectedChunkTypes.length > 0)
)

const clearAllFilters = () => {
  emit('clear')
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-3" :class="{ 'gap-2': isCompact }">
    <!-- Case Filter -->
    <USelectMenu
      v-model="localCases"
      :items="availableCases"
      multiple
      by="id"
      :placeholder="selectedCases.length > 0 ? `${selectedCases.length} case${selectedCases.length > 1 ? 's' : ''}` : 'All Cases'"
      :ui="{
        trigger: 'inline-flex items-center gap-x-1.5',
        width: 'w-auto min-w-[160px]'
      }"
    >
      <template #label>
        <UIcon name="i-lucide-briefcase" class="size-4" />
        <span v-if="selectedCases.length === 0">All Cases</span>
        <span v-else>{{ selectedCases.length }} case{{ selectedCases.length > 1 ? 's' : '' }}</span>
      </template>

      <template #option="{ option }">
        <div class="flex flex-col">
          <span class="font-medium">{{ option.name }}</span>
          <span class="text-xs text-muted">{{ option.case_number }}</span>
        </div>
      </template>
    </USelectMenu>

    <!-- Document Type Filter -->
    <USelectMenu
      v-model="localDocTypes"
      :items="documentTypeOptions"
      multiple
      :placeholder="selectedDocumentTypes.length > 0 ? `${selectedDocumentTypes.length} type${selectedDocumentTypes.length > 1 ? 's' : ''}` : 'All Types'"
      :ui="{
        trigger: 'inline-flex items-center gap-x-1.5',
        width: 'w-auto min-w-[160px]'
      }"
      value-attribute="value"
    >
      <template #label>
        <UIcon name="i-lucide-file-type" class="size-4" />
        <span v-if="selectedDocumentTypes.length === 0">All Types</span>
        <span v-else>{{ selectedDocumentTypes.length }} type{{ selectedDocumentTypes.length > 1 ? 's' : '' }}</span>
      </template>

      <template #option="{ option }">
        <div class="flex items-center gap-2">
          <UIcon :name="option.icon" class="size-4" />
          <span>{{ option.label }}</span>
        </div>
      </template>
    </USelectMenu>

    <!-- Chunk Type Filter (Granularity) -->
    <USelectMenu
      v-if="showChunkTypes"
      v-model="localChunkTypes"
      :items="chunkTypeOptions"
      multiple
      :placeholder="(selectedChunkTypes?.length || 0) > 0 ? `${selectedChunkTypes?.length} level${(selectedChunkTypes?.length || 0) > 1 ? 's' : ''}` : 'All Levels'"
      :ui="{
        trigger: 'inline-flex items-center gap-x-1.5',
        width: 'w-auto min-w-[160px]'
      }"
      value-attribute="value"
    >
      <template #label>
        <UIcon name="i-lucide-layers" class="size-4" />
        <span v-if="(selectedChunkTypes?.length || 0) === 0">All Levels</span>
        <span v-else>{{ selectedChunkTypes?.length }} level{{ (selectedChunkTypes?.length || 0) > 1 ? 's' : '' }}</span>
      </template>

      <template #option="{ option }">
        <div class="flex items-center gap-2">
          <UIcon :name="option.icon" class="size-4" />
          <span>{{ option.label }}</span>
        </div>
      </template>
    </USelectMenu>

    <!-- Clear Filters Button -->
    <UButton
      v-if="hasActiveFilters"
      label="Clear"
      icon="i-lucide-x"
      color="neutral"
      variant="ghost"
      size="sm"
      @click="clearAllFilters"
    />

    <!-- Active Filters Badges (Optional, for more visibility) -->
    <div v-if="!isCompact && hasActiveFilters" class="flex flex-wrap gap-1.5">
      <UBadge
        v-for="caseId in selectedCases"
        :key="`case-${caseId}`"
        :label="availableCases.find(c => c.id === caseId)?.name || `Case #${caseId}`"
        color="primary"
        variant="soft"
        size="sm"
        @click="localCases = selectedCases.filter(id => id !== caseId)"
      >
        <template #trailing>
          <UIcon name="i-lucide-x" class="size-3 cursor-pointer" />
        </template>
      </UBadge>
      <UBadge
        v-for="type in selectedDocumentTypes"
        :key="`type-${type}`"
        :label="documentTypeOptions.find(o => o.value === type)?.label || type"
        color="secondary"
        variant="soft"
        size="sm"
        @click="localDocTypes = selectedDocumentTypes.filter(t => t !== type)"
      >
        <template #trailing>
          <UIcon name="i-lucide-x" class="size-3 cursor-pointer" />
        </template>
      </UBadge>
      <UBadge
        v-for="type in (selectedChunkTypes || [])"
        :key="`chunk-${type}`"
        :label="chunkTypeOptions.find(o => o.value === type)?.label || type"
        color="info"
        variant="soft"
        size="sm"
        @click="localChunkTypes = (selectedChunkTypes || []).filter(t => t !== type)"
      >
        <template #trailing>
          <UIcon name="i-lucide-x" class="size-3 cursor-pointer" />
        </template>
      </UBadge>
    </div>
  </div>
</template>
