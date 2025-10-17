<script setup lang="ts">
import { ref, computed } from 'vue'

definePageMeta({
  layout: 'default'
})

const selectedNode = ref<any>(null)
const showNodeDrawer = ref(false)
const showFilters = ref(true)

// Graph filters
const filters = ref({
  nodeTypes: ['case', 'document', 'person', 'organization'],
  relationshipTypes: ['cited_by', 'related_to', 'party_to'],
  timeRange: 'all',
  strengthThreshold: 0.3
})

const nodeTypes = [
  { label: 'Cases', value: 'case', icon: 'i-lucide-briefcase', color: 'primary', iconClass: 'text-primary', bgClass: 'bg-primary', count: 45 },
  { label: 'Documents', value: 'document', icon: 'i-lucide-file-text', color: 'info', iconClass: 'text-info', bgClass: 'bg-info', count: 189 },
  { label: 'People', value: 'person', icon: 'i-lucide-user', color: 'success', iconClass: 'text-success', bgClass: 'bg-success', count: 67 },
  { label: 'Organizations', value: 'organization', icon: 'i-lucide-building', color: 'warning', iconClass: 'text-warning', bgClass: 'bg-warning', count: 34 },
  { label: 'Courts', value: 'court', icon: 'i-lucide-landmark', color: 'error', iconClass: 'text-error', bgClass: 'bg-error', count: 12 },
  { label: 'Citations', value: 'citation', icon: 'i-lucide-link', color: 'neutral', iconClass: 'text-neutral', bgClass: 'bg-neutral', count: 98 }
]

const relationshipTypes = [
  { label: 'Cited by', value: 'cited_by', count: 234 },
  { label: 'Related to', value: 'related_to', count: 456 },
  { label: 'Party to', value: 'party_to', count: 189 },
  { label: 'Precedent for', value: 'precedent_for', count: 123 }
]

const layoutModes = [
  { label: 'Force-Directed', value: 'force', icon: 'i-lucide-git-fork' },
  { label: 'Hierarchical', value: 'hierarchical', icon: 'i-lucide-git-branch' },
  { label: 'Circular', value: 'circular', icon: 'i-lucide-circle-dot' },
  { label: 'Timeline', value: 'timeline', icon: 'i-lucide-timeline' }
]

const selectedLayout = ref('force')

// Mock node data - In reality this would come from Neo4j
const mockNode = {
  id: 'case-1',
  type: 'case',
  label: 'Acme Corp v. Global Tech',
  properties: {
    caseNumber: '2024-CV-12345',
    status: 'active',
    court: 'Superior Court of California',
    filed: '2024-01-15'
  },
  connections: 15,
  relatedNodes: [
    { id: 'doc-1', type: 'document', label: 'Master Services Agreement.pdf', relationship: 'contains' },
    { id: 'person-1', type: 'person', label: 'Jane Smith', relationship: 'attorney_for' },
    { id: 'org-1', type: 'organization', label: 'Acme Corporation', relationship: 'party_to' }
  ]
}

function selectNode(node: any) {
  selectedNode.value = node
  showNodeDrawer.value = true
}

function exportGraph(format: string) {
  console.log('Exporting graph as:', format)
  // TODO: Implement graph export
}

const selectedNodeTypes = computed({
  get: () => filters.value.nodeTypes,
  set: (value) => {
    filters.value.nodeTypes = value
  }
})

