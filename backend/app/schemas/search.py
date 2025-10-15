"""
Pydantic schemas for search operations.

This module defines request and response models for hybrid search
operations on legal documents using Qdrant vector database.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# Bounding Box and Page Schemas

class BoundingBox(BaseModel):
    """
    Bounding box coordinates for text highlighting.

    Attributes:
        x0: Left coordinate (or 'l' for Docling format)
        y0: Top coordinate (or 't' for Docling format)
        x1: Right coordinate (or 'r' for Docling format)
        y1: Bottom coordinate (or 'b' for Docling format)
        page: Page number this bbox belongs to
        text: Text content within this bbox
        type: Type of element (e.g., 'word', 'TextItem', 'TableItem')
    """

    x0: Optional[float] = Field(None, description="Left X coordinate")
    y0: Optional[float] = Field(None, description="Top Y coordinate")
    x1: Optional[float] = Field(None, description="Right X coordinate")
    y1: Optional[float] = Field(None, description="Bottom Y coordinate")
    l: Optional[float] = Field(None, description="Left coordinate (Docling format)")
    t: Optional[float] = Field(None, description="Top coordinate (Docling format)")
    r: Optional[float] = Field(None, description="Right coordinate (Docling format)")
    b: Optional[float] = Field(None, description="Bottom coordinate (Docling format)")
    page: Optional[int] = Field(None, description="Page number")
    text: Optional[str] = Field(None, description="Text content")
    type: Optional[str] = Field(None, description="Element type")

    class Config:
        json_schema_extra = {
            "example": {
                "x0": 72.0,
                "y0": 100.0,
                "x1": 200.0,
                "y1": 120.0,
                "page": 1,
                "text": "contract",
                "type": "word",
            }
        }


class PageItem(BaseModel):
    """
    Structured item on a document page.

    Attributes:
        text: Text content of the item
        type: Type of element (e.g., 'TextItem', 'TableItem')
        bboxes: Optional list of bounding boxes
        chunk_id: Optional associated chunk ID
    """

    text: str = Field(..., description="Item text content")
    type: Optional[str] = Field(None, description="Item type")
    bboxes: List[Dict[str, Any]] = Field(default_factory=list, description="Bounding boxes for this item")
    chunk_id: Optional[int] = Field(None, description="Associated chunk ID")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "This is the contract text...",
                "type": "TextItem",
                "bboxes": [{"l": 72.0, "t": 100.0, "r": 500.0, "b": 120.0}],
                "chunk_id": 42,
            }
        }


class DocumentPage(BaseModel):
    """
    Single page of a document with items and metadata.

    Attributes:
        page_number: Page number (1-indexed)
        text: Full text content of the page
        items: List of structured items on this page
        image_url: Optional presigned URL for page image
    """

    page_number: int = Field(..., description="Page number (1-indexed)")
    text: str = Field(..., description="Full page text")
    items: List[PageItem] = Field(default_factory=list, description="Structured page items")
    image_url: Optional[str] = Field(None, description="Presigned URL for page image")

    class Config:
        json_schema_extra = {
            "example": {
                "page_number": 1,
                "text": "Contract Agreement...",
                "items": [
                    {
                        "text": "Contract Agreement",
                        "type": "TextItem",
                        "bbox": {"l": 72.0, "t": 100.0, "r": 500.0, "b": 120.0},
                    }
                ],
                "image_url": "https://minio.example.com/...",
            }
        }


class DocumentContentResponse(BaseModel):
    """
    Complete document content with pages, items, and bounding boxes.

    Attributes:
        document_id: Database document ID
        filename: Original filename
        text: Full document text
        pages: List of pages with items and bboxes
        metadata: Document metadata
        total_chunks: Total number of indexed chunks
        total_pages: Total number of pages
    """

    document_id: int = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    text: str = Field(..., description="Full document text")
    pages: List[DocumentPage] = Field(..., description="Document pages with items")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    total_chunks: int = Field(..., description="Total indexed chunks")
    total_pages: int = Field(..., description="Total pages")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": 5,
                "filename": "contract.pdf",
                "text": "Full document text...",
                "pages": [
                    {
                        "page_number": 1,
                        "text": "Page 1 text...",
                        "items": [],
                    }
                ],
                "metadata": {"author": "John Doe", "page_count": 10},
                "total_chunks": 45,
                "total_pages": 10,
            }
        }


class PageImageResponse(BaseModel):
    """
    Response containing page image URL.

    Attributes:
        page_number: Page number (1-indexed)
        image_url: Presigned URL for the page image
        document_id: Document ID
        expires_in: Seconds until URL expires
    """

    page_number: int = Field(..., description="Page number")
    image_url: str = Field(..., description="Presigned image URL")
    document_id: int = Field(..., description="Document ID")
    expires_in: int = Field(3600, description="URL expiration in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "page_number": 1,
                "image_url": "https://minio.example.com/documents/1/5/pages/page_1.png?...",
                "document_id": 5,
                "expires_in": 3600,
            }
        }


class PageListResponse(BaseModel):
    """
    List of page images for a document.

    Attributes:
        document_id: Document ID
        total_pages: Total number of pages
        pages: List of pages with image URLs
    """

    document_id: int = Field(..., description="Document ID")
    total_pages: int = Field(..., description="Total pages")
    pages: List[Dict[str, Any]] = Field(..., description="Page data with image URLs")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": 5,
                "total_pages": 10,
                "pages": [
                    {"page_number": 1, "image_url": "https://..."},
                    {"page_number": 2, "image_url": "https://..."},
                ],
            }
        }


class SearchQuery(BaseModel):
    """
    Base search query parameters.

    Attributes:
        query: The search query text
        case_ids: Optional list of case IDs to filter results
        document_ids: Optional list of document IDs to filter results
        chunk_types: Optional list of chunk types to filter (e.g., 'summary', 'section', 'microblock')
        top_k: Maximum number of results to return
        score_threshold: Minimum relevance score threshold
        use_bm25: Whether to include BM25 keyword search
        use_dense: Whether to include dense vector search
    """

    query: str = Field(..., min_length=1, description="Search query text")
    case_ids: Optional[List[int]] = Field(None, description="Filter by case IDs")
    document_ids: Optional[List[int]] = Field(None, description="Filter by document IDs")
    chunk_types: Optional[List[str]] = Field(None, description="Filter by chunk types")
    top_k: int = Field(10, ge=1, le=100, description="Maximum number of results")
    score_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum score threshold")
    use_bm25: bool = Field(True, description="Include BM25 keyword search")
    use_dense: bool = Field(True, description="Include dense vector search")

    @field_validator("chunk_types")
    @classmethod
    def validate_chunk_types(cls, v):
        """Validate chunk types against allowed values."""
        if v is not None:
            allowed_types = {"summary", "section", "microblock", "paragraph", "page", "transcript_segment"}
            invalid_types = set(v) - allowed_types
            if invalid_types:
                raise ValueError(f"Invalid chunk types: {invalid_types}. Allowed: {allowed_types}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "contract breach liability damages",
                "case_ids": [1, 2],
                "top_k": 20,
                "score_threshold": 0.5,
                "use_bm25": True,
                "use_dense": True,
            }
        }


class SearchResult(BaseModel):
    """
    Individual search result item.

    Attributes:
        id: Unique identifier of the chunk/point (int or UUID string)
        score: Relevance score (0.0 to 1.0 or higher)
        text: The actual text content
        metadata: Additional metadata about the result
        highlights: Optional highlighted portions of the text
        vector_type: Type of vector used for this match (e.g., 'summary', 'bm25')
        match_type: Type of match - 'bm25' for keyword matches, 'semantic' for semantic matches
        page_number: Page number for this result
        bboxes: Bounding boxes for highlighting
    """

    id: Union[int, str] = Field(..., description="Chunk/point ID (int or UUID string)")
    score: float = Field(..., description="Relevance score")
    text: str = Field(..., description="Content text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    highlights: Optional[List[str]] = Field(None, description="Highlighted text snippets")
    vector_type: Optional[str] = Field(None, description="Vector type used for matching")
    match_type: Optional[str] = Field("semantic", description="Match type: 'bm25' for keyword, 'semantic' for semantic")
    page_number: Optional[int] = Field(None, description="Page number for this result")
    bboxes: List[Dict[str, Any]] = Field(default_factory=list, description="Bounding boxes for highlighting")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 42,
                "score": 0.87,
                "text": "The defendant breached the contract by failing to deliver...",
                "metadata": {
                    "document_id": 5,
                    "case_id": 1,
                    "chunk_type": "section",
                    "page_number": 3,
                },
                "highlights": ["breached the contract", "failing to deliver"],
                "vector_type": "section",
            }
        }


class HybridSearchRequest(BaseModel):
    """
    Request model for hybrid search combining multiple search strategies.

    Extends SearchQuery with hybrid-specific parameters.

    Attributes:
        query: The search query (inherited from SearchQuery)
        fusion_method: Method for combining results (default: 'rrf' for Reciprocal Rank Fusion)
        rrf_k: RRF k parameter for rank fusion
        vector_weights: Optional weights for different vector types
    """

    query: str = Field(..., min_length=1, description="Search query text")
    case_ids: Optional[List[int]] = Field(None, description="Filter by case IDs")
    document_ids: Optional[List[int]] = Field(None, description="Filter by document IDs")
    chunk_types: Optional[List[str]] = Field(None, description="Filter by chunk types")
    top_k: int = Field(10, ge=1, le=100, description="Maximum number of results")
    score_threshold: Optional[float] = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score threshold (0.0-1.0). Default 0.3. Set to 0.0 to show all results. Scores are normalized: 0.85-1.0 for strong keyword matches, 0.6-0.85 for semantic matches, 0.3-0.6 for weak matches."
    )
    use_bm25: bool = Field(True, description="Include BM25 keyword search")
    use_dense: bool = Field(True, description="Include dense vector search")
    fusion_method: str = Field("rrf", description="Fusion method: 'rrf' (Reciprocal Rank Fusion), 'dbsf' (Distribution-Based Score Fusion)")
    rrf_k: int = Field(60, ge=1, description="RRF k parameter (only used with rrf fusion)")
    vector_weights: Optional[Dict[str, float]] = Field(
        None,
        description="Weights for vector types (e.g., {'summary': 0.3, 'section': 0.4, 'microblock': 0.3})"
    )

    @field_validator("fusion_method")
    @classmethod
    def validate_fusion_method(cls, v):
        """Validate fusion method."""
        allowed_methods = {"rrf", "weighted", "max"}
        if v not in allowed_methods:
            raise ValueError(f"Invalid fusion method: {v}. Allowed: {allowed_methods}")
        return v

    @field_validator("chunk_types")
    @classmethod
    def validate_chunk_types(cls, v):
        """Validate chunk types against allowed values."""
        if v is not None:
            allowed_types = {"summary", "section", "microblock", "paragraph", "page", "transcript_segment"}
            invalid_types = set(v) - allowed_types
            if invalid_types:
                raise ValueError(f"Invalid chunk types: {invalid_types}. Allowed: {allowed_types}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "employment discrimination wrongful termination",
                "case_ids": [3, 5, 7],
                "top_k": 15,
                "fusion_method": "rrf",
                "rrf_k": 60,
                "use_bm25": True,
                "use_dense": True,
            }
        }


class HybridSearchResponse(BaseModel):
    """
    Response model for hybrid search results.

    Attributes:
        results: List of search results ordered by relevance
        total_results: Total number of results found
        query: The original query text
        search_metadata: Metadata about the search execution
    """

    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., ge=0, description="Total number of results")
    query: str = Field(..., description="Original query text")
    search_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Search execution metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "id": 42,
                        "score": 0.87,
                        "text": "The defendant breached the contract...",
                        "metadata": {
                            "document_id": 5,
                            "case_id": 1,
                            "chunk_type": "section",
                        },
                        "vector_type": "section",
                    }
                ],
                "total_results": 1,
                "query": "contract breach",
                "search_metadata": {
                    "search_time_ms": 45,
                    "vectors_used": ["summary", "section", "bm25"],
                    "fusion_method": "rrf",
                },
            }
        }


class DocumentChunk(BaseModel):
    """
    Model for document chunk to be indexed.

    Used when uploading documents to the vector database.

    Attributes:
        chunk_id: Unique chunk identifier
        document_id: Parent document ID
        case_id: Associated case ID
        text: Chunk text content
        chunk_type: Type of chunk (summary, section, microblock)
        position: Position/order in document
        page_number: Optional page number
        metadata: Additional metadata
    """

    chunk_id: int = Field(..., description="Unique chunk ID")
    document_id: int = Field(..., description="Parent document ID")
    case_id: int = Field(..., description="Associated case ID")
    text: str = Field(..., min_length=1, description="Chunk text content")
    chunk_type: str = Field(..., description="Chunk type")
    position: int = Field(..., ge=0, description="Position in document")
    page_number: Optional[int] = Field(None, description="Page number if applicable")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("chunk_type")
    @classmethod
    def validate_chunk_type(cls, v):
        """Validate chunk type."""
        allowed_types = {"summary", "section", "microblock", "paragraph", "page", "transcript_segment"}
        if v not in allowed_types:
            raise ValueError(f"Invalid chunk type: {v}. Allowed: {allowed_types}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": 123,
                "document_id": 5,
                "case_id": 1,
                "text": "This section discusses the breach of contract...",
                "chunk_type": "section",
                "position": 2,
                "page_number": 3,
                "metadata": {
                    "section_title": "Breach of Contract",
                    "confidence": 0.95,
                },
            }
        }


class IndexRequest(BaseModel):
    """
    Request to index document chunks.

    Attributes:
        chunks: List of document chunks to index
        collection_name: Optional custom collection name
    """

    chunks: List[DocumentChunk] = Field(..., min_length=1, description="Chunks to index")
    collection_name: Optional[str] = Field(None, description="Custom collection name")

    class Config:
        json_schema_extra = {
            "example": {
                "chunks": [
                    {
                        "chunk_id": 123,
                        "document_id": 5,
                        "case_id": 1,
                        "text": "Contract section...",
                        "chunk_type": "section",
                        "position": 1,
                    }
                ]
            }
        }


class IndexResponse(BaseModel):
    """
    Response after indexing chunks.

    Attributes:
        indexed_count: Number of chunks successfully indexed
        failed_count: Number of chunks that failed to index
        collection_name: Name of the collection
        timestamp: When the indexing occurred
    """

    indexed_count: int = Field(..., ge=0, description="Successfully indexed chunks")
    failed_count: int = Field(0, ge=0, description="Failed chunks")
    collection_name: str = Field(..., description="Collection name")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Indexing timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "indexed_count": 150,
                "failed_count": 0,
                "collection_name": "legalease_documents",
                "timestamp": "2025-10-09T12:30:00Z",
            }
        }
