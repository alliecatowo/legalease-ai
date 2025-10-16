<script setup lang="ts">
import type { DiscoveryItemFilters, Category } from '~/types/discovery'

const props = defineProps<{
  filters: DiscoveryItemFilters
  hasActiveFilters: boolean
}>()

const emit = defineEmits<{
  clear: []
}>()

// Fetch categories for filter
const categories = ref<Category[]>([])

async function fetchCategories() {
  try {
    const response = await $fetch('/api/discovery/categories')
    categories.value = response
  } catch (error) {
    console.error('Error fetching categories:', error)
  }
}

onMounted(() => {
  fetchCategories()
})

// Options for dropdowns
const typeOptions = [
  { label: 'All Types', value: null },
  { label: 'Photo', value: 'PHOTO' },
  { label: 'Video', value: 'VIDEO' },
  { label: 'Audio', value: 'AUDIO' },
  { label: 'Social Media', value: 'SOCIAL_MEDIA_POST' },
  { label: 'Email', value: 'EMAIL' },
  { label: 'Call Log', value: 'CALL_LOG' },
  { label: 'SMS', value: 'SMS' },
  { label: 'Document', value: 'DOCUMENT' }
]

const sourceOptions = [
  { label: 'All Sources', value: null },
  { label: 'Cellebrite', value: 'CELLEBRITE' },
  { label: 'Prosecutor', value: 'PROSECUTOR' },
  { label: 'Evidence', value: 'EVIDENCE' },
  { label: 'Surveillance', value: 'SURVEILLANCE' },
  { label: 'Body Cam', value: 'BODY_CAM' },
  { label: 'Social Media', value: 'SOCIAL_MEDIA' },
  { label: 'Email Export', value: 'EMAIL_EXPORT' },
  { label: 'Phone Records', value: 'PHONE_RECORDS' },
  { label: 'Other', value: 'OTHER' }
]

const formFactorOptions = [
  { label: 'All Form Factors', value: null },
  { label: 'Short Form', value: 'SHORT_FORM' },
  { label: 'Long Form', value: 'LONG_FORM' },
  { label: 'Single Item', value: 'SINGLE_ITEM' },
  { label: 'Batch Dump', value: 'BATCH_DUMP' }
]

const memeFilterOptions = [
  { label: 'All Items', value: null },
  { label: 'Memes Only', value: true },
  { label: 'No Memes', value: false }
]

// Computed for category options
const categoryOptions = computed(() => {
  return categories.value.map(cat => ({
    label: cat.name,
    value: cat.id
  }))
})
</script>

