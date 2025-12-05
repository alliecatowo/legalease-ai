/**
 * Bounding Box Utilities
 *
 * Converts between different coordinate systems:
 * - Docling: {l, t, r, b} with BOTTOMLEFT or TOPLEFT origin
 * - PyMuPDF: {x0, y0, x1, y1} with top-left origin
 * - Normalized: {x, y, width, height} in 0-1 range with top-left origin
 *
 * Frontend PDFViewerWithHighlights expects normalized coordinates.
 */

import type { NormalizedBbox, PageElement } from './types.js'

/** Docling bounding box format */
export interface DoclingBbox {
  l: number // left
  t: number // top (meaning depends on coord_origin)
  r: number // right
  b: number // bottom (meaning depends on coord_origin)
  coord_origin: 'BOTTOMLEFT' | 'TOPLEFT'
}

/** PyMuPDF bounding box format */
export interface PyMuPdfBbox {
  x0: number // left
  y0: number // top
  x1: number // right
  y1: number // bottom
}

/** Clamp a value between min and max */
function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

/**
 * Convert Docling bbox to normalized format
 *
 * Docling can output two coordinate systems:
 * - BOTTOMLEFT: t > b (t is higher from bottom), standard PDF coordinates
 * - TOPLEFT: t < b (t is from top), already in screen coordinates
 */
export function fromDoclingBbox(
  bbox: DoclingBbox,
  pageWidth: number,
  pageHeight: number,
  pageNumber: number
): NormalizedBbox {
  if (pageWidth <= 0 || pageHeight <= 0) {
    throw new Error(`Invalid page dimensions: ${pageWidth}x${pageHeight}`)
  }

  const isBottomLeft = bbox.coord_origin === 'BOTTOMLEFT'

  // Normalize x coordinates (same for both origins)
  const x = bbox.l / pageWidth
  const width = (bbox.r - bbox.l) / pageWidth

  let y: number
  let height: number

  if (isBottomLeft) {
    // Bottom-left origin: t > b (t is higher on page from bottom)
    // Convert to top-left: y = 1 - (t / pageHeight)
    y = 1 - (bbox.t / pageHeight)
    height = (bbox.t - bbox.b) / pageHeight
  } else {
    // Top-left origin: t < b (already in screen coordinates)
    y = bbox.t / pageHeight
    height = (bbox.b - bbox.t) / pageHeight
  }

  return {
    x: clamp(x, 0, 1),
    y: clamp(y, 0, 1),
    width: clamp(width, 0, 1),
    height: clamp(Math.abs(height), 0, 1),
    pageNumber
  }
}

/**
 * Convert PyMuPDF bbox to normalized format
 *
 * PyMuPDF uses top-left origin with coordinates in points
 */
export function fromPyMuPdfBbox(
  bbox: PyMuPdfBbox,
  pageWidth: number,
  pageHeight: number,
  pageNumber: number
): NormalizedBbox {
  if (pageWidth <= 0 || pageHeight <= 0) {
    throw new Error(`Invalid page dimensions: ${pageWidth}x${pageHeight}`)
  }

  return {
    x: clamp(bbox.x0 / pageWidth, 0, 1),
    y: clamp(bbox.y0 / pageHeight, 0, 1),
    width: clamp((bbox.x1 - bbox.x0) / pageWidth, 0, 1),
    height: clamp((bbox.y1 - bbox.y0) / pageHeight, 0, 1),
    pageNumber
  }
}

/**
 * Merge multiple bboxes into a single bounding box that contains all of them
 */
export function mergeBboxes(bboxes: NormalizedBbox[]): NormalizedBbox | null {
  if (bboxes.length === 0) return null
  if (bboxes.length === 1) return { ...bboxes[0] }

  // Group by page
  const byPage = new Map<number, NormalizedBbox[]>()
  for (const bbox of bboxes) {
    const existing = byPage.get(bbox.pageNumber) || []
    existing.push(bbox)
    byPage.set(bbox.pageNumber, existing)
  }

  // For simplicity, merge within the first page that has bboxes
  const firstPage = Math.min(...Array.from(byPage.keys()))
  const pageBboxes = byPage.get(firstPage)!

  let minX = pageBboxes[0].x
  let minY = pageBboxes[0].y
  let maxX = pageBboxes[0].x + pageBboxes[0].width
  let maxY = pageBboxes[0].y + pageBboxes[0].height

  for (const bbox of pageBboxes) {
    minX = Math.min(minX, bbox.x)
    minY = Math.min(minY, bbox.y)
    maxX = Math.max(maxX, bbox.x + bbox.width)
    maxY = Math.max(maxY, bbox.y + bbox.height)
  }

  return {
    x: minX,
    y: minY,
    width: maxX - minX,
    height: maxY - minY,
    pageNumber: firstPage
  }
}

/**
 * Sort elements by reading order (top-to-bottom, left-to-right)
 */
export function sortByReadingOrder(elements: PageElement[]): PageElement[] {
  return [...elements].sort((a, b) => {
    // First by page
    if (a.bbox.pageNumber !== b.bbox.pageNumber) {
      return a.bbox.pageNumber - b.bbox.pageNumber
    }

    // Then by vertical position (with some tolerance for same-line elements)
    const tolerance = 0.02 // 2% of page height
    const yDiff = a.bbox.y - b.bbox.y
    if (Math.abs(yDiff) > tolerance) {
      return yDiff
    }

    // Finally by horizontal position for same-line elements
    return a.bbox.x - b.bbox.x
  })
}

/**
 * Check if two bboxes overlap
 */
export function bboxesOverlap(a: NormalizedBbox, b: NormalizedBbox): boolean {
  if (a.pageNumber !== b.pageNumber) return false

  return !(
    a.x + a.width < b.x ||
    b.x + b.width < a.x ||
    a.y + a.height < b.y ||
    b.y + b.height < a.y
  )
}

/**
 * Calculate the overlap area between two bboxes (0-1 range)
 */
export function calculateOverlap(a: NormalizedBbox, b: NormalizedBbox): number {
  if (a.pageNumber !== b.pageNumber) return 0

  const xOverlap = Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x))
  const yOverlap = Math.max(0, Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y))

  return xOverlap * yOverlap
}

/**
 * Expand a bbox by a margin (percentage of original dimensions)
 */
export function expandBbox(bbox: NormalizedBbox, margin: number = 0.01): NormalizedBbox {
  return {
    x: clamp(bbox.x - margin, 0, 1),
    y: clamp(bbox.y - margin, 0, 1),
    width: clamp(bbox.width + margin * 2, 0, 1 - bbox.x + margin),
    height: clamp(bbox.height + margin * 2, 0, 1 - bbox.y + margin),
    pageNumber: bbox.pageNumber
  }
}
