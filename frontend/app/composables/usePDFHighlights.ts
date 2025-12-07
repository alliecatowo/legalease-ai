import { ref, computed } from 'vue'

export interface BoundingBox {
  page: number
  x: number
  y: number
  width: number
  height: number
  text: string
  type: 'entity' | 'clause' | 'highlight' | 'annotation'
  entityType?: string
  confidence?: number
  id: string
}

export interface Entity {
  id: string
  text: string
  type: string
  boundingBoxes: BoundingBox[]
  confidence: number
  metadata?: Record<string, any>
}

export interface Annotation {
  id: string
  page: number
  boundingBox: BoundingBox
  text: string
  note: string
  createdAt: string
  createdBy?: string
}

export function usePDFHighlights() {
  const entities = ref<Entity[]>([])
  const annotations = ref<Annotation[]>([])
  const selectedEntity = ref<Entity | null>(null)
  const selectedAnnotation = ref<Annotation | null>(null)
  const hoveredBoundingBox = ref<BoundingBox | null>(null)
  const searchHighlights = ref<BoundingBox[]>([])
  const currentPage = ref(1)
  const totalPages = ref(0)
  const zoomLevel = ref(1.0)

  // Entity type colors (matching RAGFlow style)
  const entityTypeColors: Record<string, string> = {
    PERSON: '#3B82F6', // blue
    ORGANIZATION: '#8B5CF6', // purple
    LOCATION: '#10B981', // green
    DATE: '#F59E0B', // amber
    MONEY: '#EF4444', // red
    COURT: '#EC4899', // pink
    CITATION: '#6366F1', // indigo
    LAW: '#14B8A6', // teal
    CLAUSE: '#F97316' // orange
  }

  // Get all bounding boxes for current page
  const currentPageBoundingBoxes = computed(() => {
    const boxes: BoundingBox[] = []

    // Add entity bounding boxes
    entities.value.forEach((entity) => {
      entity.boundingBoxes
        .filter(box => box.page === currentPage.value)
        .forEach(box => boxes.push(box))
    })

    // Add annotation bounding boxes
    annotations.value
      .filter(ann => ann.page === currentPage.value)
      .forEach(ann => boxes.push(ann.boundingBox))

    // Add search highlights
    searchHighlights.value
      .filter(box => box.page === currentPage.value)
      .forEach(box => boxes.push(box))

    return boxes
  })

  // Get color for bounding box
  function getBoundingBoxColor(box: BoundingBox): string {
    if (box.type === 'entity' && box.entityType) {
      return entityTypeColors[box.entityType] || '#6B7280'
    }
    if (box.type === 'highlight') {
      return '#FBBF24' // yellow for search highlights
    }
    if (box.type === 'annotation') {
      return '#8B5CF6' // purple for user annotations
    }
    if (box.type === 'clause') {
      return entityTypeColors.CLAUSE
    }
    return '#6B7280' // gray default
  }

  // Add entity (from backend)
  function addEntity(entity: Entity) {
    entities.value.push(entity)
  }

  // Add annotation (user-created)
  function addAnnotation(annotation: Annotation) {
    annotations.value.push(annotation)
    // TODO: Save to backend
  }

  // Delete annotation
  function deleteAnnotation(id: string) {
    annotations.value = annotations.value.filter(a => a.id !== id)
    if (selectedAnnotation.value?.id === id) {
      selectedAnnotation.value = null
    }
    // TODO: Delete from backend
  }

  // Select entity
  function selectEntity(entity: Entity | null) {
    selectedEntity.value = entity
    selectedAnnotation.value = null
  }

  // Select annotation
  function selectAnnotation(annotation: Annotation | null) {
    selectedAnnotation.value = annotation
    selectedEntity.value = null
  }

  // Search and highlight text
  function searchText(query: string, searchResults: any[]) {
    // Convert search results to bounding boxes
    // TODO: Get actual bounding boxes from backend
    searchHighlights.value = searchResults.map((result, idx) => ({
      page: result.page || 1,
      x: result.x || 0,
      y: result.y || 0,
      width: result.width || 100,
      height: result.height || 20,
      text: result.text,
      type: 'highlight',
      id: `search-${idx}`
    }))
  }

  // Clear search highlights
  function clearSearchHighlights() {
    searchHighlights.value = []
  }

  // Navigate to bounding box
  function navigateToBoundingBox(box: BoundingBox) {
    currentPage.value = box.page
    // Scroll to box position (handled by parent component)
  }

  // Get entity by ID
  function getEntityById(id: string): Entity | undefined {
    return entities.value.find(e => e.id === id)
  }

  // Get entities by type
  function getEntitiesByType(type: string): Entity[] {
    return entities.value.filter(e => e.type === type)
  }

  // Get entity types present in document
  const entityTypes = computed(() => {
    const types = new Set(entities.value.map(e => e.type))
    return Array.from(types)
  })

  // Count entities by type
  function getEntityCountByType(type: string): number {
    return entities.value.filter(e => e.type === type).length
  }

  return {
    // State
    entities,
    annotations,
    selectedEntity,
    selectedAnnotation,
    hoveredBoundingBox,
    searchHighlights,
    currentPage,
    totalPages,
    zoomLevel,

    // Computed
    currentPageBoundingBoxes,
    entityTypes,

    // Methods
    entityTypeColors,
    getBoundingBoxColor,
    addEntity,
    addAnnotation,
    deleteAnnotation,
    selectEntity,
    selectAnnotation,
    searchText,
    clearSearchHighlights,
    navigateToBoundingBox,
    getEntityById,
    getEntitiesByType,
    getEntityCountByType
  }
}
