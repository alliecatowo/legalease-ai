/**
 * Hierarchical Document Chunking
 *
 * Creates chunks at multiple granularities for optimal retrieval:
 * - summary: First ~2000 chars for high-level context
 * - section: Content between headings (~1000 tokens)
 * - paragraph: Fine-grained chunks (~400 tokens with overlap)
 *
 * Each chunk preserves bounding boxes for UI highlighting.
 */

import type {
  PageContent,
  PageElement,
  ExtractedChunk,
  ChunkType,
  NormalizedBbox,
  ElementType,
  ChunkingConfig
} from './types.js'

/** Default chunking configuration */
const DEFAULT_CONFIG: ChunkingConfig = {
  maxTokensPerChunk: 400,
  overlapTokens: 50,
  respectHeadings: true,
  preserveTables: true
}

/** Approximate characters per token */
const CHARS_PER_TOKEN = 4

/** Generate a unique chunk ID */
function generateChunkId(): string {
  return `chunk-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

/** Estimate token count from text */
function estimateTokens(text: string): number {
  return Math.ceil(text.length / CHARS_PER_TOKEN)
}

/** Flatten all elements from pages into a single array */
function flattenElements(pages: PageContent[]): PageElement[] {
  const elements: PageElement[] = []
  for (const page of pages) {
    for (const element of page.elements) {
      elements.push(element)
    }
  }
  return elements
}

/** Get the full text from a list of elements */
function getElementsText(elements: PageElement[]): string {
  return elements.map(el => el.content).join('\n\n')
}

/** Get all bboxes from a list of elements */
function getElementsBboxes(elements: PageElement[]): NormalizedBbox[] {
  return elements.map(el => el.bbox)
}

/** Get page numbers from a list of elements */
function getPageNumbers(elements: PageElement[]): number[] {
  const pages = new Set<number>()
  for (const el of elements) {
    pages.add(el.bbox.pageNumber)
  }
  return Array.from(pages).sort((a, b) => a - b)
}

/** Get element types from a list of elements */
function getElementTypes(elements: PageElement[]): ElementType[] {
  const types = new Set<ElementType>()
  for (const el of elements) {
    types.add(el.type)
  }
  return Array.from(types)
}

/** Check if an element is a heading */
function isHeading(element: PageElement): boolean {
  return element.type === 'heading'
}

/** Get heading text from elements up to current position */
function getHeadingHierarchy(elements: PageElement[], upToIndex: number): string[] {
  const headings: string[] = []
  const headingsByLevel = new Map<number, string>()

  for (let i = 0; i <= upToIndex && i < elements.length; i++) {
    const el = elements[i]
    if (isHeading(el)) {
      const level = el.level || 1
      headingsByLevel.set(level, el.content)
      // Clear lower-level headings when a higher-level heading appears
      for (const [existingLevel] of headingsByLevel) {
        if (existingLevel > level) {
          headingsByLevel.delete(existingLevel)
        }
      }
    }
  }

  // Return headings sorted by level
  const sortedLevels = Array.from(headingsByLevel.keys()).sort((a, b) => a - b)
  for (const level of sortedLevels) {
    headings.push(headingsByLevel.get(level)!)
  }

  return headings
}

/**
 * Create a summary chunk from the beginning of the document
 */
function createSummaryChunk(elements: PageElement[], maxChars: number = 2000): ExtractedChunk | null {
  if (elements.length === 0) return null

  const summaryElements: PageElement[] = []
  let charCount = 0

  for (const el of elements) {
    if (charCount >= maxChars) break
    summaryElements.push(el)
    charCount += el.content.length
  }

  if (summaryElements.length === 0) return null

  const text = getElementsText(summaryElements)

  return {
    id: generateChunkId(),
    text: text.substring(0, maxChars),
    type: 'summary',
    bboxes: getElementsBboxes(summaryElements),
    headings: [],
    metadata: {
      pageNumbers: getPageNumbers(summaryElements),
      elementTypes: getElementTypes(summaryElements),
      charStart: 0,
      charEnd: Math.min(charCount, maxChars)
    }
  }
}

/**
 * Create section chunks based on headings
 */
function createSectionChunks(
  elements: PageElement[],
  maxTokens: number = 1000
): ExtractedChunk[] {
  const chunks: ExtractedChunk[] = []
  let currentSection: PageElement[] = []
  let sectionHeadings: string[] = []
  let charOffset = 0

  const flushSection = () => {
    if (currentSection.length === 0) return

    const text = getElementsText(currentSection)
    const tokenCount = estimateTokens(text)

    // If section is too large, split it further
    if (tokenCount > maxTokens) {
      // Split into smaller chunks while keeping within section
      const subChunks = createParagraphChunks(currentSection, maxTokens, CHARS_PER_TOKEN * 50)
      for (const subChunk of subChunks) {
        subChunk.type = 'section'
        subChunk.headings = [...sectionHeadings]
        chunks.push(subChunk)
      }
    } else {
      chunks.push({
        id: generateChunkId(),
        text,
        type: 'section',
        bboxes: getElementsBboxes(currentSection),
        headings: [...sectionHeadings],
        metadata: {
          pageNumbers: getPageNumbers(currentSection),
          elementTypes: getElementTypes(currentSection),
          charStart: charOffset,
          charEnd: charOffset + text.length
        }
      })
    }

    charOffset += text.length + 2 // +2 for \n\n separator
    currentSection = []
  }

  for (let i = 0; i < elements.length; i++) {
    const el = elements[i]

    if (isHeading(el)) {
      // Flush current section before starting a new one
      flushSection()
      sectionHeadings = getHeadingHierarchy(elements, i)
      currentSection.push(el)
    } else {
      currentSection.push(el)
    }
  }

  // Flush the last section
  flushSection()

  return chunks
}

/**
 * Create paragraph-level chunks with overlap
 */
function createParagraphChunks(
  elements: PageElement[],
  maxTokens: number = 400,
  overlapChars: number = 200
): ExtractedChunk[] {
  const chunks: ExtractedChunk[] = []
  let currentElements: PageElement[] = []
  let currentTokens = 0
  let charOffset = 0

  const flushChunk = (startIndex: number): number => {
    if (currentElements.length === 0) return startIndex

    const text = getElementsText(currentElements)

    chunks.push({
      id: generateChunkId(),
      text,
      type: 'paragraph',
      bboxes: getElementsBboxes(currentElements),
      headings: getHeadingHierarchy(elements, startIndex),
      metadata: {
        pageNumbers: getPageNumbers(currentElements),
        elementTypes: getElementTypes(currentElements),
        charStart: charOffset,
        charEnd: charOffset + text.length
      }
    })

    charOffset += text.length - overlapChars // Account for overlap

    // Calculate how many elements to keep for overlap
    let overlapElements: PageElement[] = []
    let overlapTokens = 0
    for (let i = currentElements.length - 1; i >= 0; i--) {
      const el = currentElements[i]
      const elTokens = estimateTokens(el.content)
      if (overlapTokens + elTokens > estimateTokens(' '.repeat(overlapChars))) {
        break
      }
      overlapElements.unshift(el)
      overlapTokens += elTokens
    }

    currentElements = overlapElements
    currentTokens = overlapTokens

    return startIndex
  }

  for (let i = 0; i < elements.length; i++) {
    const el = elements[i]
    const elTokens = estimateTokens(el.content)

    // Tables should stay intact if possible
    if (el.type === 'table' && elTokens > maxTokens) {
      // Flush current chunk
      flushChunk(i)
      currentElements = []
      currentTokens = 0

      // Create a dedicated chunk for the large table
      chunks.push({
        id: generateChunkId(),
        text: el.content,
        type: 'paragraph',
        bboxes: [el.bbox],
        headings: getHeadingHierarchy(elements, i),
        metadata: {
          pageNumbers: [el.bbox.pageNumber],
          elementTypes: ['table'],
          charStart: charOffset,
          charEnd: charOffset + el.content.length
        }
      })
      charOffset += el.content.length
      continue
    }

    // Would this element exceed the token limit?
    if (currentTokens + elTokens > maxTokens && currentElements.length > 0) {
      flushChunk(i - 1)
    }

    currentElements.push(el)
    currentTokens += elTokens
  }

  // Flush remaining elements
  if (currentElements.length > 0) {
    flushChunk(elements.length - 1)
  }

  return chunks
}

/**
 * Main chunking function - creates hierarchical chunks from document pages
 */
export function chunkDocument(
  pages: PageContent[],
  config: Partial<ChunkingConfig> = {}
): ExtractedChunk[] {
  const cfg = { ...DEFAULT_CONFIG, ...config }
  const elements = flattenElements(pages)

  if (elements.length === 0) {
    return []
  }

  const allChunks: ExtractedChunk[] = []

  // 1. Create summary chunk (first ~2000 chars)
  const summaryChunk = createSummaryChunk(elements)
  if (summaryChunk) {
    allChunks.push(summaryChunk)
  }

  // 2. Create section chunks based on headings
  if (cfg.respectHeadings) {
    const sectionChunks = createSectionChunks(elements, cfg.maxTokensPerChunk * 2.5)
    allChunks.push(...sectionChunks)
  }

  // 3. Create paragraph chunks with overlap
  const paragraphChunks = createParagraphChunks(
    elements,
    cfg.maxTokensPerChunk,
    cfg.overlapTokens * CHARS_PER_TOKEN
  )
  allChunks.push(...paragraphChunks)

  return allChunks
}

/**
 * Re-export the config type for external use
 */
export type { ChunkingConfig }
