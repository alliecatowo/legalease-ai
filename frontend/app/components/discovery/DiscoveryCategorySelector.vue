<script setup lang="ts">
import type { Category, CategoryType } from '~/types/discovery'

const emit = defineEmits<{
  select: [categoryId: number]
}>()

// State
const categories = ref<Category[]>([])
const loading = ref(false)
const searchQuery = ref('')
const selectedType = ref<CategoryType | null>(null)
const showCreateModal = ref(false)

// New category form
const newCategory = reactive({
  name: '',
  description: '',
  type: 'CUSTOM' as CategoryType,
  parent_category_id: null as number | null,
  color: '#3b82f6',
  icon: 'i-lucide-tag'
})

// Fetch categories
async function fetchCategories() {
  loading.value = true
  try {
    const response = await $fetch('/api/discovery/categories')
    categories.value = response
  } catch (error) {
    console.error('Error fetching categories:', error)
  } finally {
    loading.value = false
  }
}

// Create category
async function createCategory() {
  try {
    const response = await $fetch('/api/discovery/categories', {
      method: 'POST',
      body: newCategory
    })

    categories.value.push(response)
    showCreateModal.value = false

    // Reset form
    Object.assign(newCategory, {
      name: '',
      description: '',
      type: 'CUSTOM',
      parent_category_id: null,
      color: '#3b82f6',
      icon: 'i-lucide-tag'
    })
  } catch (error) {
    console.error('Error creating category:', error)
  }
}

// Filter categories
const filteredCategories = computed(() => {
  let filtered = categories.value

  if (selectedType.value) {
    filtered = filtered.filter(cat => cat.type === selectedType.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(cat =>
      cat.name.toLowerCase().includes(query) ||
      cat.description?.toLowerCase().includes(query)
    )
  }

  return filtered
})

// Group categories by type
const groupedCategories = computed(() => {
  const groups: Record<CategoryType, Category[]> = {
    EVIDENCE_TYPE: [],
    SUBJECT_MATTER: [],
    LEGAL_RELEVANCE: [],
    CUSTOM: []
  }

  filteredCategories.value.forEach(cat => {
    groups[cat.type].push(cat)
  })

  return groups
})

// Type options
const typeOptions = [
  { label: 'All Types', value: null },
  { label: 'Evidence Type', value: 'EVIDENCE_TYPE' },
  { label: 'Subject Matter', value: 'SUBJECT_MATTER' },
  { label: 'Legal Relevance', value: 'LEGAL_RELEVANCE' },
  { label: 'Custom', value: 'CUSTOM' }
]

// Icon options for new categories
const iconOptions = [
  'i-lucide-tag',
  'i-lucide-star',
  'i-lucide-flag',
  'i-lucide-bookmark',
  'i-lucide-shield',
  'i-lucide-alert-triangle',
  'i-lucide-check-circle',
  'i-lucide-x-circle',
  'i-lucide-info',
  'i-lucide-file-text'
]

onMounted(() => {
  fetchCategories()
})

function selectCategory(categoryId: number) {
  emit('select', categoryId)
}
</script>

<template>
  <div class="space-y-4">
    <!-- Search and filters -->
    <div class="flex gap-2">
      <UInput
        v-model="searchQuery"
        placeholder="Search categories..."
        icon="i-lucide-search"
        class="flex-1"
      />
      <USelect
        v-model="selectedType"
        :options="typeOptions"
        option-attribute="label"
        value-attribute="value"
        class="w-48"
      />
      <UButton
        label="New"
        icon="i-lucide-plus"
        color="primary"
        @click="showCreateModal = true"
      />
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="flex items-center justify-center py-8">
      <UIcon name="i-lucide-loader-2" class="size-6 animate-spin text-primary" />
    </div>

    <!-- Categories list -->
    <div v-else class="space-y-4 max-h-96 overflow-y-auto">
      <!-- Group by type -->
      <div
        v-for="(cats, type) in groupedCategories"
        :key="type"
        class="space-y-2"
      >
        <h3
          v-if="cats.length > 0 && !selectedType"
          class="text-sm font-semibold text-dimmed uppercase tracking-wide"
        >
          {{ type.replace(/_/g, ' ') }}
        </h3>

        <div class="grid grid-cols-1 gap-2">
          <UCard
            v-for="category in cats"
            :key="category.id"
            class="cursor-pointer hover:bg-elevated transition-colors"
            @click="selectCategory(category.id)"
          >
            <div class="flex items-center gap-3">
              <!-- Color indicator -->
              <div
                :style="{ backgroundColor: category.color || '#3b82f6' }"
                class="w-3 h-3 rounded-full flex-shrink-0"
              />

              <!-- Icon -->
              <UIcon
                v-if="category.icon"
                :name="category.icon"
                class="size-5 flex-shrink-0"
              />

              <!-- Content -->
              <div class="flex-1 min-w-0">
                <p class="font-semibold">{{ category.name }}</p>
                <p v-if="category.description" class="text-sm text-dimmed truncate">
                  {{ category.description }}
                </p>
              </div>

              <!-- Select icon -->
              <UIcon name="i-lucide-chevron-right" class="size-4 text-dimmed flex-shrink-0" />
            </div>
          </UCard>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-if="filteredCategories.length === 0"
        class="text-center py-8"
      >
        <UIcon name="i-lucide-tag" class="size-12 text-dimmed mb-2" />
        <p class="text-dimmed">No categories found</p>
      </div>
    </div>

    <!-- Create category modal -->
    <UModal v-model:open="showCreateModal">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Create Category</h3>
        </template>

        <div class="space-y-4">
          <!-- Name -->
          <UFormField label="Name" required>
            <UInput
              v-model="newCategory.name"
              placeholder="Enter category name"
            />
          </UFormField>

          <!-- Description -->
          <UFormField label="Description">
            <UTextarea
              v-model="newCategory.description"
              placeholder="Enter category description"
              rows="3"
            />
          </UFormField>

          <!-- Type -->
          <UFormField label="Type" required>
            <USelect
              v-model="newCategory.type"
              :options="typeOptions.slice(1)"
              option-attribute="label"
              value-attribute="value"
            />
          </UFormField>

          <!-- Parent category -->
          <UFormField label="Parent Category">
            <USelect
              v-model="newCategory.parent_category_id"
              :options="[
                { label: 'None', value: null },
                ...categories.map(cat => ({ label: cat.name, value: cat.id }))
              ]"
              option-attribute="label"
              value-attribute="value"
            />
          </UFormField>

          <!-- Color -->
          <UFormField label="Color">
            <div class="flex items-center gap-2">
              <input
                v-model="newCategory.color"
                type="color"
                class="w-12 h-10 rounded border border-default cursor-pointer"
              />
              <UInput
                v-model="newCategory.color"
                placeholder="#3b82f6"
                class="flex-1"
              />
            </div>
          </UFormField>

          <!-- Icon -->
          <UFormField label="Icon">
            <div class="grid grid-cols-5 gap-2">
              <button
                v-for="icon in iconOptions"
                :key="icon"
                :class="[
                  'p-3 rounded border-2 transition-colors',
                  newCategory.icon === icon
                    ? 'border-primary bg-primary/10'
                    : 'border-default hover:border-primary/50'
                ]"
                @click="newCategory.icon = icon"
              >
                <UIcon :name="icon" class="size-6" />
              </button>
            </div>
          </UFormField>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton
              label="Cancel"
              color="neutral"
              variant="ghost"
              @click="showCreateModal = false"
            />
            <UButton
              label="Create"
              color="primary"
              :disabled="!newCategory.name"
              @click="createCategory"
            />
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>
