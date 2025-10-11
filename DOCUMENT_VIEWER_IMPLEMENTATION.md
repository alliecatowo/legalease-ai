# RAGFlow-Style Document Viewer Implementation

This document describes the implementation of a visual document viewer with PDF viewing and bounding box highlights, similar to RAGFlow.

## Overview

The implementation provides a rich document viewing experience with:
- PDF rendering with zoom and pan controls
- SVG overlay for bounding box highlights
- Search-within-document with visual highlighting
- Integration with backend bbox data
- Responsive layout using Nuxt UI components

## Components Created

### 1. Backend API Endpoint
**File**: `/home/Allie/develop/legalease/backend/app/api/v1/documents.py`

Added new endpoint:
```python
@router.get("/documents/{document_id}/content")
def get_document_content(document_id: int, db: Session)
```

Returns:
```json
{
  "text": "Full document text...",
  "pages": [
    {
      "page_number": 1,
      "text": "Page text...",
      "items": [
        {
          "text": "Item text",
          "type": "paragraph",
          "bbox": {
            "l": 100,
            "t": 200,
            "r": 500,
            "b": 250
          },
          "chunk_id": 123
        }
      ]
    }
  ],
  "metadata": {...},
  "filename": "document.pdf",
  "document_id": 1,
  "total_chunks": 50,
  "total_pages": 10
}
```

### 2. Backend Service Method
**File**: `/home/Allie/develop/legalease/backend/app/services/document_service.py`

Added `get_document_content()` method that:
- Retrieves all chunks for a document
- Groups chunks by page
- Extracts bbox data from chunk metadata
- Returns structured content with page-level organization

### 3. DocumentViewer Component
**File**: `/home/Allie/develop/legalease/frontend/app/components/DocumentViewer.vue`

Features:
- **PDF Rendering**: Uses `vue-pdf-embed` library
- **Zoom Controls**: 50% to 300% zoom with controls
- **Page Navigation**: Next/previous buttons and direct page input
- **Bounding Box Overlay**: SVG layer with highlighted regions
- **Search Integration**: Highlights matching text with bbox visualization
- **Responsive Toolbar**: Sticky toolbar with zoom, navigation, and status

Props:
```typescript
interface Props {
  documentId: number | string
  searchQuery?: string
  highlightBboxes?: BBox[]
  initialPage?: number
}
```

Usage:
```vue
<DocumentViewer
  :document-id="123"
  :search-query="searchQuery"
  :initial-page="1"
/>
```

### 4. SearchResultCard Component
**File**: `/home/Allie/develop/legalease/frontend/app/components/SearchResultCard.vue`

Features:
- **Rich Result Display**: Document type, relevance score, metadata
- **Entity Badges**: Visual display of extracted entities
- **Highlighted Excerpts**: Search term highlighting in snippets
- **Click Navigation**: Navigate to document with page/chunk context
- **Vector Type Indicator**: Shows if result is keyword or semantic match

Props:
```typescript
interface SearchResult {
  id: number
  title: string
  excerpt: string
  documentType: string
  date: string
  relevanceScore: number
  entities?: Entity[]
  metadata?: any
  highlights?: string[]
  pageNumber?: number
  filename?: string
}
```

### 5. Document Viewer Composable
**File**: `/home/Allie/develop/legalease/frontend/app/composables/useDocumentViewer.ts`

Utility functions for working with documents:

```typescript
const {
  normalizeBBox,           // Convert bbox formats
  bboxesOverlap,          // Check bbox overlap
  calculateOverlap,       // Calculate overlap percentage
  filterItemsByQuery,     // Filter items by search query
  getItemsWithBboxes,     // Get items matching bboxes
  highlightText,          // Add HTML highlight marks
  findBestSnippet,        // Extract relevant text snippet
  getHighlightColor,      // Get color for highlight type
  scaleBBox,              // Scale bbox for zoom
  groupItemsByPage        // Group items by page
} = useDocumentViewer()
```

### 6. Updated Pages

#### Document Detail Page
**File**: `/home/Allie/develop/legalease/frontend/app/pages/documents/[id].vue`

Changes:
- Integrated `<DocumentViewer>` component for PDF files
- Search input controls document viewer highlighting
- Supports page number from URL query params
- Removed old text-based search implementation

Usage flow:
1. User searches within document
2. DocumentViewer highlights matching bboxes in yellow
3. User can zoom and pan to explore highlights
4. Page navigation preserved across search

#### Search Page
**File**: `/home/Allie/develop/legalease/frontend/app/pages/search.vue`

Changes:
- Uses `<SearchResultCard>` component for all results
- Cards show document type, relevance, entities
- Clicking result navigates to document with page context
- Supports chunk-level navigation

### 7. Package Installation

Added dependency:
```json
{
  "dependencies": {
    "vue-pdf-embed": "^2.1.3"
  }
}
```

## BBox Data Flow

1. **Document Upload**: PDF is parsed with Docling or PyMuPDF
2. **Chunk Creation**: Each chunk stores bbox in metadata:
   ```json
   {
     "bbox": {
       "l": 100,    // left
       "t": 200,    // top
       "r": 500,    // right
       "b": 250     // bottom
     }
   }
   ```
