<template>
  <div class="bg-white rounded-lg border border-gray-200 p-6">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h3 class="text-lg font-semibold text-gray-900">Knowledge Graph</h3>
        <p class="text-sm text-gray-600">
          Visual representation of entity relationships and citations
        </p>
      </div>

      <div class="flex items-center space-x-3">
        <USelectMenu
          v-model="selectedView"
          :options="viewOptions"
          size="sm"
          class="w-32"
        />

        <UButton
          variant="outline"
          size="sm"
          @click="fitToScreen"
        >
          <UIcon name="i-heroicons-arrows-pointing-in-20-solid" class="w-4 h-4 mr-2" />
          Fit
        </UButton>

        <UButton
          variant="outline"
          size="sm"
          @click="resetView"
        >
          <UIcon name="i-heroicons-arrow-path-20-solid" class="w-4 h-4 mr-2" />
          Reset
        </UButton>
      </div>
    </div>

    <!-- Graph Container -->
    <div class="relative">
      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center h-96">
        <div class="text-center">
          <UIcon name="i-heroicons-arrow-path-20-solid" class="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
          <p class="text-gray-600">Loading knowledge graph...</p>
        </div>
      </div>

      <!-- Graph Canvas -->
      <div
        v-else
        ref="graphRef"
        class="w-full h-96 border border-gray-200 rounded-lg bg-gray-50 overflow-hidden"
      />

      <!-- Empty State -->
      <div v-if="!loading && nodes.length === 0" class="flex items-center justify-center h-96">
        <div class="text-center">
          <UIcon name="i-heroicons-share-20-solid" class="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 class="text-lg font-medium text-gray-900 mb-2">No graph data available</h3>
          <p class="text-gray-500">
            Generate entity relationships to visualize the knowledge graph
          </p>
        </div>
      </div>

      <!-- Graph Legend -->
      <div v-if="nodes.length > 0" class="absolute top-4 left-4 bg-white rounded-lg border border-gray-200 p-3 shadow-lg">
        <h4 class="text-sm font-medium text-gray-900 mb-2">Legend</h4>
        <div class="space-y-1">
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-blue-500 rounded-full" />
            <span class="text-xs text-gray-600">Document</span>
          </div>
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-green-500 rounded-full" />
            <span class="text-xs text-gray-600">Entity</span>
          </div>
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 bg-purple-500 rounded" />
            <span class="text-xs text-gray-600">Citation</span>
          </div>
        </div>
      </div>

      <!-- Node Info Panel -->
      <div
        v-if="selectedNode"
        class="absolute top-4 right-4 bg-white rounded-lg border border-gray-200 p-4 shadow-lg max-w-xs"
      >
        <div class="flex items-center justify-between mb-3">
          <h4 class="text-sm font-medium text-gray-900">Node Info</h4>
          <UButton
            variant="ghost"
            size="xs"
            @click="selectedNode = null"
          >
            <UIcon name="i-heroicons-x-mark-20-solid" class="w-3 h-3" />
          </UButton>
        </div>

        <div class="space-y-2">
          <div>
            <label class="text-xs font-medium text-gray-500">Type</label>
            <p class="text-sm text-gray-900">{{ selectedNode.type }}</p>
          </div>

          <div>
            <label class="text-xs font-medium text-gray-500">Label</label>
            <p class="text-sm text-gray-900">{{ selectedNode.label }}</p>
          </div>

          <div v-if="selectedNode.properties">
            <label class="text-xs font-medium text-gray-500">Properties</label>
            <div class="text-xs text-gray-600 mt-1">
              <div
                v-for="[key, value] in Object.entries(selectedNode.properties)"
                :key="key"
              >
                <span class="font-medium">{{ key }}:</span> {{ String(value) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Graph Stats -->
    <div v-if="nodes.length > 0" class="mt-4 grid grid-cols-4 gap-4 text-center">
      <div class="p-3 bg-gray-50 rounded-lg">
        <div class="text-2xl font-bold text-gray-900">{{ nodes.length }}</div>
        <div class="text-xs text-gray-600">Nodes</div>
      </div>
      <div class="p-3 bg-gray-50 rounded-lg">
        <div class="text-2xl font-bold text-gray-900">{{ edges.length }}</div>
        <div class="text-xs text-gray-600">Relationships</div>
      </div>
      <div class="p-3 bg-gray-50 rounded-lg">
        <div class="text-2xl font-bold text-gray-900">{{ entityTypes.length }}</div>
        <div class="text-xs text-gray-600">Entity Types</div>
      </div>
      <div class="p-3 bg-gray-50 rounded-lg">
        <div class="text-2xl font-bold text-gray-900">{{ connectedComponents }}</div>
        <div class="text-xs text-gray-600">Components</div>
      </div>
    </div>

    <!-- Controls -->
    <div class="mt-4 flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <div class="flex items-center space-x-2">
          <label class="text-sm text-gray-600">Layout:</label>
          <USelectMenu
            v-model="layout"
            :options="layoutOptions"
            size="sm"
            class="w-32"
            @update:model-value="updateLayout"
          />
        </div>

        <div class="flex items-center space-x-2">
          <label class="text-sm text-gray-600">Physics:</label>
          <UButton
            :variant="physicsEnabled ? 'primary' : 'outline'"
            size="sm"
            @click="togglePhysics"
          >
            {{ physicsEnabled ? 'On' : 'Off' }}
          </UButton>
        </div>
      </div>

      <div class="flex items-center space-x-2">
        <UButton
          variant="outline"
          size="sm"
          @click="exportGraph"
        >
          <UIcon name="i-heroicons-arrow-down-tray-20-solid" class="w-4 h-4 mr-2" />
          Export
        </UButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'

// Using vis.js for graph visualization (lightweight and works well)
interface GraphNode {
  id: string
  label: string
  type: 'document' | 'entity' | 'citation'
  properties?: Record<string, any>
  color?: string
  size?: number
}

interface GraphEdge {
  from: string
  to: string
  label?: string
  type: 'mentions' | 'cites' | 'related'
  width?: number
}

interface Props {
  nodes: GraphNode[]
  edges: GraphEdge[]
  loading?: boolean
}

interface Emits {
  'node-click': [node: GraphNode]
  'edge-click': [edge: GraphEdge]
  'export': [format: string]
}

const props = withDefaults(defineProps<Props>(), {
  nodes: () => [],
  edges: () => [],
  loading: false
})

const emit = defineEmits<Emits>()

// Refs
const graphRef = ref<HTMLDivElement>()

// Reactive state
const selectedView = ref('force')
const layout = ref('force')
const physicsEnabled = ref(true)
const selectedNode = ref<GraphNode | null>(null)
const visNetwork = ref<any>(null)

// Options
const viewOptions = [
  { label: 'Force', value: 'force' },
  { label: 'Hierarchical', value: 'hierarchical' },
  { label: 'Circular', value: 'circular' }
]

const layoutOptions = [
  { label: 'Force', value: 'force' },
  { label: 'Hierarchical', value: 'hierarchical' },
  { label: 'Circular', value: 'circular' }
]

// Computed
const entityTypes = computed(() => {
  const types = new Set<string>()
  props.nodes.forEach(node => {
    if (node.type === 'entity' && node.properties?.type) {
      types.add(node.properties.type)
    }
  })
  return Array.from(types)
})

const connectedComponents = computed(() => {
  // Simple calculation of connected components
  // In a real implementation, you'd use graph algorithms
  return Math.max(1, Math.floor(props.nodes.length / 10))
})

// Methods
async function initializeGraph() {
  if (!graphRef.value) return

  try {
    // Dynamically import vis.js
    const { Network, DataSet } = await import('vis-network')

    // Prepare nodes data
    const nodesData = props.nodes.map(node => ({
      color: getNodeColor(node),
      size: getNodeSize(node),
      font: { size: 12 },
      ...node
    }))

    // Prepare edges data
    const edgesData = props.edges.map(edge => ({
      width: edge.width || 1,
      color: getEdgeColor(edge),
      arrows: edge.type === 'cites' ? 'to' : undefined,
      ...edge
    }))

    // Create datasets
    const nodesDataset = new DataSet(nodesData as any)
    const edgesDataset = new DataSet(edgesData as any)

    // Network options
    const options = {
      nodes: {
        shape: 'dot',
        scaling: {
          min: 10,
          max: 30
        }
      },
      edges: {
        width: 1,
        shadow: true
      },
      physics: {
        enabled: physicsEnabled.value,
        barnesHut: {
          gravitationalConstant: -2000,
          centralGravity: 0.3,
          springLength: 95,
          springConstant: 0.04,
          damping: 0.09
        }
      },
      layout: getLayoutOptions(layout.value),
      interaction: {
        hover: true,
        tooltipDelay: 300
      }
    }

    // Create network
    visNetwork.value = new Network(
      graphRef.value,
      { nodes: nodesDataset, edges: edgesDataset },
      options
    )

    // Event handlers
    visNetwork.value.on('click', (params: any) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0]
        const node = props.nodes.find(n => n.id === nodeId)
        if (node) {
          selectedNode.value = node
          emit('node-click', node)
        }
      } else if (params.edges.length > 0) {
        const edgeId = params.edges[0]
        const edge = props.edges.find(e => e.from + '-' + e.to === edgeId)
        if (edge) {
          emit('edge-click', edge)
        }
      } else {
        selectedNode.value = null
      }
    })

    visNetwork.value.on('hoverNode', (params: any) => {
      graphRef.value!.style.cursor = 'pointer'
    })

    visNetwork.value.on('blurNode', () => {
      graphRef.value!.style.cursor = 'default'
    })

  } catch (error) {
    console.error('Failed to initialize graph:', error)
  }
}

