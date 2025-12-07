<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  modelValue?: {
    documentTypes?: string[]
    jurisdictions?: string[]
    dateRange?: [Date | null, Date | null]
    parties?: string[]
    tags?: string[]
    sortBy?: string
  }
}>()

const emit = defineEmits<{
  'update:modelValue': [value: typeof props.modelValue]
}>()

const filters = computed({
  get: () => props.modelValue || {},
  set: value => emit('update:modelValue', value)
})

// Document Types
const documentTypes = ref([
  { label: 'Contracts', value: 'contract', count: 234 },
  { label: 'Court Filings', value: 'court_filing', count: 156 },
  { label: 'Correspondence', value: 'correspondence', count: 89 },
  { label: 'Transcripts', value: 'transcript', count: 45 },
  { label: 'Briefs', value: 'brief', count: 78 },
  { label: 'Motions', value: 'motion', count: 123 }
])

// Jurisdictions
const jurisdictions = ref([
  { label: 'Federal', value: 'federal', count: 345 },
  { label: 'California', value: 'ca', count: 234 },
  { label: 'New York', value: 'ny', count: 189 },
  { label: 'Texas', value: 'tx', count: 145 },
  { label: 'Delaware', value: 'de', count: 98 }
])

// Date presets
const datePresets = [
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
  { label: 'Last 90 days', value: '90d' },
  { label: 'Last year', value: '1y' },
  { label: 'Custom range', value: 'custom' }
]

// Sort options
const sortOptions = [
  { label: 'Relevance', value: 'relevance', icon: 'i-lucide-sparkles' },
  { label: 'Date (Newest)', value: 'date_desc', icon: 'i-lucide-arrow-down-wide-narrow' },
  { label: 'Date (Oldest)', value: 'date_asc', icon: 'i-lucide-arrow-up-narrow-wide' },
  { label: 'Name (A-Z)', value: 'name_asc', icon: 'i-lucide-arrow-down-a-z' },
  { label: 'Citations (Most)', value: 'citations_desc', icon: 'i-lucide-link' }
]

const selectedDocTypes = computed({
  get: () => filters.value.documentTypes || [],
  set: (value) => {
    filters.value = { ...filters.value, documentTypes: value }
  }
})

const selectedJurisdictions = computed({
  get: () => filters.value.jurisdictions || [],
  set: (value) => {
    filters.value = { ...filters.value, jurisdictions: value }
  }
})

const selectedSort = computed({
  get: () => filters.value.sortBy || 'relevance',
  set: (value) => {
    filters.value = { ...filters.value, sortBy: value }
  }
})

const selectedTags = computed({
  get: () => filters.value.tags || [],
  set: (value) => {
    filters.value = { ...filters.value, tags: value }
  }
})

function clearFilters() {
  filters.value = { sortBy: 'relevance' }
}

const activeFilterCount = computed(() => {
  let count = 0
  if (selectedDocTypes.value.length) count++
  if (selectedJurisdictions.value.length) count++
  if (selectedTags.value.length) count++
  return count
})
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between p-4 border-b border-default">
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-filter" class="size-5 text-primary" />
        <h3 class="font-semibold text-highlighted">
          Filters
        </h3>
        <UBadge v-if="activeFilterCount" size="sm" variant="soft">
          {{ activeFilterCount }}
        </UBadge>
      </div>
      <UButton
        v-if="activeFilterCount"
        color="neutral"
        variant="ghost"
        size="xs"
        label="Clear all"
        @click="clearFilters"
      />
    </div>

    <!-- Filters Content -->
    <div class="flex-1 overflow-y-auto p-4 space-y-4">
      <!-- Sort By -->
      <div class="space-y-2">
        <label class="text-sm font-medium text-highlighted">Sort by</label>
        <USelectMenu
          v-model="selectedSort"
          :items="sortOptions"
          placeholder="Select sort order"
          value-key="value"
        >
          <template #leading="{ item }">
            <UIcon :name="item.icon" class="size-4" />
          </template>
        </USelectMenu>
      </div>

      <!-- Accordion for filter groups -->
      <UAccordion
        :items="[
          { label: 'Document Type', slot: 'doctype' },
          { label: 'Jurisdiction', slot: 'jurisdiction' },
          { label: 'Tags', slot: 'tags' },
          { label: 'Date Range', slot: 'daterange' }
        ]"
        :default-value="['0', '1']"
        type="multiple"
      >
        <!-- Document Types -->
        <template #doctype>
          <UCheckboxGroup v-model="selectedDocTypes" class="space-y-2">
            <div v-for="type in documentTypes" :key="type.value" class="flex items-center justify-between">
              <UCheckbox :value="type.value" :label="type.label" />
              <span class="text-xs text-dimmed">{{ type.count }}</span>
            </div>
          </UCheckboxGroup>
        </template>

        <!-- Jurisdictions -->
        <template #jurisdiction>
          <UCheckboxGroup v-model="selectedJurisdictions" class="space-y-2">
            <div v-for="jurisdiction in jurisdictions" :key="jurisdiction.value" class="flex items-center justify-between">
              <UCheckbox :value="jurisdiction.value" :label="jurisdiction.label" />
              <span class="text-xs text-dimmed">{{ jurisdiction.count }}</span>
            </div>
          </UCheckboxGroup>
        </template>

        <!-- Tags -->
        <template #tags>
          <UInputTags
            v-model="selectedTags"
            placeholder="Add tags to filter..."
            class="w-full"
          />
          <p class="text-xs text-muted mt-2">
            Press Enter to add tags
          </p>
        </template>

        <!-- Date Range -->
        <template #daterange>
          <div class="space-y-3">
            <div class="grid grid-cols-2 gap-2">
              <UButton
                v-for="preset in datePresets.slice(0, 4)"
                :key="preset.value"
                :label="preset.label"
                color="neutral"
                variant="outline"
                size="xs"
                class="justify-center"
              />
            </div>
            <div class="pt-2 border-t border-default">
              <UCalendar
                class="w-full"
              />
            </div>
          </div>
        </template>
      </UAccordion>
    </div>

    <!-- Footer -->
    <div class="p-4 border-t border-default">
      <UButton
        label="Apply Filters"
        color="primary"
        block
        icon="i-lucide-check"
      />
    </div>
  </div>
</template>
