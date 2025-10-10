<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import cytoscape, { type Core, type ElementDefinition, type LayoutOptions } from 'cytoscape'

const props = defineProps<{
  elements: ElementDefinition[]
  layout?: 'cose' | 'circle' | 'grid' | 'breadthfirst' | 'concentric'
  selectedNodeId?: string | null
  selectedEdgeId?: string | null
}>()

const emit = defineEmits<{
  'node-click': [nodeId: string]
  'edge-click': [edgeId: string]
  'node-hover': [nodeId: string | null]
  'canvas-click': []
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const cy = ref<Core | null>(null)
const isInitialized = ref(false)

// Cytoscape stylesheet
const cytoscapeStyle = [
  {
    selector: 'node',
    style: {
      'background-color': 'data(color)',
      'label': 'data(label)',
      'text-valign': 'center',
      'text-halign': 'center',
      'color': '#ffffff',
      'text-outline-color': 'data(color)',
      'text-outline-width': 2,
      'font-size': '12px',
      'font-weight': 'bold',
      'width': 60,
      'height': 60,
      'border-width': 2,
      'border-color': '#ffffff',
      'overlay-padding': '6px',
      'z-index': 10
    }
  },
  {
    selector: 'node:selected',
    style: {
      'border-width': 4,
      'border-color': '#3B82F6',
      'overlay-opacity': 0.3,
      'overlay-color': '#3B82F6'
    }
  },
  {
    selector: 'node:active',
    style: {
      'overlay-opacity': 0.3,
      'overlay-color': '#3B82F6'
    }
  },
  {
    selector: 'edge',
    style: {
      'width': 'data(weight)',
      'line-color': '#94A3B8',
      'target-arrow-color': '#94A3B8',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      'label': 'data(label)',
      'font-size': '10px',
      'text-rotation': 'autorotate',
      'text-margin-y': -10,
      'color': '#64748B',
      'text-background-color': '#ffffff',
      'text-background-opacity': 0.8,
      'text-background-padding': '3px'
    }
  },
  {
    selector: 'edge:selected',
    style: {
      'line-color': '#3B82F6',
      'target-arrow-color': '#3B82F6',
      'width': 3
    }
  },
  {
    selector: '.highlighted',
    style: {
      'border-width': 4,
      'border-color': '#F59E0B',
      'z-index': 999
    }
  },
  {
    selector: '.dimmed',
    style: {
      'opacity': 0.3
    }
  }
]

// Initialize Cytoscape
async function initializeCytoscape() {
  if (!containerRef.value || isInitialized.value) return

  cy.value = cytoscape({
    container: containerRef.value,
    elements: props.elements,
    style: cytoscapeStyle,
    layout: getLayoutOptions(props.layout || 'cose'),
    minZoom: 0.3,
    maxZoom: 3,
    wheelSensitivity: 0.2
  })

  // Event handlers
  cy.value.on('tap', 'node', (event) => {
    const nodeId = event.target.id()
    emit('node-click', nodeId)
  })

  cy.value.on('tap', 'edge', (event) => {
    const edgeId = event.target.id()
    emit('edge-click', edgeId)
  })

  cy.value.on('tap', (event) => {
    if (event.target === cy.value) {
      emit('canvas-click')
    }
  })

  cy.value.on('mouseover', 'node', (event) => {
    const nodeId = event.target.id()
    emit('node-hover', nodeId)
    event.target.style('cursor', 'pointer')
  })

  cy.value.on('mouseout', 'node', () => {
    emit('node-hover', null)
  })

  isInitialized.value = true
}

// Get layout options
function getLayoutOptions(layoutType: string): LayoutOptions {
  const baseOptions = {
    animate: true,
    animationDuration: 500,
    fit: true,
    padding: 50
  }

  switch (layoutType) {
    case 'cose':
      return {
        ...baseOptions,
        name: 'cose',
        idealEdgeLength: 100,
        nodeOverlap: 20,
        refresh: 20,
        randomize: false,
        componentSpacing: 100,
        nodeRepulsion: 400000,
        edgeElasticity: 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: 1000,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0
      }
    case 'circle':
      return {
        ...baseOptions,
        name: 'circle',
        radius: 300,
        startAngle: -Math.PI / 2
      }
    case 'grid':
      return {
        ...baseOptions,
        name: 'grid',
        rows: undefined,
        cols: undefined,
        position: undefined
      }
    case 'breadthfirst':
      return {
        ...baseOptions,
        name: 'breadthfirst',
        directed: true,
        spacingFactor: 1.5
      }
    case 'concentric':
      return {
        ...baseOptions,
        name: 'concentric',
        minNodeSpacing: 100,
        concentric: (node: any) => node.degree(),
        levelWidth: () => 2
      }
    default:
      return {
        ...baseOptions,
        name: 'cose'
      }
  }
}

// Update elements
function updateElements() {
  if (!cy.value) return

  cy.value.elements().remove()
  cy.value.add(props.elements)
  cy.value.layout(getLayoutOptions(props.layout || 'cose')).run()
}

// Update layout
function updateLayout() {
  if (!cy.value) return
  cy.value.layout(getLayoutOptions(props.layout || 'cose')).run()
}

// Update selection
function updateSelection() {
  if (!cy.value) return

  // Clear previous selections
  cy.value.elements().removeClass('highlighted dimmed')
  cy.value.elements().unselect()

  if (props.selectedNodeId) {
    const node = cy.value.getElementById(props.selectedNodeId)
    node.select()

    // Highlight connected edges and nodes
    const connectedEdges = node.connectedEdges()
    const connectedNodes = connectedEdges.connectedNodes()

    node.addClass('highlighted')
    connectedEdges.addClass('highlighted')
    connectedNodes.addClass('highlighted')

    // Dim unconnected nodes
    cy.value.nodes().not(connectedNodes).not(node).addClass('dimmed')
    cy.value.edges().not(connectedEdges).addClass('dimmed')
  } else if (props.selectedEdgeId) {
    const edge = cy.value.getElementById(props.selectedEdgeId)
    edge.select()
    edge.addClass('highlighted')
  }
}

// Public methods
function fit() {
  if (!cy.value) return
  cy.value.fit(undefined, 50)
}

function zoomIn() {
  if (!cy.value) return
  cy.value.zoom({
    level: cy.value.zoom() * 1.2,
    renderedPosition: {
      x: cy.value.width() / 2,
      y: cy.value.height() / 2
    }
  })
}

function zoomOut() {
  if (!cy.value) return
  cy.value.zoom({
    level: cy.value.zoom() * 0.8,
    renderedPosition: {
      x: cy.value.width() / 2,
      y: cy.value.height() / 2
    }
  })
}

function resetZoom() {
  if (!cy.value) return
  cy.value.fit(undefined, 50)
}

function center(nodeId?: string) {
  if (!cy.value) return

  if (nodeId) {
    const node = cy.value.getElementById(nodeId)
    cy.value.center(node)
  } else {
    cy.value.center()
  }
}

function exportImage(): string | null {
  if (!cy.value) return null
  return cy.value.png({ scale: 2 })
}

// Expose public methods
defineExpose({
  fit,
  zoomIn,
  zoomOut,
  resetZoom,
  center,
  exportImage,
  cy
})

// Watch for changes
watch(() => props.elements, () => {
  nextTick(() => {
    updateElements()
  })
}, { deep: true })

watch(() => props.layout, () => {
  nextTick(() => {
    updateLayout()
  })
})

watch(() => [props.selectedNodeId, props.selectedEdgeId], () => {
  nextTick(() => {
    updateSelection()
  })
})

onMounted(() => {
  nextTick(() => {
    initializeCytoscape()
  })
})
</script>

<template>
  <div ref="containerRef" class="w-full h-full bg-default" />
</template>

<style scoped>
/* Cytoscape requires explicit dimensions */
div {
  width: 100%;
  height: 100%;
}
</style>