3. **Content Endpoint**: Retrieves chunks and returns with bboxes
4. **DocumentViewer**: Renders PDF with SVG overlay showing bboxes
5. **Highlighting**: Yellow highlights for search matches

## Bbox Coordinate Systems

The implementation handles two bbox formats:

### Docling Format (l, t, r, b)
```json
{
  "l": 100,  // left x coordinate
  "t": 200,  // top y coordinate
  "r": 500,  // right x coordinate
  "b": 250   // bottom y coordinate
}
```

### PyMuPDF Format (x0, y0, x1, y1)
```json
{
  "x0": 100,  // left x coordinate
  "y0": 200,  // top y coordinate
  "x1": 500,  // right x coordinate
  "y1": 250   // bottom y coordinate
}
```

The `normalizeBBox()` function converts both to a standard format.

## Styling

### Highlight Colors

- **Search Matches**: Yellow (`rgba(255, 235, 59, 0.3)`)
- **Keyword Matches**: Yellow/Amber (warning color)
- **Semantic Matches**: Blue (primary color)
- **Hybrid Matches**: Purple gradient

### Component Classes

```css
.highlight-box {
  fill: rgba(255, 235, 59, 0.3);
  stroke: rgba(255, 235, 59, 0.8);
  stroke-width: 2;
  transition: all 0.2s ease;
}

.highlight-box:hover {
  fill: rgba(255, 235, 59, 0.5);
  stroke-width: 3;
}
```

## Usage Examples

### Basic Document Viewing
```vue
<DocumentViewer :document-id="documentId" />
```

### With Search Highlighting
```vue
<script setup>
const searchQuery = ref('indemnification')
</script>

<template>
  <DocumentViewer
    :document-id="123"
    :search-query="searchQuery"
  />
</template>
```

### Navigate to Specific Page
```vue
<DocumentViewer
  :document-id="123"
  :initial-page="5"
/>
```

### Search Results Integration
```vue
<SearchResultCard
  v-for="result in results"
  :key="result.id"
  :result="result"
  @click="navigateToDocument(result)"
/>
```

## Features Supported

### Document Viewer
- [x] PDF rendering with vue-pdf-embed
- [x] Zoom controls (50% - 300%)
- [x] Page navigation
- [x] Bounding box overlay
- [x] Search highlighting
- [x] Responsive layout
- [x] Loading states
- [x] Error handling

### Search Integration
- [x] Click to navigate to document
- [x] Page number context
- [x] Chunk ID preservation
- [x] Highlighted excerpts
- [x] Entity display
- [x] Relevance scores

### Different Document Types
- [x] PDF: Full viewer with bboxes
- [x] DOCX/TXT: Text display fallback
- [x] Unsupported: Download prompt

## Browser Compatibility

The PDF viewer uses:
- PDF.js (via vue-pdf-embed)
- SVG overlays
- Modern CSS features

Supported browsers:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Performance Considerations

1. **Lazy Loading**: Content loaded on demand
2. **Page-based Rendering**: Only current page rendered
3. **Bbox Filtering**: Only highlights for current page
4. **Efficient Updates**: Reactive updates only when needed
5. **Memory Management**: PDF.js handles page cleanup

## Future Enhancements

Potential improvements:
- [ ] Thumbnail sidebar for quick navigation
- [ ] Text selection and annotation
- [ ] Multiple highlight colors for different entities
- [ ] Page thumbnails with highlight previews
- [ ] Print with highlights
- [ ] Export highlighted sections
- [ ] Collaborative annotations
- [ ] Mobile touch gestures for zoom/pan

## Troubleshooting

### PDF Not Loading
- Check document is indexed (`status: INDEXED`)
- Verify `/api/v1/documents/{id}/download` endpoint works
- Check browser console for CORS errors

### Bboxes Not Showing
- Verify chunks have bbox in metadata
- Check bbox format (l,t,r,b vs x0,y0,x1,y1)
- Ensure coordinates are in correct scale

### Search Not Highlighting
- Verify searchQuery prop is passed
- Check item text matches query
- Ensure items have bbox data

## Files Modified/Created

### Backend
- `/home/Allie/develop/legalease/backend/app/api/v1/documents.py` - Added content endpoint
- `/home/Allie/develop/legalease/backend/app/services/document_service.py` - Added get_document_content()

### Frontend
- `/home/Allie/develop/legalease/frontend/app/components/DocumentViewer.vue` - NEW
- `/home/Allie/develop/legalease/frontend/app/components/SearchResultCard.vue` - NEW
- `/home/Allie/develop/legalease/frontend/app/composables/useDocumentViewer.ts` - NEW
- `/home/Allie/develop/legalease/frontend/app/pages/documents/[id].vue` - Modified
- `/home/Allie/develop/legalease/frontend/app/pages/search.vue` - Modified
- `/home/Allie/develop/legalease/frontend/package.json` - Added vue-pdf-embed

## Summary

This implementation provides a comprehensive document viewing experience with visual bounding box highlights, similar to RAGFlow. The modular design allows for easy extension and customization, while maintaining good performance and user experience.
