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
    const response = await $fetch('/api/v1/discovery/categories')
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
  { label: 'All Types', value: null, icon: 'i-lucide-grid-3x3' },
  { label: 'Photo / Image', value: 'PHOTO', icon: 'i-lucide-image' },
  { label: 'Video', value: 'VIDEO', icon: 'i-lucide-video' },
  { label: 'Audio', value: 'AUDIO', icon: 'i-lucide-mic' },
  { label: 'Social Media', value: 'SOCIAL_MEDIA_POST', icon: 'i-lucide-share-2' },
  { label: 'Email', value: 'EMAIL', icon: 'i-lucide-mail' },
  { label: 'Call Log', value: 'CALL_LOG', icon: 'i-lucide-phone' },
  { label: 'SMS', value: 'SMS', icon: 'i-lucide-message-square' },
  { label: 'Document', value: 'DOCUMENT', icon: 'i-lucide-file-text' }
]

const sourceOptions = [
  { label: 'All Sources', value: null, icon: 'i-lucide-map-pin' },
  { label: 'Cellebrite', value: 'CELLEBRITE', icon: 'i-lucide-cpu' },
  { label: 'Prosecutor', value: 'PROSECUTOR', icon: 'i-lucide-briefcase' },
  { label: 'Evidence Locker', value: 'EVIDENCE', icon: 'i-lucide-archive' },
  { label: 'Surveillance', value: 'SURVEILLANCE', icon: 'i-lucide-eye' },
  { label: 'Body Cam', value: 'BODY_CAM', icon: 'i-lucide-camera' },
  { label: 'Social Media', value: 'SOCIAL_MEDIA', icon: 'i-lucide-at-sign' },
  { label: 'Email Export', value: 'EMAIL_EXPORT', icon: 'i-lucide-inbox' },
  { label: 'Phone Records', value: 'PHONE_RECORDS', icon: 'i-lucide-phone-call' },
  { label: 'Other', value: 'OTHER', icon: 'i-lucide-ellipsis' }
]

const formFactorOptions = [
  { label: 'All Form Factors', value: null, icon: 'i-lucide-layers' },
  { label: 'Short Form', value: 'SHORT_FORM', icon: 'i-lucide-timer' },
  { label: 'Long Form', value: 'LONG_FORM', icon: 'i-lucide-hourglass' },
  { label: 'Single Item', value: 'SINGLE_ITEM', icon: 'i-lucide-square' },
  { label: 'Batch Dump', value: 'BATCH_DUMP', icon: 'i-lucide-layers' }
]

const memeFilterOptions = [
  { label: 'All Items', value: null, icon: 'i-lucide-layers' },
  { label: 'Memes Only', value: true, icon: 'i-lucide-smile' },
  { label: 'No Memes', value: false, icon: 'i-lucide-ban' }
]

// Computed for category options
const categoryOptions = computed(() => {
  return categories.value.map(cat => ({
    label: cat.name,
    value: cat.id,
    icon: cat.icon,
    color: cat.color
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
      <USelectMenu
        v-model="filters.type"
        :items="typeOptions"
        value-attribute="value"
        placeholder="All Types"
      >
        <template #leading>
          <UIcon name="i-lucide-image" class="size-4 text-dimmed" />
        </template>
        <template #option="{ option }">
          <div class="flex items-center gap-2">
            <UIcon v-if="option.icon" :name="option.icon" class="size-4 text-dimmed" />
            <span>{{ option.label }}</span>
          </div>
        </template>
      </USelectMenu>
    </div>

    <!-- Source -->
    <div>
      <label class="block text-sm font-medium mb-2">Source</label>
      <USelectMenu
        v-model="filters.source"
        :items="sourceOptions"
        value-attribute="value"
        placeholder="All Sources"
      >
        <template #leading>
          <UIcon name="i-lucide-map-pin" class="size-4 text-dimmed" />
        </template>
        <template #option="{ option }">
          <div class="flex items-center gap-2">
            <UIcon v-if="option.icon" :name="option.icon" class="size-4 text-dimmed" />
            <span>{{ option.label }}</span>
          </div>
        </template>
      </USelectMenu>
    </div>

    <!-- Form Factor -->
    <div>
      <label class="block text-sm font-medium mb-2">Form Factor</label>
      <USelectMenu
        v-model="filters.formFactor"
        :items="formFactorOptions"
        value-attribute="value"
        placeholder="All Form Factors"
      >
        <template #leading>
          <UIcon name="i-lucide-layers" class="size-4 text-dimmed" />
        </template>
        <template #option="{ option }">
          <div class="flex items-center gap-2">
            <UIcon v-if="option.icon" :name="option.icon" class="size-4 text-dimmed" />
            <span>{{ option.label }}</span>
          </div>
        </template>
      </USelectMenu>
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
        :items="categoryOptions"
        value-attribute="value"
        multiple
        placeholder="Select categories"
      >
        <template #leading>
          <UIcon name="i-lucide-tag" class="size-4 text-dimmed" />
        </template>
        <template #option="{ option }">
          <div class="flex items-center gap-2">
            <div
              v-if="option.color"
              :style="{ backgroundColor: option.color }"
              class="w-2.5 h-2.5 rounded-full"
            />
            <UIcon v-if="option.icon" :name="option.icon" class="size-4 text-dimmed" />
            <span>{{ option.label }}</span>
          </div>
        </template>
        <template #selection="{ option }">
          <div class="flex items-center gap-2">
            <div
              v-if="option.color"
              :style="{ backgroundColor: option.color }"
              class="w-2 h-2 rounded-full"
            />
            <span>{{ option.label }}</span>
          </div>
        </template>
      </USelectMenu>

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
      <USelectMenu
        v-model="filters.memeFilter"
        :items="memeFilterOptions"
        value-attribute="value"
        placeholder="All items"
      >
        <template #leading>
          <UIcon name="i-lucide-smile" class="size-4 text-dimmed" />
        </template>
        <template #option="{ option }">
          <div class="flex items-center gap-2">
            <UIcon v-if="option.icon" :name="option.icon" class="size-4 text-dimmed" />
            <span>{{ option.label }}</span>
          </div>
        </template>
      </USelectMenu>
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
