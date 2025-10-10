<script setup lang="ts">
import { computed } from 'vue'
import type { GraphFilter, GraphNode, GraphEdge } from '~/composables/useKnowledgeGraph'

const props = defineProps<{
  filters: GraphFilter
  nodes: GraphNode[]
  edges: GraphEdge[]
  nodeTypeColors: Record<string, string>
  nodeTypeIcons: Record<string, string>
}>()

const emit = defineEmits<{
  'update:filters': [filters: Partial<GraphFilter>]
  'clear': []
}>()

// Get unique node types with counts
const nodeTypeCounts = computed(() => {
  const counts: Record<string, number> = {}
  props.nodes.forEach(node => {
    counts[node.type] = (counts[node.type] || 0) + 1
  })
  return Object.entries(counts).map(([type, count]) => ({
    value: type,
    label: type.charAt(0).toUpperCase() + type.slice(1),
    count,
    icon: props.nodeTypeIcons[type] || 'i-lucide-circle',
    color: props.nodeTypeColors[type] || '#6B7280'
  })).sort((a, b) => b.count - a.count)
})

// Get unique edge types with counts
const edgeTypeCounts = computed(() => {
  const counts: Record<string, number> = {}
  props.edges.forEach(edge => {
    counts[edge.type] = (counts[edge.type] || 0) + 1
  })
  return Object.entries(counts).map(([type, count]) => ({
    value: type,
    label: type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
    count
  })).sort((a, b) => b.count - a.count)
})

// Local filter state
const localNodeTypes = computed({
  get: () => props.filters.nodeTypes,
  set: (value) => emit('update:filters', { nodeTypes: value })
})

const localEdgeTypes = computed({
  get: () => props.filters.edgeTypes,
  set: (value) => emit('update:filters', { edgeTypes: value })
})

const localSearchQuery = computed({
  get: () => props.filters.searchQuery || '',
  set: (value) => emit('update:filters', { searchQuery: value })
})

const localMinConfidence = computed({
  get: () => props.filters.minConfidence || 0,
  set: (value) => emit('update:filters', { minConfidence: value })
})

// Active filter count
const activeFilterCount = computed(() => {
  let count = 0
  if (props.filters.nodeTypes.length > 0) count++
  if (props.filters.edgeTypes.length > 0) count++
  if (props.filters.minConfidence && props.filters.minConfidence > 0) count++
  if (props.filters.searchQuery) count++
  return count
})
</script>

<template>
  <div class="flex flex-col h-full bg-default">
    <!-- Header -->
    <div class="p-4 border-b border-default">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <UIcon name="i-lucide-filter" class="size-5 text-primary" />
          <h3 class="font-semibold text-highlighted">Filters</h3>
          <UBadge v-if="activeFilterCount > 0" :label="String(activeFilterCount)" size="sm" color="primary" />
        </div>
        <UButton
          v-if="activeFilterCount > 0"
          label="Clear"
          color="neutral"
          variant="ghost"
          size="xs"
          @click="emit('clear')"
        />
      </div>

      <!-- Search -->
      <UInput
        v-model="localSearchQuery"
        icon="i-lucide-search"
        placeholder="Search nodes..."
        size="sm"
      />
    </div>

    <!-- Filters -->
    <div class="flex-1 overflow-y-auto p-4 space-y-4">
      <!-- Node Types -->
      <div>
        <UAccordion
          :items="[{ label: 'Node Types', slot: 'nodetypes', defaultOpen: true }]"
          type="multiple"
        >
          <template #nodetypes>
            <div class="space-y-2 pt-2">
              <div
                v-for="type in nodeTypeCounts"
                :key="type.value"
                class="flex items-center justify-between"
              >
                <UCheckbox
                  :model-value="localNodeTypes.includes(type.value)"
                  @update:model-value="(checked) => {
                    if (checked) {
                      localNodeTypes = [...localNodeTypes, type.value]
                    } else {
                      localNodeTypes = localNodeTypes.filter(t => t !== type.value)
                    }
                  }"
                >
                  <template #label>
                    <div class="flex items-center gap-2">
                      <UIcon :name="type.icon" class="size-4" :style="{ color: type.color }" />
                      <span class="text-sm text-default">{{ type.label }}</span>
                    </div>
                  </template>
                </UCheckbox>
                <span class="text-xs text-dimmed">{{ type.count }}</span>
              </div>
            </div>
          </template>
        </UAccordion>
      </div>

      <!-- Edge Types -->
      <div>
        <UAccordion
          :items="[{ label: 'Edge Types', slot: 'edgetypes' }]"
          type="multiple"
        >
          <template #edgetypes>
            <div class="space-y-2 pt-2">
              <div
                v-for="type in edgeTypeCounts"
                :key="type.value"
                class="flex items-center justify-between"
              >
                <UCheckbox
                  :model-value="localEdgeTypes.includes(type.value)"
                  @update:model-value="(checked) => {
                    if (checked) {
                      localEdgeTypes = [...localEdgeTypes, type.value]
                    } else {
                      localEdgeTypes = localEdgeTypes.filter(t => t !== type.value)
                    }
                  }"
                >
                  <template #label>
                    <span class="text-sm text-default">{{ type.label }}</span>
                  </template>
                </UCheckbox>
                <span class="text-xs text-dimmed">{{ type.count }}</span>
              </div>
            </div>
          </template>
        </UAccordion>
      </div>

      <!-- Confidence Threshold -->
      <div>
        <UAccordion
          :items="[{ label: 'Confidence', slot: 'confidence' }]"
          type="multiple"
        >
          <template #confidence>
            <div class="pt-2 space-y-3">
              <div class="flex items-center justify-between text-sm">
                <span class="text-muted">Minimum Confidence</span>
                <span class="font-medium text-highlighted">{{ Math.round(localMinConfidence * 100) }}%</span>
              </div>
              <input
                v-model.number="localMinConfidence"
                type="range"
                min="0"
                max="1"
                step="0.05"
                class="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
              />
              <div class="flex justify-between text-xs text-dimmed">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>
          </template>
        </UAccordion>
      </div>
    </div>

    <!-- Footer Stats -->
    <div class="p-4 border-t border-default bg-muted/10">
      <div class="grid grid-cols-2 gap-4 text-center">
        <div>
          <p class="text-2xl font-bold text-highlighted">{{ nodes.length }}</p>
          <p class="text-xs text-muted">Nodes</p>
        </div>
        <div>
          <p class="text-2xl font-bold text-highlighted">{{ edges.length }}</p>
          <p class="text-xs text-muted">Edges</p>
        </div>
      </div>
    </div>
  </div>
</template>