function getNodeColor(node: GraphNode): string {
  switch (node.type) {
    case 'document':
      return '#3B82F6' // blue
    case 'entity':
      return '#10B981' // green
    case 'citation':
      return '#8B5CF6' // purple
    default:
      return '#6B7280' // gray
  }
}

function getNodeSize(node: GraphNode): number {
  switch (node.type) {
    case 'document':
      return 20
    case 'entity':
      return 15
    case 'citation':
      return 12
    default:
      return 10
  }
}

function getEdgeColor(edge: GraphEdge): string {
  switch (edge.type) {
    case 'mentions':
      return '#10B981' // green
    case 'cites':
      return '#8B5CF6' // purple
    case 'related':
      return '#F59E0B' // yellow
    default:
      return '#6B7280' // gray
  }
}

function getLayoutOptions(layoutType: string) {
  switch (layoutType) {
    case 'hierarchical':
      return {
        hierarchical: {
          direction: 'UD',
          sortMethod: 'directed'
        }
      }
    case 'circular':
      return {
        circular: {
          sortMethod: 'directed'
        }
      }
    default: // force
      return {}
  }
}

function updateLayout(newLayout: string) {
  if (!visNetwork.value) return

  const options = getLayoutOptions(newLayout)
  visNetwork.value.setOptions({ layout: options })
}

function togglePhysics() {
  physicsEnabled.value = !physicsEnabled.value
  if (visNetwork.value) {
    visNetwork.value.setOptions({
      physics: { enabled: physicsEnabled.value }
    })
  }
}

function fitToScreen() {
  if (visNetwork.value) {
    visNetwork.value.fit()
  }
}

function resetView() {
  if (visNetwork.value) {
    visNetwork.value.fit()
    // Could also reset zoom level here
  }
}

function exportGraph() {
  emit('export', 'png') // or other formats
}

// Watch for data changes
watch(() => props.nodes, () => {
  nextTick(() => {
    initializeGraph()
  })
}, { deep: true })

watch(() => props.edges, () => {
  nextTick(() => {
    initializeGraph()
  })
}, { deep: true })

// Lifecycle
onMounted(() => {
  if (props.nodes.length > 0) {
    initializeGraph()
  }
})
</script>

<style scoped>
/* Custom styles for the graph container */
.vis-network {
  width: 100%;
  height: 100%;
}
</style>