<script setup lang="ts">
import { computed } from 'vue'
import type { GraphNode, GraphEdge } from '~/composables/useKnowledgeGraph'

const props = defineProps<{
  node: GraphNode | null
  edges: GraphEdge[]
  nodeTypeIcons: Record<string, string>
  nodeTypeColors: Record<string, string>
}>()

const emit = defineEmits<{
  'close': []
  'navigate-to-node': [nodeId: string]
  'navigate-to-document': [documentId: string]
}>()

// Get connected edges for this node
const connectedEdges = computed(() => {
  if (!props.node) return []
  return props.edges.filter(edge =>
    edge.source === props.node!.id || edge.target === props.node!.id
  )
})

// Group edges by direction
const incomingEdges = computed(() =>
  connectedEdges.value.filter(edge => edge.target === props.node!.id)
)

const outgoingEdges = computed(() =>
  connectedEdges.value.filter(edge => edge.source === props.node!.id)
)

// Format property value
function formatPropertyValue(value: any): string {
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }
  return String(value)
}

// Get edge label with direction indicator
function getEdgeLabel(edge: GraphEdge, isIncoming: boolean): string {
  const arrow = isIncoming ? '←' : '→'
  return `${arrow} ${edge.label}`
}

// Get the other node ID in an edge
function getOtherNodeId(edge: GraphEdge): string {
  return edge.source === props.node!.id ? edge.target : edge.source
}
</script>

<template>
  <UDrawer
    :model-value="!!node"
    @update:model-value="(value) => !value && emit('close')"
    side="right"
    :ui="{ width: 'w-96' }"
  >
    <template #header>
      <div class="flex items-start justify-between">
        <div class="flex items-start gap-3 flex-1">
          <div
            class="p-3 rounded-lg"
            :style="{ backgroundColor: node ? nodeTypeColors[node.type] + '20' : '#F3F4F6' }"
          >
            <UIcon
              :name="node ? nodeTypeIcons[node.type] || 'i-lucide-circle' : 'i-lucide-circle'"
              class="size-6"
              :style="{ color: node ? nodeTypeColors[node.type] : '#6B7280' }"
            />
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-highlighted text-lg mb-1">
              {{ node?.label }}
            </h3>
            <UBadge
              v-if="node"
              :label="node.type.charAt(0).toUpperCase() + node.type.slice(1)"
              :style="{ backgroundColor: nodeTypeColors[node.type] + '20', color: nodeTypeColors[node.type] }"
              size="sm"
            />
          </div>
        </div>
      </div>
    </template>

    <div v-if="node" class="space-y-6">
      <!-- Metadata -->
      <div v-if="node.metadata">
        <h4 class="text-sm font-semibold text-highlighted mb-3">Metadata</h4>
        <div class="space-y-2">
          <div v-if="node.metadata.confidence !== undefined" class="flex items-center justify-between p-2 rounded-lg bg-muted/20">
            <span class="text-sm text-muted">Confidence</span>
            <UBadge
              :label="`${Math.round(node.metadata.confidence * 100)}%`"
              :color="node.metadata.confidence > 0.9 ? 'success' : node.metadata.confidence > 0.7 ? 'warning' : 'neutral'"
              size="sm"
            />
          </div>
          <div v-if="node.metadata.extractedFrom && node.metadata.extractedFrom.length > 0" class="p-2 rounded-lg bg-muted/20">
            <span class="text-sm text-muted block mb-2">Extracted From</span>
            <div class="flex flex-wrap gap-1">
              <UButton
                v-for="docId in node.metadata.extractedFrom"
                :key="docId"
                :label="docId"
                color="neutral"
                variant="soft"
                size="xs"
                @click="emit('navigate-to-document', docId)"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Properties -->
      <div v-if="Object.keys(node.properties).length > 0">
        <h4 class="text-sm font-semibold text-highlighted mb-3">Properties</h4>
        <div class="space-y-2">
          <div
            v-for="[key, value] in Object.entries(node.properties)"
            :key="key"
            class="p-3 rounded-lg bg-muted/20"
          >
            <div class="text-xs text-muted mb-1">{{ key }}</div>
            <div class="text-sm text-highlighted font-medium">{{ formatPropertyValue(value) }}</div>
          </div>
        </div>
      </div>

      <!-- Connections -->
      <div>
        <h4 class="text-sm font-semibold text-highlighted mb-3">
          Connections
          <UBadge :label="String(connectedEdges.length)" size="sm" variant="soft" class="ml-2" />
        </h4>

        <div class="space-y-4">
          <!-- Incoming Edges -->
          <div v-if="incomingEdges.length > 0">
            <div class="text-xs text-muted mb-2">Incoming ({{ incomingEdges.length }})</div>
            <div class="space-y-1">
              <button
                v-for="edge in incomingEdges"
                :key="edge.id"
                class="w-full text-left p-2 rounded-lg hover:bg-elevated transition-colors flex items-center justify-between group"
                @click="emit('navigate-to-node', getOtherNodeId(edge))"
              >
                <div class="flex items-center gap-2 flex-1 min-w-0">
                  <UIcon name="i-lucide-arrow-left" class="size-3 text-muted shrink-0" />
                  <span class="text-sm text-default truncate">{{ getOtherNodeId(edge) }}</span>
                </div>
                <span class="text-xs text-muted">{{ edge.label }}</span>
              </button>
            </div>
          </div>

          <!-- Outgoing Edges -->
          <div v-if="outgoingEdges.length > 0">
            <div class="text-xs text-muted mb-2">Outgoing ({{ outgoingEdges.length }})</div>
            <div class="space-y-1">
              <button
                v-for="edge in outgoingEdges"
                :key="edge.id"
                class="w-full text-left p-2 rounded-lg hover:bg-elevated transition-colors flex items-center justify-between group"
                @click="emit('navigate-to-node', getOtherNodeId(edge))"
              >
                <div class="flex items-center gap-2 flex-1 min-w-0">
                  <UIcon name="i-lucide-arrow-right" class="size-3 text-muted shrink-0" />
                  <span class="text-sm text-default truncate">{{ getOtherNodeId(edge) }}</span>
                </div>
                <span class="text-xs text-muted">{{ edge.label }}</span>
              </button>
            </div>
          </div>

          <!-- No connections -->
          <div v-if="connectedEdges.length === 0" class="text-center py-8">
            <UIcon name="i-lucide-unlink" class="size-8 text-muted mx-auto mb-2 opacity-30" />
            <p class="text-sm text-muted">No connections</p>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="pt-4 border-t border-default">
        <h4 class="text-sm font-semibold text-highlighted mb-3">Actions</h4>
        <div class="space-y-2">
          <UButton
            label="View in Document"
            icon="i-lucide-file-text"
            color="neutral"
            variant="outline"
            block
          />
          <UButton
            label="Add to Case"
            icon="i-lucide-folder-plus"
            color="neutral"
            variant="outline"
            block
          />
          <UButton
            label="Export Node Data"
            icon="i-lucide-download"
            color="neutral"
            variant="outline"
            block
          />
        </div>
      </div>
    </div>
  </UDrawer>
</template>
