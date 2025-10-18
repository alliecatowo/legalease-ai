/**
 * Composable for document viewer utilities
 * Provides helpers for working with document bboxes, page navigation, and highlights
 */

export interface BBox {
  l?: number
  t?: number
  r?: number
  b?: number
  x0?: number
  y0?: number
  x1?: number
  y1?: number
}

export interface NormalizedBBox {
  x: number
  y: number
  width: number
  height: number
}

export interface DocumentContentItem {
  text: string
  type: string
  bboxes?: Array<BBox | { bbox: BBox; text?: string; page?: number }>
  chunk_id?: string | number
}

export interface PageData {
  page_number: number
  text: string
  items: DocumentContentItem[]
  image_url?: string
}

export interface DocumentContent {
  text: string
  pages: PageData[]
  metadata: any
  filename: string
  document_id: number
  total_chunks: number
  total_pages: number
}

export const useDocumentViewer = () => {
  /**
   * Normalize bbox coordinates from different formats
   * Supports both {l,t,r,b} (Docling) and {x0,y0,x1,y1} (PyMuPDF) formats
   */
  const normalizeBBox = (bbox: BBox): NormalizedBBox => {
    if (bbox.l !== undefined) {
      return {
        x: bbox.l,
        y: bbox.t || 0,
        width: (bbox.r || 0) - bbox.l,
        height: (bbox.b || 0) - (bbox.t || 0)
      }
    } else if (bbox.x0 !== undefined) {
      return {
        x: bbox.x0,
        y: bbox.y0 || 0,
        width: (bbox.x1 || 0) - bbox.x0,
        height: (bbox.y1 || 0) - (bbox.y0 || 0)
      }
    }
    return { x: 0, y: 0, width: 0, height: 0 }
  }

  /**
   * Check if two bboxes overlap
   */
  const bboxesOverlap = (bbox1: BBox, bbox2: BBox): boolean => {
    const b1 = normalizeBBox(bbox1)
    const b2 = normalizeBBox(bbox2)

    return !(
      b1.x + b1.width < b2.x ||
      b2.x + b2.width < b1.x ||
      b1.y + b1.height < b2.y ||
      b2.y + b2.height < b1.y
    )
  }

  /**
   * Calculate overlap percentage between two bboxes
   */
  const calculateOverlap = (bbox1: BBox, bbox2: BBox): number => {
    const b1 = normalizeBBox(bbox1)
    const b2 = normalizeBBox(bbox2)

    const xOverlap = Math.max(0, Math.min(b1.x + b1.width, b2.x + b2.width) - Math.max(b1.x, b2.x))
    const yOverlap = Math.max(0, Math.min(b1.y + b1.height, b2.y + b2.height) - Math.max(b1.y, b2.y))

    const overlapArea = xOverlap * yOverlap
    const area1 = b1.width * b1.height
    const area2 = b2.width * b2.height

    if (area1 === 0 || area2 === 0) return 0

    return overlapArea / Math.min(area1, area2)
  }

  /**
   * Filter items by search query
   */
  const filterItemsByQuery = (
    items: DocumentContentItem[],
    query: string,
    requireBbox = true
  ): DocumentContentItem[] => {
    if (!query) return []

    const lowerQuery = query.toLowerCase()

    return items.filter(item => {
      const hasMatch = item.text && item.text.toLowerCase().includes(lowerQuery)
      const hasBbox = !requireBbox || (item.bboxes && item.bboxes.length > 0)
      return hasMatch && hasBbox
    })
  }

  /**
   * Get page items that match specific bboxes
   */
  const getItemsWithBboxes = (
    items: DocumentContentItem[],
    targetBboxes: BBox[],
    overlapThreshold = 0.5
  ): DocumentContentItem[] => {
    if (!targetBboxes || targetBboxes.length === 0) return []

    return items.filter(item => {
      const boxes: BBox[] = []
      if (item.bboxes && item.bboxes.length) {
        for (const entry of item.bboxes) {
          boxes.push((entry as any).bbox ? (entry as any).bbox as BBox : (entry as BBox))
        }
      }
      if (boxes.length === 0) return false

      return boxes.some(b => targetBboxes.some(targetBbox =>
        calculateOverlap(b, targetBbox) >= overlapThreshold
      ))
    })
  }

  /**
   * Highlight text with HTML marks
   */
  const highlightText = (
    text: string,
    query: string,
    highlightClass = 'bg-warning/30 text-warning-600 dark:text-warning-400 font-medium px-0.5 rounded'
  ): string => {
    if (!query) return text

    const terms = query.toLowerCase().split(/\s+/).filter(t => t.length > 2)
    let highlighted = text

    terms.forEach(term => {
      const escapedTerm = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      const regex = new RegExp(`(${escapedTerm})`, 'gi')
      highlighted = highlighted.replace(regex, `<mark class="${highlightClass}">$1</mark>`)
    })

    return highlighted
  }

  /**
   * Find best snippet containing search terms
   */
  const findBestSnippet = (
    text: string,
    query: string,
    maxLength = 400
  ): string => {
    if (!text) return ''

    const terms = query.toLowerCase().split(/\s+/).filter(t => t.length > 2)
    if (terms.length === 0) {
      return text.substring(0, maxLength).trim() + (text.length > maxLength ? '...' : '')
    }

    // Find first occurrence of any term
    const lowerText = text.toLowerCase()
    let bestIndex = -1

    for (const term of terms) {
      const index = lowerText.indexOf(term)
      if (index !== -1 && (bestIndex === -1 || index < bestIndex)) {
        bestIndex = index
      }
    }

    if (bestIndex === -1) {
      return text.substring(0, maxLength).trim() + (text.length > maxLength ? '...' : '')
    }

    // Extract snippet around the term
    const snippetStart = Math.max(0, bestIndex - 100)
    const snippetEnd = Math.min(text.length, bestIndex + maxLength - 100)
    let snippet = text.substring(snippetStart, snippetEnd).trim()

    // Add ellipsis
    if (snippetStart > 0) snippet = '...' + snippet
    if (snippetEnd < text.length) snippet = snippet + '...'

    return snippet
  }

  /**
   * Get color for highlight based on score or type
   */
  const getHighlightColor = (
    type: 'keyword' | 'semantic' | 'hybrid' = 'hybrid',
    opacity = 0.3
  ): string => {
    const colors = {
      keyword: `rgba(255, 235, 59, ${opacity})`, // Yellow
      semantic: `rgba(33, 150, 243, ${opacity})`, // Blue
      hybrid: `rgba(156, 39, 176, ${opacity})` // Purple
    }
    return colors[type]
  }

  /**
   * Scale bbox coordinates based on zoom level
   */
  const scaleBBox = (bbox: BBox, scale: number): BBox => {
    const normalized = normalizeBBox(bbox)

    if (bbox.l !== undefined) {
      return {
        l: normalized.x * scale,
        t: normalized.y * scale,
        r: (normalized.x + normalized.width) * scale,
        b: (normalized.y + normalized.height) * scale
      }
    } else {
      return {
        x0: normalized.x * scale,
        y0: normalized.y * scale,
        x1: (normalized.x + normalized.width) * scale,
        y1: (normalized.y + normalized.height) * scale
      }
    }
  }

  /**
   * Group items by page
   */
  const groupItemsByPage = (items: DocumentContentItem[]): Map<number, DocumentContentItem[]> => {
    const grouped = new Map<number, DocumentContentItem[]>()

    items.forEach(item => {
      const pageNum = (item as any).page_number || 1
      if (!grouped.has(pageNum)) {
        grouped.set(pageNum, [])
      }
      grouped.get(pageNum)!.push(item)
    })

    return grouped
  }

  return {
    normalizeBBox,
    bboxesOverlap,
    calculateOverlap,
    filterItemsByQuery,
    getItemsWithBboxes,
    highlightText,
    findBestSnippet,
    getHighlightColor,
    scaleBBox,
    groupItemsByPage
  }
}
