"""
Hybrid Search Service - Using Qdrant Query API

Production hybrid search implementation using:
- Qdrant Query API (v1.10+) for proper hybrid search
- FastEmbed for embeddings
- Cross-encoder reranking
- RRF and DBSF fusion methods
- Proper named sparse vector handling
"""

from typing import List, Dict, Any, Optional
import logging
from collections import defaultdict
import re
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Prefetch,
    SparseVector,
    Filter,
    Fusion,
    FusionQuery,
)

from app.core.qdrant import get_qdrant_client, build_filter
from app.core.config import settings
from app.schemas.search import (
    HybridSearchRequest,
    HybridSearchResponse,
    SearchResult,
)
from app.workers.pipelines.embeddings import FastEmbedPipeline
from app.workers.pipelines.reranker import CrossEncoderReranker
from app.workers.pipelines.bm25_encoder import BM25Encoder
from app.core.database import SessionLocal
from app.models.document import Document
from app.models.case import Case

logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """
    Modern hybrid search engine using Qdrant Query API.

    Features:
    - Multi-stage retrieval (BM25 → Dense → Rerank)
    - Proper named vector support
    - RRF and DBSF fusion
    - Cross-encoder reranking
    - FastEmbed for fast inference
    """

    def __init__(
        self,
        embedding_model_name: str = "BAAI/bge-small-en-v1.5",
        reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        collection_name: Optional[str] = None,
        enable_reranking: bool = False,  # Disabled until sentence-transformers is added
    ):
        """
        Initialize the hybrid search engine.

        Args:
            embedding_model_name: FastEmbed model for dense vectors
            reranker_model_name: Cross-encoder model for reranking
            collection_name: Qdrant collection name
            enable_reranking: Enable cross-encoder reranking
        """
        self.embedding_model_name = embedding_model_name
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.client = get_qdrant_client()
        self.enable_reranking = enable_reranking

        logger.info(f"HybridSearchEngine initialized")
        logger.info(f"  Embedding model: {embedding_model_name}")
        logger.info(f"  Reranking: {enable_reranking}")

        # Initialize components
        self.embed_pipeline = FastEmbedPipeline(model_name=embedding_model_name)
        self.bm25_encoder = BM25Encoder()

        if enable_reranking:
            self.reranker = CrossEncoderReranker(model_name=reranker_model_name)
        else:
            self.reranker = None

        # Simple in-memory caches for ID↔GID lookups within a single process
        self._document_gid_cache: Dict[str, Optional[str]] = {}
        self._case_gid_cache: Dict[str, Optional[str]] = {}
        self._document_uuid_cache: Dict[str, Optional[str]] = {}
        self._case_uuid_cache: Dict[str, Optional[str]] = {}

    def _create_sparse_vector(self, text: str) -> SparseVector:
        """
        Create BM25 sparse vector from text.

        Args:
            text: Input text

        Returns:
            Qdrant SparseVector
        """
        indices, values = self.bm25_encoder.encode_to_qdrant_format(text)
        return SparseVector(indices=indices, values=values)

    def _create_dense_vector(self, text: str) -> List[float]:
        """
        Create dense embedding from text.

        Args:
            text: Input text

        Returns:
            Embedding vector as list
        """
        embedding = self.embed_pipeline.generate_single_embedding(text)
        return embedding.tolist()

    def _normalize_and_boost_scores(
        self,
        results: List[Dict[str, Any]],
        raw_scores: List[float],
        fusion_method: str,
        bm25_scores: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """
        Normalize RRF/DBSF scores to 0-1 range and boost keyword matches.

        RRF scores are rank-based (1/(rank+k)) and typically range 0-0.02 for k=60.
        We need to:
        1. Normalize to 0-1 range using min-max scaling
        2. Boost results with strong BM25 scores (keyword matches)
        3. Apply non-linear scaling to spread out the top results

        Args:
            results: Search results with raw scores
            raw_scores: List of raw fusion scores
            fusion_method: Fusion method used (rrf or dbsf)
            bm25_scores: Dictionary of BM25 scores by point ID

        Returns:
            Results with normalized and boosted scores
        """
        if not results or not raw_scores:
            return results

        # Calculate score statistics
        min_score = min(raw_scores)
        max_score = max(raw_scores)
        score_range = max_score - min_score

        # Avoid division by zero
        if score_range < 1e-9:
            # All scores are the same, assign uniform scores
            for result in results:
                result["score"] = 0.7
            return results

        # Step 1: Min-max normalization to 0-1
        for i, result in enumerate(results):
            normalized_score = (raw_scores[i] - min_score) / score_range

            # Step 2: Boost keyword matches
            point_id = result["id"]
            bm25_score = bm25_scores.get(point_id, 0.0)

            # Keyword boost: High BM25 scores indicate strong keyword matches
            # BM25 scores typically range 0-20+ for good matches
            keyword_boost = 0.0
            if bm25_score > 0:
                # Normalize BM25 score and apply as boost
                # Strong keyword matches (BM25 > 5) get significant boost
                bm25_normalized = min(bm25_score / 10.0, 1.0)  # Cap at 1.0
                keyword_boost = bm25_normalized * 0.3  # Up to +0.3 boost

            # Step 3: Apply non-linear scaling for better score distribution
            # Use power scaling to spread out top results
            if fusion_method == "rrf":
                # RRF benefits from square root scaling to spread scores
                boosted_score = (normalized_score ** 0.7) + keyword_boost
            else:
                # DBSF is already normalized, apply lighter scaling
                boosted_score = (normalized_score ** 0.85) + keyword_boost

            # Step 4: Ensure keyword-only matches get high scores
            # If BM25 score is very high and it's a top result, boost to 0.85+
            if bm25_score > 5.0 and i < 5:
                boosted_score = max(boosted_score, 0.85 + (bm25_normalized * 0.1))

            # Clamp to 0-1 range
            boosted_score = max(0.0, min(1.0, boosted_score))

            result["score"] = boosted_score

            # Add debug info
            result["_score_debug"] = {
                "raw_fusion_score": raw_scores[i],
                "normalized_fusion": normalized_score,
                "actual_bm25_score": bm25_score,
                "actual_dense_score": result.get("dense_score", 0.0),
                "keyword_boost": keyword_boost,
                "final_score": boosted_score,
            }

        logger.info(
            f"Score normalization complete: "
            f"raw range [{min_score:.4f}, {max_score:.4f}] -> "
            f"normalized range [0.0, 1.0]"
        )

        return results

    def _resolve_document_gid(self, document_id: Any) -> Optional[str]:
        """Resolve document UUID to GID with simple caching."""
        if document_id is None:
            return None

        doc_key = str(document_id)
        if doc_key in self._document_gid_cache:
            return self._document_gid_cache[doc_key]

        try:
            uuid_val = UUID(doc_key)
        except (ValueError, TypeError):
            self._document_gid_cache[doc_key] = None
            return None

        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == uuid_val).first()
            gid = document.gid if document else None
        except Exception as exc:
            logger.error(f"Failed to resolve document GID for {doc_key}: {exc}", exc_info=True)
            gid = None
        finally:
            db.close()

        self._document_gid_cache[doc_key] = gid
        return gid

    def _resolve_case_gid(self, case_id: Any) -> Optional[str]:
        """Resolve case UUID to GID with simple caching."""
        if case_id is None:
            return None

        case_key = str(case_id)
        if case_key in self._case_gid_cache:
            return self._case_gid_cache[case_key]

        try:
            uuid_val = UUID(case_key)
        except (ValueError, TypeError):
            self._case_gid_cache[case_key] = None
            return None

        db = SessionLocal()
        try:
            case = db.query(Case).filter(Case.id == uuid_val).first()
            gid = case.gid if case else None
        except Exception as exc:
            logger.error(f"Failed to resolve case GID for {case_key}: {exc}", exc_info=True)
            gid = None
        finally:
            db.close()

        self._case_gid_cache[case_key] = gid
        return gid

    def _resolve_document_uuid_from_gid(self, document_gid: str) -> Optional[str]:
        """Resolve document GID back to UUID string with caching."""
        if not document_gid:
            return None

        if document_gid in self._document_uuid_cache:
            return self._document_uuid_cache[document_gid]

        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.gid == document_gid).first()
            uuid_value = str(document.id) if document else None
        except Exception as exc:
            logger.error(f"Failed to resolve document UUID for GID {document_gid}: {exc}", exc_info=True)
            uuid_value = None
        finally:
            db.close()

        self._document_uuid_cache[document_gid] = uuid_value
        return uuid_value

    def _resolve_case_uuid_from_gid(self, case_gid: str) -> Optional[str]:
        """Resolve case GID back to UUID string with caching."""
        if not case_gid:
            return None

        if case_gid in self._case_uuid_cache:
            return self._case_uuid_cache[case_gid]

        db = SessionLocal()
        try:
            case = db.query(Case).filter(Case.gid == case_gid).first()
            uuid_value = str(case.id) if case else None
        except Exception as exc:
            logger.error(f"Failed to resolve case UUID for GID {case_gid}: {exc}", exc_info=True)
            uuid_value = None
        finally:
            db.close()

        self._case_uuid_cache[case_gid] = uuid_value
        return uuid_value

    def search_keyword_only(
        self,
        request: HybridSearchRequest,
    ) -> List[Dict[str, Any]]:
        """
        Pure BM25 keyword search - no fusion, no dense vectors, no reranking.

        Used for exact keyword/phrase matching.

        Args:
            request: Search request

        Returns:
            List of search results with BM25 scores
        """
        try:
            case_ids_filter_set = {str(cid) for cid in (request.case_ids or []) if cid is not None}
            if request.case_gids:
                for gid in request.case_gids:
                    resolved = self._resolve_case_uuid_from_gid(gid)
                    if resolved:
                        case_ids_filter_set.add(resolved)

            document_ids_filter_set = {str(did) for did in (request.document_ids or []) if did is not None}
            if request.document_gids:
                for gid in request.document_gids:
                    resolved = self._resolve_document_uuid_from_gid(gid)
                    if resolved:
                        document_ids_filter_set.add(resolved)

            case_ids_filter = list(case_ids_filter_set) if case_ids_filter_set else None
            case_gids_filter = None if case_ids_filter else request.case_gids
            document_ids_filter = list(document_ids_filter_set) if document_ids_filter_set else None
            document_gids_filter = None if document_ids_filter else request.document_gids

            # Build filters
            filters = build_filter(
                case_ids=case_ids_filter,
                case_gids=case_gids_filter,
                document_ids=document_ids_filter,
                document_gids=document_gids_filter,
                chunk_types=request.chunk_types,
            )

            # Log filter details
            logger.info(
                "Keyword-only search filters: case_ids=%s, case_gids=%s, document_ids=%s, document_gids=%s, chunk_types=%s",
                case_ids_filter,
                case_gids_filter,
                document_ids_filter,
                document_gids_filter,
                request.chunk_types,
            )
            if filters:
                logger.info(f"Filter conditions: {filters.model_dump() if hasattr(filters, 'model_dump') else filters}")

            # Create BM25 sparse vector
            sparse_vector = self._create_sparse_vector(request.query)
            logger.info(f"BM25 query vector: {len(sparse_vector.indices)} tokens")
            if sparse_vector.indices:
                logger.info(f"First 3 token IDs: {sparse_vector.indices[:3]}, values: {sparse_vector.values[:3]}")

            # Search with BM25 only using Prefetch (which supports filters)
            results = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=[
                    Prefetch(
                        query=sparse_vector,
                        using="bm25",
                        filter=filters,
                        limit=request.top_k * 3,  # Get more for threshold filtering
                    )
                ],
                query=FusionQuery(fusion=Fusion.RRF),  # Single prefetch, no actual fusion
                limit=request.top_k * 3,
                with_payload=True,
            )

            # Convert to standard format
            formatted_results = []
            for point in results.points:
                score = point.score if point.score is not None else 0.0

                formatted_results.append({
                    "id": str(point.id),
                    "score": score,  # Raw BM25 score
                    "payload": point.payload if point.payload else {},
                    "bm25_score": score,  # Same as score for keyword-only
                })

            logger.info(
                f"Keyword-only search returned {len(formatted_results)} results"
            )
            return formatted_results

        except Exception as e:
            logger.error(f"Error in keyword-only search: {e}", exc_info=True)
            raise

    def search_with_query_api(
        self,
        request: HybridSearchRequest,
    ) -> List[Dict[str, Any]]:
        """
        Search using Qdrant Query API with hybrid approach.

        Uses prefetch for initial retrieval and Query API for fusion.
        Performs separate BM25 and dense searches to track individual scores.

        Args:
            request: Search request

        Returns:
            List of search results with normalized scores
        """
        try:
            case_ids_filter_set = {str(cid) for cid in (request.case_ids or []) if cid is not None}
            if request.case_gids:
                for gid in request.case_gids:
                    resolved = self._resolve_case_uuid_from_gid(gid)
                    if resolved:
                        case_ids_filter_set.add(resolved)

            document_ids_filter_set = {str(did) for did in (request.document_ids or []) if did is not None}
            if request.document_gids:
                for gid in request.document_gids:
                    resolved = self._resolve_document_uuid_from_gid(gid)
                    if resolved:
                        document_ids_filter_set.add(resolved)

            case_ids_filter = list(case_ids_filter_set) if case_ids_filter_set else None
            case_gids_filter = None if case_ids_filter else request.case_gids
            document_ids_filter = list(document_ids_filter_set) if document_ids_filter_set else None
            document_gids_filter = None if document_ids_filter else request.document_gids

            # Build filters
            filters = build_filter(
                case_ids=case_ids_filter,
                case_gids=case_gids_filter,
                document_ids=document_ids_filter,
                document_gids=document_gids_filter,
                chunk_types=request.chunk_types,
            )

            # Log filter details
            logger.info(
                "Query API search filters: case_ids=%s, case_gids=%s, document_ids=%s, document_gids=%s, chunk_types=%s",
                case_ids_filter,
                case_gids_filter,
                document_ids_filter,
                document_gids_filter,
                request.chunk_types,
            )
            if filters:
                logger.info(f"Filter conditions: {filters.model_dump() if hasattr(filters, 'model_dump') else filters}")

            # Step 1: Perform separate searches to get individual scores
            bm25_results_map = {}  # Map point_id -> BM25 score
            dense_results_map = {}  # Map point_id -> dense score

            # Perform BM25 search if enabled
            if request.use_bm25:
                sparse_vector = self._create_sparse_vector(request.query)
                logger.info(f"Performing BM25 search with {len(sparse_vector.indices)} tokens")

                bm25_search = self.client.query_points(
                    collection_name=self.collection_name,
                    prefetch=[
                        Prefetch(
                            query=sparse_vector,
                            using="bm25",
                            filter=filters,
                            limit=request.top_k * 2,
                        )
                    ],
                    query=FusionQuery(fusion=Fusion.RRF),  # Single prefetch, no actual fusion
                    limit=request.top_k * 2,
                    with_payload=True,
                )

                for point in bm25_search.points:
                    bm25_results_map[str(point.id)] = point.score if point.score else 0.0

                logger.info(f"BM25 search returned {len(bm25_results_map)} results")

            # Perform dense vector search if enabled
            if request.use_dense:
                dense_vector = self._create_dense_vector(request.query)
                logger.info("Performing dense vector search across summary/section/microblock")

                # Search all dense vector types
                dense_prefetch = []
                for vector_name in ["summary", "section", "microblock"]:
                    dense_prefetch.append(
                        Prefetch(
                            query=dense_vector,
                            using=vector_name,
                            filter=filters,
                            limit=request.top_k,
                        )
                    )

                dense_search = self.client.query_points(
                    collection_name=self.collection_name,
                    prefetch=dense_prefetch,
                    query=FusionQuery(fusion=Fusion.RRF),  # Fuse dense vectors together
                    limit=request.top_k * 2,
                    with_payload=True,
                )

                for point in dense_search.points:
                    dense_results_map[str(point.id)] = point.score if point.score else 0.0

                logger.info(f"Dense search returned {len(dense_results_map)} results")

            # Step 2: Perform hybrid fusion if both enabled
            if request.use_bm25 and request.use_dense:
                # Build prefetch queries for hybrid fusion
                prefetch_queries = []

                sparse_vector = self._create_sparse_vector(request.query)
                prefetch_queries.append(
                    Prefetch(
                        query=sparse_vector,
                        using="bm25",
                        filter=filters,
                        limit=request.top_k * 2,
                    )
                )

                dense_vector = self._create_dense_vector(request.query)
                for vector_name in ["summary", "section", "microblock"]:
                    prefetch_queries.append(
                        Prefetch(
                            query=dense_vector,
                            using=vector_name,
                            filter=filters,
                            limit=request.top_k,
                        )
                    )

                # Determine fusion method
                if request.fusion_method == "rrf":
                    fusion = Fusion.RRF
                elif request.fusion_method == "dbsf":
                    fusion = Fusion.DBSF
                else:
                    fusion = Fusion.RRF  # Default

                # Execute hybrid fusion
                logger.info(f"Performing hybrid fusion with {request.fusion_method}")
                results = self.client.query_points(
                    collection_name=self.collection_name,
                    prefetch=prefetch_queries,
                    query=FusionQuery(fusion=fusion),
                    limit=request.top_k * 3,
                    with_payload=True,
                )
            elif request.use_bm25:
                # BM25 only
                results = bm25_search
            elif request.use_dense:
                # Dense only
                results = dense_search
            else:
                # No search enabled
                logger.warning("Neither BM25 nor dense search enabled")
                return []

            # Step 3: Format results with actual BM25 and dense scores
            formatted_results = []
            raw_scores = []
            bm25_scores = {}  # Track actual BM25 scores by point ID

            for point in results.points:
                score = point.score if point.score is not None else 0.0
                raw_scores.append(score)
                point_id = str(point.id)

                # Get actual BM25 score from separate search (not fusion score!)
                actual_bm25_score = bm25_results_map.get(point_id, 0.0)
                actual_dense_score = dense_results_map.get(point_id, 0.0)

                formatted_results.append({
                    "id": point_id,
                    "score": score,  # Fusion score
                    "payload": point.payload if point.payload else {},
                    "bm25_score": actual_bm25_score,  # Actual BM25 score
                    "dense_score": actual_dense_score,  # Actual dense score
                })

                # Use actual BM25 score for boosting (not fusion score!)
                bm25_scores[point_id] = actual_bm25_score

            # Log search statistics
            bm25_only_count = sum(1 for r in formatted_results if r["bm25_score"] > 0 and r["dense_score"] == 0)
            dense_only_count = sum(1 for r in formatted_results if r["dense_score"] > 0 and r["bm25_score"] == 0)
            both_count = sum(1 for r in formatted_results if r["bm25_score"] > 0 and r["dense_score"] > 0)

            logger.info(
                f"Result breakdown: {bm25_only_count} BM25-only, "
                f"{dense_only_count} dense-only, {both_count} in both"
            )

            # Normalize and boost scores
            formatted_results = self._normalize_and_boost_scores(
                formatted_results,
                raw_scores,
                request.fusion_method,
                bm25_scores,
            )

            logger.info(
                f"Query API returned {len(formatted_results)} results "
                f"(before threshold filtering)"
            )
            return formatted_results

        except Exception as e:
            logger.error(f"Error in Query API search: {e}", exc_info=True)
            raise

    def search(
        self,
        request: HybridSearchRequest,
    ) -> HybridSearchResponse:
        """
        Main search method with reranking and score filtering.

        Pipeline:
        1. Hybrid search with Query API (BM25 + Dense + Fusion)
           - If no chunk_types filter: Do separate document + transcript searches and merge
           - If chunk_types specified: Single search with filter
        2. Score normalization and boosting
        3. Score threshold filtering
        4. Cross-encoder reranking (optional)
        5. Format results

        Args:
            request: Search request

        Returns:
            Search response with normalized scores
        """
        import time
        start_time = time.time()

        try:
            # Stage 1: Hybrid search with score normalization
            # If no chunk_types filter specified, do separate searches for documents and transcripts
            # to ensure both appear in results (transcripts score lower and get excluded otherwise)
            if not request.chunk_types or len(request.chunk_types) == 0:
                logger.info("No chunk_types filter - performing separate document and transcript searches")

                # Search documents (summary, section, microblock) - get top 40
                doc_request = HybridSearchRequest(
                    query=request.query,
                    use_bm25=request.use_bm25,
                    use_dense=request.use_dense,
                    fusion_method=request.fusion_method,
                    top_k=40,  # Reserve 40 slots for documents
                    score_threshold=request.score_threshold,
                    chunk_types=["summary", "section", "microblock"],
                    case_ids=request.case_ids,
                    case_gids=request.case_gids,
                    document_ids=request.document_ids,
                    document_gids=request.document_gids,
                )
                doc_results = self.search_with_query_api(doc_request)
                logger.info(f"Document search returned {len(doc_results)} results")

                # Search transcripts - get top 10
                transcript_request = HybridSearchRequest(
                    query=request.query,
                    use_bm25=request.use_bm25,
                    use_dense=request.use_dense,
                    fusion_method=request.fusion_method,
                    top_k=10,  # Reserve 10 slots for transcripts
                    score_threshold=request.score_threshold,
                    chunk_types=["transcript_segment"],
                    case_ids=request.case_ids,
                    case_gids=request.case_gids,
                    document_ids=request.document_ids,
                    document_gids=request.document_gids,
                )
                transcript_results = self.search_with_query_api(transcript_request)
                logger.info(f"Transcript search returned {len(transcript_results)} results")

                # Merge results and re-sort by score
                search_results = doc_results + transcript_results
                search_results.sort(key=lambda x: x["score"], reverse=True)
                logger.info(f"Merged search: {len(search_results)} total results ({len(doc_results)} docs + {len(transcript_results)} transcripts)")
            else:
                # Normal single search with chunk_types filter
                search_results = self.search_with_query_api(request)

            # Stage 2: Apply score threshold filtering
            score_threshold = request.score_threshold if request.score_threshold is not None else 0.3
            results_before_filtering = len(search_results)

            search_results = [
                result for result in search_results
                if result["score"] >= score_threshold
            ]

            filtered_count = results_before_filtering - len(search_results)
            if filtered_count > 0:
                logger.info(
                    f"Filtered out {filtered_count} results below "
                    f"threshold {score_threshold:.2f}"
                )

            # Stage 3: Limit to top_k after filtering
            search_results = search_results[:request.top_k]

            # Stage 4: Reranking (optional)
            if self.enable_reranking and self.reranker and len(search_results) > 0:
                logger.info(f"Reranking {len(search_results)} results")
                search_results = self.reranker.rerank_search_results(
                    query=request.query,
                    search_results=search_results,
                    top_k=request.top_k,
                    text_key="payload.text",  # Nested key
                )

            # Stage 5: Format results
            formatted_results = []
            for result in search_results:
                payload = result.get("payload", {})

                # Extract text from payload
                text = payload.get("text", "")

                # Extract highlights (simple implementation)
                highlights = self._extract_highlights(text, request.query)

                # Determine match type based on actual BM25 and dense scores
                # Use the actual scores from separate searches, not fusion scores
                actual_bm25_score = result.get("bm25_score", 0.0)
                actual_dense_score = result.get("dense_score", 0.0)

                # Determine match type based on which search found it
                if actual_bm25_score > 0 and actual_dense_score > 0:
                    # Found by both searches - determine which one ranked it higher
                    if actual_bm25_score > actual_dense_score:
                        match_type = "bm25"
                    else:
                        match_type = "semantic"
                elif actual_bm25_score > 0:
                    # Only BM25 found this
                    match_type = "bm25"
                elif actual_dense_score > 0:
                    # Only dense vector found this
                    match_type = "semantic"
                else:
                    # Neither found it (shouldn't happen, but default to hybrid)
                    match_type = "hybrid"

                document_id_raw = payload.get("document_id")
                document_id = str(document_id_raw) if document_id_raw is not None else None
                if document_id is not None:
                    payload["document_id"] = document_id

                document_gid = payload.get("document_gid")
                if not document_gid and document_id:
                    document_gid = self._resolve_document_gid(document_id)
                    if document_gid:
                        payload["document_gid"] = document_gid

                case_id_raw = payload.get("case_id")
                case_id = str(case_id_raw) if case_id_raw is not None else None
                if case_id is not None:
                    payload["case_id"] = case_id

                case_gid = payload.get("case_gid")
                if not case_gid and case_id:
                    case_gid = self._resolve_case_gid(case_id)
                    if case_gid:
                        payload["case_gid"] = case_gid

                chunk_identifier = str(result["id"])

                formatted_results.append(
                    SearchResult(
                        id=chunk_identifier,
                        gid=chunk_identifier,
                        score=result["score"],
                        text=text,
                        match_type=match_type,
                        page_number=payload.get("page_number"),
                        bboxes=payload.get("bboxes", []),
                        metadata={
                            "document_id": document_id,
                            "document_gid": document_gid,
                            "case_id": case_id,
                            "case_gid": case_gid,
                            "chunk_type": payload.get("chunk_type"),
                            "position": payload.get("position"),
                            "bm25_score": actual_bm25_score,
                            "dense_score": actual_dense_score,
                            "score_debug": result.get("_score_debug"),
                            "point_id": chunk_identifier,
                        },
                        highlights=highlights,
                        vector_type=payload.get("chunk_type"),
                    )
                )

            # Calculate execution time
            search_time_ms = int((time.time() - start_time) * 1000)

            # Calculate result type statistics
            bm25_matches = sum(1 for r in formatted_results if r.match_type == "bm25")
            semantic_matches = sum(1 for r in formatted_results if r.match_type == "semantic")
            hybrid_matches = sum(1 for r in formatted_results if r.match_type == "hybrid")

            # Build response
            response = HybridSearchResponse(
                results=formatted_results,
                total_results=len(formatted_results),
                query=request.query,
                search_metadata={
                    "search_time_ms": search_time_ms,
                    "fusion_method": request.fusion_method,
                    "reranking_enabled": self.enable_reranking,
                    "score_threshold": score_threshold,
                    "results_filtered": filtered_count,
                    "use_bm25": request.use_bm25,
                    "use_dense": request.use_dense,
                    "match_breakdown": {
                        "bm25_matches": bm25_matches,
                        "semantic_matches": semantic_matches,
                        "hybrid_matches": hybrid_matches,
                    },
                    "filters_applied": {
                        "case_ids": request.case_ids,
                        "case_gids": request.case_gids,
                        "document_ids": request.document_ids,
                        "document_gids": request.document_gids,
                        "chunk_types": request.chunk_types,
                    },
                },
            )

            logger.info(
                f"Hybrid search completed in {search_time_ms}ms: "
                f"{len(formatted_results)} results (filtered {filtered_count}), "
                f"Match breakdown: {bm25_matches} BM25, {semantic_matches} semantic, {hybrid_matches} hybrid"
            )

            return response

        except Exception as e:
            logger.error(f"Hybrid search error: {e}", exc_info=True)
            raise

    def _extract_highlights(
        self,
        text: str,
        query: str,
        max_highlights: int = 3,
        context_words: int = 10,
    ) -> Optional[List[str]]:
        """
        Extract highlighted snippets from text.

        Args:
            text: Source text
            query: Search query
            max_highlights: Max number of highlights
            context_words: Context words around match

        Returns:
            List of highlight snippets
        """
        if not text or not query:
            return None

        # Simple tokenization
        query_tokens = set(query.lower().split())
        words = text.split()
        highlights = []

        for i, word in enumerate(words):
            clean_word = re.sub(r'[^\w\s]', '', word.lower())
            if clean_word in query_tokens:
                start = max(0, i - context_words)
                end = min(len(words), i + context_words + 1)
                snippet = " ".join(words[start:end])

                if start > 0:
                    snippet = "..." + snippet
                if end < len(words):
                    snippet = snippet + "..."

                highlights.append(snippet)

                if len(highlights) >= max_highlights:
                    break

        return highlights if highlights else None


# Singleton instance
_search_engine_instance: Optional[HybridSearchEngine] = None


def get_search_engine() -> HybridSearchEngine:
    """
    Get or create singleton HybridSearchEngine instance.

    Returns:
        HybridSearchEngine instance
    """
    global _search_engine_instance

    if _search_engine_instance is None:
        _search_engine_instance = HybridSearchEngine()
        logger.info("Created new HybridSearchEngine singleton instance")

    return _search_engine_instance
