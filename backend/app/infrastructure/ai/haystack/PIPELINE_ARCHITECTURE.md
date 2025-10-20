# Haystack Hybrid Search Pipeline Architecture

## Pipeline Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          HYBRID SEARCH PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

Input: query="contract breach liability damages"
       filters={case_ids, document_ids, chunk_types, evidence_types}

┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: Query Preprocessing                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ LegalQueryPreprocessor                                                │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │ • Expand synonyms: attorney → [lawyer, counsel]                       │ │
│  │ • Preserve citations: "123 F.3d 456"                                  │ │
│  │ • Remove common stopwords (keep legal terms)                          │ │
│  │ • Normalize: lowercase, clean whitespace                              │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Output: "contract agreement breach violation liability damages"            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌─────────────────────────────────────┐ ┌─────────────────────────────────────┐
│ STAGE 2A: Dense Vector Search       │ │ STAGE 2B: Keyword Search            │
├─────────────────────────────────────┤ ├─────────────────────────────────────┤
│                                     │ │                                     │
│  ┌──────────────────────────────┐  │ │  ┌──────────────────────────────┐  │
│  │ QueryEmbedder                │  │ │  │ OpenSearchHybridRetriever    │  │
│  ├──────────────────────────────┤  │ │  ├──────────────────────────────┤  │
│  │ Model: BAAI/bge-small-en-v1.5│  │ │  │ • BM25 scoring               │  │
│  │ Output: 384-dim vector       │  │ │  │ • Legal term analysis        │  │
│  └──────────────────────────────┘  │ │  │ • Citation matching          │  │
│              │                      │ │  │ • Multi-index search         │  │
│              ▼                      │ │  │   - documents                │  │
│  ┌──────────────────────────────┐  │ │  │   - transcripts              │  │
│  │ QdrantHybridRetriever        │  │ │  │   - communications           │  │
│  ├──────────────────────────────┤  │ │  │                              │  │
│  │ • Hierarchical embeddings    │  │ │  │ Filters:                     │  │
│  │   - summary                  │  │ │  │ • case_ids                   │  │
│  │   - section                  │  │ │  │ • document_ids               │  │
│  │   - microblock               │  │ │  │ • chunk_types                │  │
│  │ • Multi-collection search    │  │ │  └──────────────────────────────┘  │
│  │   - documents                │  │ │              │                      │
│  │   - transcripts              │  │ │              ▼                      │
│  │   - communications           │  │ │  Top 20 results (BM25 scored)      │
│  │                              │  │ │  - "contract breach": 12.5         │
│  │ Filters:                     │  │ │  - "liability clause": 8.3         │
│  │ • case_ids                   │  │ │  - "damages provision": 7.1        │
│  │ • document_ids               │  │ │  ...                                │
│  │ • chunk_types                │  │ │                                     │
│  └──────────────────────────────┘  │ │                                     │
│              │                      │ │                                     │
│              ▼                      │ │                                     │
│  Top 20 results (cosine scored)    │ │                                     │
│  - "contractual obligations": 0.82 │ │                                     │
│  - "breach of duty": 0.79          │ │                                     │
│  - "legal liability": 0.76         │ │                                     │
│  ...                                │ │                                     │
└─────────────────────────────────────┘ └─────────────────────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: Reciprocal Rank Fusion                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ ReciprocalRankFusionRanker (k=60)                                     │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │                                                                        │ │
│  │ For each document:                                                    │ │
│  │   rrf_score = sum(1 / (k + rank_i)) for all result lists             │ │
│  │                                                                        │ │
│  │ Example (doc_123):                                                    │ │
│  │   - BM25 rank: 3    → 1/(60+3)  = 0.0159                             │ │
│  │   - Dense rank: 5   → 1/(60+5)  = 0.0154                             │ │
│  │   - Total RRF:      → 0.0159 + 0.0154 = 0.0313                       │ │
│  │                                                                        │ │
│  │ Score Normalization:                                                  │ │
│  │   1. Min-max to 0-1 range                                            │ │
│  │   2. Keyword boost (+0.3 for BM25 > 5.0)                             │ │
│  │   3. Non-linear scaling (power 0.7)                                  │ │
│  │   4. Priority boost for top keyword matches (→ 0.85+)                │ │
│  │                                                                        │ │
│  │ Match Type Detection:                                                │ │
│  │   - "bm25": Found only in BM25 or BM25 score > dense score          │ │
│  │   - "semantic": Found only in dense or dense score > BM25            │ │
│  │   - "hybrid": Found in both with similar scores                      │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Output: Fused results with normalized scores                               │
│  - doc_123: 0.87 (match_type=bm25, bm25_score=12.5, dense_score=0.79)      │
│  - doc_456: 0.82 (match_type=semantic, bm25_score=0, dense_score=0.88)     │
│  - doc_789: 0.75 (match_type=hybrid, bm25_score=8.3, dense_score=0.76)     │
│  ...                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: Score Filtering                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ ScoreThresholdFilter (threshold=0.3)                                  │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │ • Remove results with score < 0.3                                     │ │
│  │ • Keep only relevant results                                          │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Filtered: 10 results (5 removed below threshold)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 5: Result Enrichment                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ ResultEnricher                                                        │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │ • Batch fetch from PostgreSQL:                                        │ │
│  │   - Document metadata (filename, type, page_count)                    │ │
│  │   - Case metadata (case_number, title, court)                         │ │
│  │                                                                        │ │
│  │ • Format citations:                                                   │ │
│  │   - Documents: "contract.pdf, page 5, ¶3"                             │ │
│  │   - Transcripts: "deposition.mp4, 00:15:32"                           │ │
│  │                                                                        │ │
│  │ • Add metadata:                                                       │ │
│  │   - document_filename, document_file_type                             │ │
│  │   - case_number, case_title, case_court                               │ │
│  │   - citation (formatted)                                              │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Enriched: 10 results with full metadata                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 6: Highlight Extraction                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ HighlightExtractor                                                    │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │ • Find query terms in text                                            │ │
│  │ • Extract context (10 words before/after)                             │ │
│  │ • Max 3 highlights per result                                         │ │
│  │                                                                        │ │
│  │ Example highlights:                                                   │ │
│  │   - "...the defendant breached the contract by..."                    │ │
│  │   - "...resulting in substantial damages and..."                      │ │
│  │   - "...liability under the agreement was..."                         │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ OUTPUT: Final Results                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  {                                                                           │
│    "documents": [                                                            │
│      {                                                                       │
│        "id": "doc_123_chunk_5",                                              │
│        "content": "The defendant breached the contract...",                  │
│        "score": 0.87,                                                        │
│        "meta": {                                                             │
│          "match_type": "bm25",                                               │
│          "bm25_score": 12.5,                                                 │
│          "dense_score": 0.79,                                                │
│          "document_filename": "contract.pdf",                                │
│          "document_file_type": "pdf",                                        │
│          "case_number": "2023-CV-12345",                                     │
│          "case_title": "Smith v. Jones",                                     │
│          "case_court": "Superior Court",                                     │
│          "citation": "contract.pdf, page 5, ¶3",                             │
│          "highlights": [                                                     │
│            "...the defendant breached the contract by...",                   │
│            "...resulting in substantial damages and..."                      │
│          ]                                                                   │
│        }                                                                     │
│      },                                                                      │
│      ...                                                                     │
│    ],                                                                        │
│    "total_results": 10,                                                      │
│    "query": "contract agreement breach violation liability damages",         │
│    "mode": "hybrid"                                                          │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Interactions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COMPONENT LAYER DIAGRAM                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ Application Layer (FastAPI endpoints)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Haystack Pipeline Layer                                                      │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ HybridRetrievalPipeline                                                 │ │
│ │ • Orchestrates component execution                                      │ │
│ │ • Manages data flow between components                                  │ │
│ │ • Handles errors and logging                                            │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Haystack Component Layer                                                     │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │ Query Processing │  │ Retrieval        │  │ Ranking          │         │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤         │
│  │ • Preprocessor   │  │ • QdrantRetriever│  │ • RRFRanker      │         │
│  │ • Embedder       │  │ • OpenSearchRet. │  │ • ScoreFilter    │         │
│  │ • SparseEncoder  │  │                  │  │                  │         │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘         │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                                │
│  │ Enrichment       │  │ Extraction       │                                │
│  ├──────────────────┤  ├──────────────────┤                                │
│  │ • ResultEnricher │  │ • Highlighter    │                                │
│  │                  │  │                  │                                │
│  └──────────────────┘  └──────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Infrastructure Layer                                                         │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │ Qdrant           │  │ OpenSearch       │  │ PostgreSQL       │         │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤         │
│  │ • DocumentRepo   │  │ • DocumentRepo   │  │ • Document model │         │
│  │ • TranscriptRepo │  │ • TranscriptRepo │  │ • Case model     │         │
│  │ • CommRepo       │  │ • CommRepo       │  │                  │         │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘         │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                                │
│  │ FastEmbed        │  │ BM25Encoder      │                                │
│  ├──────────────────┤  ├──────────────────┤                                │
│  │ • Dense vectors  │  │ • Sparse vectors │                                │
│  │ • Model caching  │  │ • Tokenization   │                                │
│  └──────────────────┘  └──────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Input Query
    ↓
[Preprocessing] → Expanded query + metadata
    ↓
    ├─→ [Dense Embedding] → 384-dim vector
    │       ↓
    │   [Qdrant Search] → Dense results (cosine similarity)
    │
    └─→ [OpenSearch Search] → BM25 results (keyword scores)
    ↓
[RRF Fusion] → Combined & normalized scores
    ↓
[Score Filtering] → Results above threshold
    ↓
[Enrichment] → Full metadata from PostgreSQL
    ↓
[Highlighting] → Context snippets
    ↓
Final Results
```