const selectedRelationshipTypes = computed({
  get: () => filters.value.relationshipTypes,
  set: (value) => {
    filters.value.relationshipTypes = value
  }
})
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Knowledge Graph">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #trailing>
          <UFieldGroup>
            <UTooltip text="Filters">
              <UButton
                icon="i-lucide-filter"
                :variant="showFilters ? 'soft' : 'ghost'"
                color="neutral"
                @click="showFilters = !showFilters"
              />
            </UTooltip>
            <UDropdownMenu>
              <UButton icon="i-lucide-download" color="neutral" variant="outline" label="Export" />
              <template #content>
                <div class="p-1">
                  <UButton label="Export as PNG" icon="i-lucide-image" color="neutral" variant="ghost" block @click="exportGraph('png')" />
                  <UButton label="Export as SVG" icon="i-lucide-file-image" color="neutral" variant="ghost" block @click="exportGraph('svg')" />
                  <UButton label="Export as GraphML" icon="i-lucide-file-code" color="neutral" variant="ghost" block @click="exportGraph('graphml')" />
                  <UButton label="Export as JSON" icon="i-lucide-braces" color="neutral" variant="ghost" block @click="exportGraph('json')" />
                </div>
              </template>
            </UDropdownMenu>
          </UFieldGroup>
        </template>
      </UDashboardNavbar>
    </template>

    <div class="flex h-[calc(100vh-64px)]">
      <!-- Filters Sidebar -->
      <div v-if="showFilters" class="w-80 border-r border-default bg-default overflow-y-auto">
        <div class="p-4 space-y-6">
          <!-- Layout Selection -->
          <div class="space-y-3">
            <label class="text-sm font-medium text-highlighted">Layout</label>
            <USelectMenu
              v-model="selectedLayout"
              :items="layoutModes"
              value-key="value"
            >
              <template #leading="{ item }">
                <UIcon v-if="item" :name="item.icon" class="size-4" />
              </template>
            </USelectMenu>
          </div>

          <!-- Node Types Filter -->
          <UAccordion
            :items="[
              { label: 'Node Types', slot: 'nodetypes', defaultOpen: true },
              { label: 'Relationships', slot: 'relationships' },
              { label: 'Connection Strength', slot: 'strength' }
            ]"
            :default-value="['0']"
            type="multiple"
          >
            <template #nodetypes>
              <UCheckboxGroup v-model="selectedNodeTypes" class="space-y-2">
                <div v-for="type in nodeTypes" :key="type.value" class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <UCheckbox :value="type.value" />
                    <UIcon :name="type.icon" class="size-4" :class="type.iconClass" />
                    <span class="text-sm">{{ type.label }}</span>
                  </div>
                  <span class="text-xs text-dimmed">{{ type.count }}</span>
                </div>
              </UCheckboxGroup>
            </template>

            <template #relationships>
              <UCheckboxGroup v-model="selectedRelationshipTypes" class="space-y-2">
                <div v-for="type in relationshipTypes" :key="type.value" class="flex items-center justify-between">
                  <UCheckbox :value="type.value" :label="type.label" />
                  <span class="text-xs text-dimmed">{{ type.count }}</span>
                </div>
              </UCheckboxGroup>
            </template>

            <template #strength>
              <div class="space-y-3">
                <div class="flex items-center justify-between text-sm">
                  <span class="text-muted">Minimum Strength</span>
                  <span class="font-medium">{{ Math.round(filters.strengthThreshold * 100) }}%</span>
                </div>
                <USlider v-model="filters.strengthThreshold" :min="0" :max="1" :step="0.1" />
                <div class="flex justify-between text-xs text-dimmed">
                  <span>Weak</span>
                  <span>Strong</span>
                </div>
              </div>
            </template>
          </UAccordion>

          <!-- Legend -->
          <div class="space-y-3 pt-4 border-t border-default">
            <h3 class="text-sm font-medium text-highlighted">Legend</h3>
            <div class="space-y-2">
              <div v-for="type in nodeTypes.filter(t => selectedNodeTypes.includes(t.value))" :key="type.value" class="flex items-center gap-2">
                <div class="size-3 rounded-full" :class="type.bgClass" />
                <span class="text-sm text-muted">{{ type.label }}</span>
              </div>
            </div>
          </div>

          <!-- Quick Actions -->
          <div class="space-y-2 pt-4 border-t border-default">
            <UButton label="Reset View" icon="i-lucide-maximize-2" color="neutral" variant="outline" block />
            <UButton label="Expand All" icon="i-lucide-maximize" color="neutral" variant="outline" block />
            <UButton label="Collapse All" icon="i-lucide-minimize" color="neutral" variant="outline" block />
          </div>
        </div>
      </div>

      <!-- Graph Visualization Area -->
      <div class="flex-1 relative bg-elevated/30">
        <!-- Graph Container -->
        <div class="absolute inset-0 flex items-center justify-center">
          <!-- Placeholder for actual graph visualization -->
          <div class="text-center max-w-2xl p-8">
            <UIcon name="i-lucide-network" class="size-24 text-primary mx-auto mb-6" />
            <h2 class="text-3xl font-bold mb-4">Interactive Knowledge Graph</h2>
            <p class="text-muted mb-8">
              Visualize complex relationships between cases, documents, parties, and legal entities.
              The graph visualization will render here using D3.js or Cytoscape.js.
            </p>

            <!-- Mock Graph Preview -->
            <UCard :ui="{ body: 'space-y-4' }">
              <div class="text-left">
                <h3 class="font-semibold mb-2">Graph Features:</h3>
                <ul class="space-y-2 text-sm text-muted">
                  <li class="flex items-center gap-2">
                    <UIcon name="i-lucide-check" class="size-4 text-success" />
                    <span>Interactive node exploration with drag & zoom</span>
                  </li>
                  <li class="flex items-center gap-2">
                    <UIcon name="i-lucide-check" class="size-4 text-success" />
                    <span>Click nodes to see details and connections</span>
                  </li>
                  <li class="flex items-center gap-2">
                    <UIcon name="i-lucide-check" class="size-4 text-success" />
                    <span>Multiple layout algorithms (force, hierarchical, circular)</span>
                  </li>
                  <li class="flex items-center gap-2">
                    <UIcon name="i-lucide-check" class="size-4 text-success" />
                    <span>Filter by node type and relationship strength</span>
                  </li>
                  <li class="flex items-center gap-2">
                    <UIcon name="i-lucide-check" class="size-4 text-success" />
                    <span>Export as image or structured data (GraphML, JSON)</span>
                  </li>
                </ul>
              </div>

              <!-- Demo Button -->
              <UButton
                label="Click to Explore Sample Node"
                icon="i-lucide-circle-dot"
                color="primary"
                size="lg"
                block
                @click="selectNode(mockNode)"
              />

              <UAlert
                icon="i-lucide-info"
                color="info"
                variant="soft"
                title="Coming Soon"
                description="Full graph visualization with Neo4j integration will be implemented using D3.js force-directed graph."
              />
            </UCard>
          </div>
        </div>

        <!-- Graph Controls Overlay -->
        <div class="absolute bottom-4 left-4 flex items-center gap-2">
          <UFieldGroup>
            <UTooltip text="Zoom In">
              <UButton icon="i-lucide-zoom-in" color="neutral" variant="outline" />
            </UTooltip>
            <UTooltip text="Zoom Out">
              <UButton icon="i-lucide-zoom-out" color="neutral" variant="outline" />
            </UTooltip>
            <UTooltip text="Reset Zoom">
              <UButton icon="i-lucide-maximize-2" color="neutral" variant="outline" />
            </UTooltip>
          </UFieldGroup>
        </div>

        <!-- Graph Stats Overlay -->
        <div class="absolute top-4 right-4 space-y-2">
          <UCard :ui="{ body: 'p-3' }">
            <div class="text-sm space-y-1">
              <div class="flex items-center justify-between gap-4">
                <span class="text-muted">Nodes:</span>
                <span class="font-semibold">445</span>
              </div>
              <div class="flex items-center justify-between gap-4">
                <span class="text-muted">Edges:</span>
                <span class="font-semibold">1,102</span>
              </div>
              <div class="flex items-center justify-between gap-4">
                <span class="text-muted">Visible:</span>
                <span class="font-semibold">{{ selectedNodeTypes.length * 50 }}</span>
              </div>
            </div>
          </UCard>
        </div>
      </div>

      <!-- Node Detail Drawer -->
      <UDrawer v-model:open="showNodeDrawer" direction="right" :ui="{ content: 'w-96' }">
        <template #header>
          <div class="flex items-center gap-3">
            <UIcon
              :name="nodeTypes.find(t => t.value === selectedNode?.type)?.icon || 'i-lucide-circle'"
              class="size-6"
              :class="nodeTypes.find(t => t.value === selectedNode?.type)?.iconClass || 'text-neutral'"
            />
            <div>
              <h3 class="font-semibold">{{ selectedNode?.label }}</h3>
              <p class="text-sm text-muted capitalize">{{ selectedNode?.type }}</p>
            </div>
          </div>
        </template>

        <template #body>
          <div v-if="selectedNode" class="space-y-6">
            <!-- Properties -->
            <div>
              <h4 class="text-sm font-medium mb-3">Properties</h4>
              <div class="space-y-2">
                <div v-for="(value, key) in selectedNode.properties" :key="key" class="flex items-center justify-between text-sm">
                  <span class="text-muted capitalize">{{ key.replace('_', ' ') }}:</span>
                  <span class="font-medium">{{ value }}</span>
                </div>
              </div>
            </div>

            <!-- Connections -->
            <div>
              <h4 class="text-sm font-medium mb-3">Connected Nodes ({{ selectedNode.connections }})</h4>
              <div class="space-y-2">
                <UCard v-for="node in selectedNode.relatedNodes" :key="node.id" :ui="{ body: 'p-3' }">
                  <div class="flex items-start gap-3">
                    <UIcon
                      :name="nodeTypes.find(t => t.value === node.type)?.icon || 'i-lucide-circle'"
                      class="size-5"
                      :class="nodeTypes.find(t => t.value === node.type)?.iconClass || 'text-neutral'"
                    />
                    <div class="flex-1 min-w-0">
                      <p class="font-medium text-sm truncate">{{ node.label }}</p>
                      <p class="text-xs text-muted">{{ node.relationship.replace('_', ' ') }}</p>
                    </div>
                  </div>
                </UCard>
              </div>
            </div>

            <!-- Actions -->
            <div class="space-y-2">
              <UButton label="View Details" icon="i-lucide-external-link" color="primary" block />
              <UButton label="Expand Connections" icon="i-lucide-git-fork" color="neutral" variant="outline" block />
              <UButton label="Add to Case" icon="i-lucide-plus-circle" color="neutral" variant="outline" block />
            </div>
          </div>
        </template>
      </UDrawer>
    </div>
  </UDashboardPanel>
</template>
