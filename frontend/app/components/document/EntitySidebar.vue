<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Entity } from '~/composables/usePDFHighlights'

const props = defineProps<{
  entities: Entity[]
  selectedEntity?: Entity | null
}>()

const emit = defineEmits<{
  'select-entity': [entity: Entity]
  'navigate-to-box': [boxId: string]
}>()

const searchQuery = ref('')
const selectedType = ref<string | null>(null)
const sortBy = ref<'type' | 'confidence' | 'alphabetical'>('type')

// Group entities by type
const entityGroups = computed(() => {
  const filtered = props.entities.filter((entity) => {
    const matchesSearch = !searchQuery.value
      || entity.text.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesType = !selectedType.value || entity.type === selectedType.value
    return matchesSearch && matchesType
  })

  // Sort
  const sorted = [...filtered].sort((a, b) => {
    if (sortBy.value === 'type') {
      return a.type.localeCompare(b.type)
    } else if (sortBy.value === 'confidence') {
      return b.confidence - a.confidence
    } else {
      return a.text.localeCompare(b.text)
    }
  })

  // Group by type
  const groups: Record<string, Entity[]> = {}
  sorted.forEach((entity) => {
    if (!groups[entity.type]) {
      groups[entity.type] = []
    }
    groups[entity.type].push(entity)
  })

  return groups
})

// Get unique entity types
const entityTypes = computed(() => {
  const types = new Set(props.entities.map(e => e.type))
  return Array.from(types).sort()
})

// Count entities by type
function getTypeCount(type: string): number {
  return props.entities.filter(e => e.type === type).length
}

// Entity type icons
const entityTypeIcons: Record<string, string> = {
  PERSON: 'i-lucide-user',
  ORGANIZATION: 'i-lucide-building',
  LOCATION: 'i-lucide-map-pin',
  DATE: 'i-lucide-calendar',
  MONEY: 'i-lucide-dollar-sign',
  COURT: 'i-lucide-landmark',
  CITATION: 'i-lucide-quote',
  LAW: 'i-lucide-scale',
  CLAUSE: 'i-lucide-file-text'
}

// Entity type colors
const entityTypeColors: Record<string, string> = {
  PERSON: 'primary',
  ORGANIZATION: 'secondary',
  LOCATION: 'success',
  DATE: 'warning',
  MONEY: 'error',
  COURT: 'neutral',
  CITATION: 'info'
}

function selectEntity(entity: Entity) {
  emit('select-entity', entity)
}

function navigateToBox(boxId: string) {
  emit('navigate-to-box', boxId)
}
</script>

<template>
  <div class="flex flex-col h-full bg-default">
    <!-- Header -->
    <div class="p-4 border-b border-default space-y-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <UIcon name="i-lucide-tag" class="size-5 text-primary" />
          <h3 class="font-semibold text-highlighted">
            Extracted Entities
          </h3>
          <UBadge :label="String(entities.length)" size="sm" variant="soft" />
        </div>
      </div>

      <!-- Search -->
      <UInput
        v-model="searchQuery"
        icon="i-lucide-search"
        placeholder="Search entities..."
        size="sm"
      />

      <!-- Type Filter -->
      <div class="flex items-center gap-2">
        <USelectMenu
          v-model="selectedType"
          :items="[{ label: 'All Types', value: null }, ...entityTypes.map(t => ({ label: t, value: t }))]"
          placeholder="Filter by type"
          size="sm"
          class="flex-1"
        />
        <USelectMenu
          v-model="sortBy"
          :items="[
            { label: 'By Type', value: 'type' },
            { label: 'By Confidence', value: 'confidence' },
            { label: 'Alphabetical', value: 'alphabetical' }
          ]"
          placeholder="Sort"
          size="sm"
          class="flex-1"
        />
      </div>
    </div>

    <!-- Entity List -->
    <div class="flex-1 overflow-y-auto p-4 space-y-4">
      <div v-for="(entitiesInGroup, type) in entityGroups" :key="type" class="space-y-2">
        <!-- Type Header -->
        <div class="flex items-center justify-between py-2 border-b border-default">
          <div class="flex items-center gap-2">
            <UIcon :name="entityTypeIcons[type] || 'i-lucide-tag'" class="size-4" />
            <span class="text-sm font-medium text-highlighted">{{ type }}</span>
            <UBadge :label="String(entitiesInGroup.length)" size="xs" variant="subtle" />
          </div>
        </div>

        <!-- Entities in this type -->
        <div class="space-y-1">
          <div
            v-for="entity in entitiesInGroup"
            :key="entity.id"
            class="p-2 rounded-md cursor-pointer transition-colors"
            :class="[
              selectedEntity?.id === entity.id
                ? 'bg-primary/10 ring-1 ring-primary'
                : 'hover:bg-elevated'
            ]"
            @click="selectEntity(entity)"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-highlighted truncate">
                  {{ entity.text }}
                </p>
                <div class="flex items-center gap-2 mt-1">
                  <UBadge
                    :label="`${Math.round(entity.confidence * 100)}%`"
                    :color="entity.confidence > 0.9 ? 'success' : entity.confidence > 0.7 ? 'warning' : 'neutral'"
                    size="xs"
                    variant="subtle"
                  />
                  <span class="text-xs text-dimmed">
                    {{ entity.boundingBoxes.length }} {{ entity.boundingBoxes.length === 1 ? 'mention' : 'mentions' }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Bounding Box Links -->
            <div v-if="selectedEntity?.id === entity.id && entity.boundingBoxes.length > 0" class="mt-2 pt-2 border-t border-default">
              <p class="text-xs text-muted mb-2">
                Mentions in document:
              </p>
              <div class="space-y-1">
                <button
                  v-for="box in entity.boundingBoxes"
                  :key="box.id"
                  class="w-full text-left px-2 py-1 rounded text-xs hover:bg-elevated transition-colors flex items-center justify-between"
                  @click.stop="navigateToBox(box.id)"
                >
                  <span class="text-default">Page {{ box.page }}</span>
                  <UIcon name="i-lucide-arrow-right" class="size-3 text-muted" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="Object.keys(entityGroups).length === 0" class="text-center py-12">
        <UIcon name="i-lucide-inbox" class="size-12 text-muted mx-auto mb-3 opacity-30" />
        <p class="text-sm text-muted">
          {{ searchQuery || selectedType ? 'No matching entities found' : 'No entities extracted yet' }}
        </p>
      </div>
    </div>

    <!-- Footer Stats -->
    <div class="p-4 border-t border-default bg-muted/10">
      <div class="grid grid-cols-3 gap-4 text-center">
        <div>
          <p class="text-2xl font-bold text-highlighted">
            {{ entities.length }}
          </p>
          <p class="text-xs text-muted">
            Total Entities
          </p>
        </div>
        <div>
          <p class="text-2xl font-bold text-highlighted">
            {{ entityTypes.length }}
          </p>
          <p class="text-xs text-muted">
            Entity Types
          </p>
        </div>
        <div>
          <p class="text-2xl font-bold text-highlighted">
            {{ Math.round(entities.reduce((sum, e) => sum + e.confidence, 0) / entities.length * 100) || 0 }}%
          </p>
          <p class="text-xs text-muted">
            Avg Confidence
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
