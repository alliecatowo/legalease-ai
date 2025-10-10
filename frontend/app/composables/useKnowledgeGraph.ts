import { ref, computed } from 'vue'
import type { NodeDefinition, EdgeDefinition, ElementDefinition } from 'cytoscape'

export interface GraphNode {
  id: string
  label: string
  type: 'person' | 'organization' | 'location' | 'document' | 'case' | 'event' | 'law' | 'clause'
  properties: Record<string, any>
  metadata?: {
    confidence?: number
    extractedFrom?: string[]
    relatedCases?: string[]
  }
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  label: string
  type: 'related_to' | 'party_to' | 'cites' | 'mentions' | 'located_in' | 'employed_by' | 'owns' | 'references'
  weight?: number
  metadata?: {
    confidence?: number
    context?: string
  }
}

export interface GraphFilter {
  nodeTypes: string[]
  edgeTypes: string[]
  minConfidence?: number
  searchQuery?: string
}

export function useKnowledgeGraph() {
  const nodes = ref<GraphNode[]>([])
  const edges = ref<GraphEdge[]>([])
  const selectedNode = ref<GraphNode | null>(null)
  const selectedEdge = ref<GraphEdge | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Filters
  const activeFilters = ref<GraphFilter>({
    nodeTypes: [],
    edgeTypes: [],
    minConfidence: 0,
    searchQuery: ''
  })

  // Layout options
  const layoutType = ref<'cose' | 'circle' | 'grid' | 'breadthfirst' | 'concentric'>('cose')

  // Node type colors for consistency
  const nodeTypeColors: Record<string, string> = {
    person: '#3B82F6',
    organization: '#8B5CF6',
    location: '#10B981',
    document: '#F59E0B',
    case: '#EF4444',
    event: '#EC4899',
    law: '#6366F1',
    clause: '#14B8A6'
  }

  // Node type icons
  const nodeTypeIcons: Record<string, string> = {
    person: 'i-lucide-user',
    organization: 'i-lucide-building',
    location: 'i-lucide-map-pin',
    document: 'i-lucide-file-text',
    case: 'i-lucide-briefcase',
    event: 'i-lucide-calendar',
    law: 'i-lucide-scale',
    clause: 'i-lucide-file-signature'
  }

  // Filter nodes and edges based on active filters
  const filteredNodes = computed(() => {
    let filtered = nodes.value

    // Filter by node types
    if (activeFilters.value.nodeTypes.length > 0) {
      filtered = filtered.filter(node =>
        activeFilters.value.nodeTypes.includes(node.type)
      )
    }

    // Filter by search query
    if (activeFilters.value.searchQuery) {
      const query = activeFilters.value.searchQuery.toLowerCase()
      filtered = filtered.filter(node =>
        node.label.toLowerCase().includes(query) ||
        Object.values(node.properties).some(val =>
          String(val).toLowerCase().includes(query)
        )
      )
    }

    // Filter by confidence
    if (activeFilters.value.minConfidence && activeFilters.value.minConfidence > 0) {
      filtered = filtered.filter(node =>
        !node.metadata?.confidence ||
        node.metadata.confidence >= (activeFilters.value.minConfidence || 0)
      )
    }

    return filtered
  })

  const filteredEdges = computed(() => {
    let filtered = edges.value

    // Only include edges where both source and target are in filtered nodes
    const filteredNodeIds = new Set(filteredNodes.value.map(n => n.id))
    filtered = filtered.filter(edge =>
      filteredNodeIds.has(edge.source) && filteredNodeIds.has(edge.target)
    )

    // Filter by edge types
    if (activeFilters.value.edgeTypes.length > 0) {
      filtered = filtered.filter(edge =>
        activeFilters.value.edgeTypes.includes(edge.type)
      )
    }

    // Filter by confidence
    if (activeFilters.value.minConfidence && activeFilters.value.minConfidence > 0) {
      filtered = filtered.filter(edge =>
        !edge.metadata?.confidence ||
        edge.metadata.confidence >= (activeFilters.value.minConfidence || 0)
      )
    }

    return filtered
  })

  // Convert to Cytoscape elements format
  const cytoscapeElements = computed((): ElementDefinition[] => {
    const nodeElements: NodeDefinition[] = filteredNodes.value.map(node => ({
      data: {
        id: node.id,
        label: node.label,
        type: node.type,
        color: nodeTypeColors[node.type] || '#6B7280',
        ...node.properties,
        metadata: node.metadata
      }
    }))

    const edgeElements: EdgeDefinition[] = filteredEdges.value.map(edge => ({
      data: {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label,
        type: edge.type,
        weight: edge.weight || 1,
        metadata: edge.metadata
      }
    }))

    return [...nodeElements, ...edgeElements]
  })

  // Load graph data
  async function loadGraph(caseId?: string, documentId?: string) {
    isLoading.value = true
    error.value = null

    try {
      // TODO: Replace with real API call
      // const response = await api.knowledgeGraph.get({ caseId, documentId })
      // nodes.value = response.nodes
      // edges.value = response.edges

      // Mock delay
      await new Promise(resolve => setTimeout(resolve, 500))

      // Load mock data
      const mockData = getMockGraphData()
      nodes.value = mockData.nodes
      edges.value = mockData.edges
    } catch (err) {
      error.value = 'Failed to load knowledge graph'
      console.error(err)
    } finally {
      isLoading.value = false
    }
  }

  // Add node
  function addNode(node: GraphNode) {
    nodes.value.push(node)
    // TODO: Save to backend
  }

  // Add edge
  function addEdge(edge: GraphEdge) {
    edges.value.push(edge)
    // TODO: Save to backend
  }

  // Remove node (and connected edges)
  function removeNode(nodeId: string) {
    nodes.value = nodes.value.filter(n => n.id !== nodeId)
    edges.value = edges.value.filter(e =>
      e.source !== nodeId && e.target !== nodeId
    )
    // TODO: Save to backend
  }

  // Remove edge
  function removeEdge(edgeId: string) {
    edges.value = edges.value.filter(e => e.id !== edgeId)
    // TODO: Save to backend
  }

  // Select node
  function selectNode(nodeId: string | null) {
    if (nodeId) {
      selectedNode.value = nodes.value.find(n => n.id === nodeId) || null
    } else {
      selectedNode.value = null
    }
    selectedEdge.value = null
  }

  // Select edge
  function selectEdge(edgeId: string | null) {
    if (edgeId) {
      selectedEdge.value = edges.value.find(e => e.id === edgeId) || null
    } else {
      selectedEdge.value = null
    }
    selectedNode.value = null
  }

  // Get node neighbors
  function getNodeNeighbors(nodeId: string): GraphNode[] {
    const neighborIds = new Set<string>()

    edges.value.forEach(edge => {
      if (edge.source === nodeId) {
        neighborIds.add(edge.target)
      } else if (edge.target === nodeId) {
        neighborIds.add(edge.source)
      }
    })

    return nodes.value.filter(n => neighborIds.has(n.id))
  }

  // Get node edges
  function getNodeEdges(nodeId: string): GraphEdge[] {
    return edges.value.filter(e =>
      e.source === nodeId || e.target === nodeId
    )
  }

  // Update filters
  function updateFilters(filters: Partial<GraphFilter>) {
    activeFilters.value = { ...activeFilters.value, ...filters }
  }

  // Clear filters
  function clearFilters() {
    activeFilters.value = {
      nodeTypes: [],
      edgeTypes: [],
      minConfidence: 0,
      searchQuery: ''
    }
  }

  return {
    nodes,
    edges,
    selectedNode,
    selectedEdge,
    isLoading,
    error,
    activeFilters,
    layoutType,
    nodeTypeColors,
    nodeTypeIcons,
    filteredNodes,
    filteredEdges,
    cytoscapeElements,
    loadGraph,
    addNode,
    addEdge,
    removeNode,
    removeEdge,
    selectNode,
    selectEdge,
    getNodeNeighbors,
    getNodeEdges,
    updateFilters,
    clearFilters
  }
}