<template>
  <div class="h-full overflow-y-auto p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold">Filters</h2>
      <UButton
        v-if="hasActiveFilters"
        label="Clear All"
        size="xs"
        variant="ghost"
        color="neutral"
        @click="emit('clear')"
      />
    </div>

    <!-- Search -->
    <div>
      <label class="block text-sm font-medium mb-2">Search</label>
      <UInput
        v-model="filters.search"
        placeholder="Search captions, filenames..."
        icon="i-lucide-search"
      />
    </div>

    <!-- Type -->
    <div>
      <label class="block text-sm font-medium mb-2">Type</label>
      <USelect
        v-model="filters.type"
        :options="typeOptions"
        option-attribute="label"
        value-attribute="value"
      />
    </div>

    <!-- Source -->
    <div>
      <label class="block text-sm font-medium mb-2">Source</label>
      <USelect
        v-model="filters.source"
        :options="sourceOptions"
        option-attribute="label"
        value-attribute="value"
      />
    </div>

    <!-- Form Factor -->
    <div>
      <label class="block text-sm font-medium mb-2">Form Factor</label>
      <USelect
        v-model="filters.formFactor"
        :options="formFactorOptions"
        option-attribute="label"
        value-attribute="value"
      />
    </div>

    <!-- Importance Score -->
    <div>
      <label class="block text-sm font-medium mb-2">Importance Score</label>
      <div class="space-y-2">
        <div class="flex items-center gap-2">
          <UInput
            v-model.number="filters.minImportance"
            type="number"
            min="0"
            max="1"
            step="0.1"
            placeholder="Min"
            class="flex-1"
          />
          <span class="text-dimmed">to</span>
          <UInput
            v-model.number="filters.maxImportance"
            type="number"
            min="0"
            max="1"
            step="0.1"
            placeholder="Max"
            class="flex-1"
          />
        </div>

        <!-- Quick filters -->
        <div class="flex gap-2 flex-wrap">
          <UButton
            label="Critical (0.8+)"
            size="xs"
            variant="outline"
            color="red"
            @click="() => { filters.minImportance = 0.8; filters.maxImportance = 1.0 }"
          />
          <UButton
            label="High (0.6+)"
            size="xs"
            variant="outline"
            color="amber"
            @click="() => { filters.minImportance = 0.6; filters.maxImportance = 1.0 }"
          />
          <UButton
            label="Medium (0.4+)"
            size="xs"
            variant="outline"
            color="blue"
            @click="() => { filters.minImportance = 0.4; filters.maxImportance = 1.0 }"
          />
        </div>
      </div>
    </div>

    <!-- Date Range -->
    <div>
      <label class="block text-sm font-medium mb-2">Date Range</label>
      <div class="space-y-2">
        <UInput
          v-model="filters.startDate"
          type="date"
          placeholder="Start date"
        />
        <UInput
          v-model="filters.endDate"
          type="date"
          placeholder="End date"
        />

        <!-- Quick date filters -->
        <div class="flex gap-2 flex-wrap">
          <UButton
            label="Today"
            size="xs"
            variant="outline"
            @click="() => {
              const today = new Date().toISOString().split('T')[0]
              filters.startDate = today
              filters.endDate = today
            }"
          />
          <UButton
            label="Last 7 days"
            size="xs"
            variant="outline"
            @click="() => {
              const today = new Date()
              const week = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)
              filters.startDate = week.toISOString().split('T')[0]
              filters.endDate = today.toISOString().split('T')[0]
            }"
          />
          <UButton
            label="Last 30 days"
            size="xs"
            variant="outline"
            @click="() => {
              const today = new Date()
              const month = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000)
              filters.startDate = month.toISOString().split('T')[0]
              filters.endDate = today.toISOString().split('T')[0]
            }"
          />
        </div>
      </div>
    </div>

    <!-- Categories -->
    <div>
      <label class="block text-sm font-medium mb-2">Categories</label>
      <USelectMenu
        v-model="filters.categories"
        :options="categoryOptions"
        option-attribute="label"
        value-attribute="value"
        multiple
        placeholder="Select categories"
      />

      <!-- Selected categories -->
      <div v-if="filters.categories.length > 0" class="mt-2 flex gap-1 flex-wrap">
        <UBadge
          v-for="catId in filters.categories"
          :key="catId"
          size="xs"
          color="primary"
          variant="subtle"
        >
          {{ categories.find(c => c.id === catId)?.name }}
          <UIcon
            name="i-lucide-x"
            class="size-3 ml-1 cursor-pointer"
            @click="filters.categories = filters.categories.filter(id => id !== catId)"
          />
        </UBadge>
      </div>
    </div>

    <!-- Meme Filter -->
    <div>
      <label class="block text-sm font-medium mb-2">Meme Filter</label>
      <USelect
        v-model="filters.memeFilter"
        :options="memeFilterOptions"
        option-attribute="label"
        value-attribute="value"
      />
    </div>

    <!-- Processing Status -->
    <div>
      <label class="flex items-center gap-2 cursor-pointer">
        <UCheckbox v-model="filters.processedOnly" />
        <span class="text-sm font-medium">Processed only</span>
      </label>
    </div>

    <!-- Active filter count -->
    <div
      v-if="hasActiveFilters"
      class="pt-4 border-t border-default"
    >
      <div class="flex items-center gap-2 text-sm text-primary">
        <UIcon name="i-lucide-filter" class="size-4" />
        <span class="font-semibold">Active filters applied</span>
      </div>
    </div>
  </div>
</template>