// Mock data generator
function getMockGraphData(): { nodes: GraphNode[], edges: GraphEdge[] } {
  const nodes: GraphNode[] = [
    {
      id: 'node-1',
      label: 'Acme Corporation',
      type: 'organization',
      properties: {
        industry: 'Technology',
        founded: '2010',
        employees: '5000+'
      },
      metadata: {
        confidence: 0.98,
        extractedFrom: ['doc-1', 'doc-2']
      }
    },
    {
      id: 'node-2',
      label: 'Global Tech Inc',
      type: 'organization',
      properties: {
        industry: 'Software',
        founded: '2005'
      },
      metadata: {
        confidence: 0.96,
        extractedFrom: ['doc-1']
      }
    },
    {
      id: 'node-3',
      label: 'Sarah Johnson',
      type: 'person',
      properties: {
        role: 'Attorney',
        organization: 'Johnson & Partners LLP'
      },
      metadata: {
        confidence: 0.95,
        extractedFrom: ['doc-1', 'doc-3']
      }
    },
    {
      id: 'node-4',
      label: 'Master Services Agreement',
      type: 'document',
      properties: {
        documentType: 'contract',
        date: '2024-01-15',
        pages: 15
      },
      metadata: {
        confidence: 1.0,
        extractedFrom: ['doc-1']
      }
    },
    {
      id: 'node-5',
      label: 'Delaware Superior Court',
      type: 'location',
      properties: {
        jurisdiction: 'Delaware',
        type: 'court'
      },
      metadata: {
        confidence: 0.99,
        extractedFrom: ['doc-1', 'doc-2']
      }
    },
    {
      id: 'node-6',
      label: 'CV-2024-1234',
      type: 'case',
      properties: {
        status: 'active',
        filedDate: '2024-01-20'
      },
      metadata: {
        confidence: 1.0
      }
    },
    {
      id: 'node-7',
      label: 'Initial Conference',
      type: 'event',
      properties: {
        date: '2024-03-15',
        type: 'hearing'
      },
      metadata: {
        confidence: 0.92
      }
    },
    {
      id: 'node-8',
      label: 'Delaware Contract Law',
      type: 'law',
      properties: {
        jurisdiction: 'Delaware',
        area: 'Contract Law'
      },
      metadata: {
        confidence: 0.88
      }
    },
    {
      id: 'node-9',
      label: 'Indemnification Clause',
      type: 'clause',
      properties: {
        section: '12.3',
        documentId: 'doc-1'
      },
      metadata: {
        confidence: 0.94
      }
    },
    {
      id: 'node-10',
      label: 'John Smith',
      type: 'person',
      properties: {
        role: 'CEO',
        organization: 'Acme Corporation'
      },
      metadata: {
        confidence: 0.91
      }
    }
  ]

  const edges: GraphEdge[] = [
    {
      id: 'edge-1',
      source: 'node-1',
      target: 'node-2',
      label: 'contract with',
      type: 'related_to',
      weight: 0.9,
      metadata: { confidence: 0.95, context: 'Master Services Agreement' }
    },
    {
      id: 'edge-2',
      source: 'node-1',
      target: 'node-6',
      label: 'plaintiff in',
      type: 'party_to',
      weight: 1.0,
      metadata: { confidence: 1.0 }
    },
    {
      id: 'edge-3',
      source: 'node-2',
      target: 'node-6',
      label: 'defendant in',
      type: 'party_to',
      weight: 1.0,
      metadata: { confidence: 1.0 }
    },
    {
      id: 'edge-4',
      source: 'node-3',
      target: 'node-6',
      label: 'attorney for',
      type: 'party_to',
      weight: 0.8,
      metadata: { confidence: 0.95 }
    },
    {
      id: 'edge-5',
      source: 'node-4',
      target: 'node-6',
      label: 'evidence in',
      type: 'related_to',
      weight: 0.9,
      metadata: { confidence: 0.98 }
    },
    {
      id: 'edge-6',
      source: 'node-6',
      target: 'node-5',
      label: 'filed in',
      type: 'located_in',
      weight: 1.0,
      metadata: { confidence: 1.0 }
    },
    {
      id: 'edge-7',
      source: 'node-7',
      target: 'node-6',
      label: 'scheduled for',
      type: 'related_to',
      weight: 0.85,
      metadata: { confidence: 0.92 }
    },
    {
      id: 'edge-8',
      source: 'node-8',
      target: 'node-6',
      label: 'governs',
      type: 'references',
      weight: 0.7,
      metadata: { confidence: 0.88 }
    },
    {
      id: 'edge-9',
      source: 'node-9',
      target: 'node-4',
      label: 'contained in',
      type: 'references',
      weight: 1.0,
      metadata: { confidence: 0.94 }
    },
    {
      id: 'edge-10',
      source: 'node-10',
      target: 'node-1',
      label: 'CEO of',
      type: 'employed_by',
      weight: 0.95,
      metadata: { confidence: 0.91 }
    },
    {
      id: 'edge-11',
      source: 'node-3',
      target: 'node-1',
      label: 'represents',
      type: 'related_to',
      weight: 0.85,
      metadata: { confidence: 0.93 }
    },
    {
      id: 'edge-12',
      source: 'node-1',
      target: 'node-4',
      label: 'signed',
      type: 'related_to',
      weight: 0.9,
      metadata: { confidence: 0.96 }
    },
    {
      id: 'edge-13',
      source: 'node-2',
      target: 'node-4',
      label: 'signed',
      type: 'related_to',
      weight: 0.9,
      metadata: { confidence: 0.96 }
    }
  ]

  return { nodes, edges }
}
