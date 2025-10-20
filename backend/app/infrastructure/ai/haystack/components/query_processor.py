"""
Query preprocessing components for legal search.

Provides query expansion, legal synonym mapping, citation preservation,
and stopword filtering tailored for legal documents.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Set

from haystack import component

logger = logging.getLogger(__name__)


@component
class LegalQueryPreprocessor:
    """
    Preprocesses search queries for legal document retrieval.

    Features:
    - Legal synonym expansion (attorney ↔ lawyer, contract ↔ agreement)
    - Citation detection and preservation
    - Legal stopword handling (preserve important legal terms)
    - Spell correction (optional)
    - Query normalization

    Example:
        "Find all contracts with attorney Jones" →
        "Find all contracts agreements with attorney lawyer Jones"
    """

    # Legal synonym mappings
    LEGAL_SYNONYMS = {
        "attorney": ["lawyer", "counsel"],
        "lawyer": ["attorney", "counsel"],
        "counsel": ["attorney", "lawyer"],
        "contract": ["agreement"],
        "agreement": ["contract"],
        "plaintiff": ["claimant", "petitioner"],
        "defendant": ["respondent"],
        "testimony": ["deposition", "statement"],
        "evidence": ["proof", "exhibit"],
        "damages": ["compensation", "award"],
        "breach": ["violation", "infringement"],
        "liability": ["responsibility", "accountability"],
        "negligence": ["carelessness", "fault"],
        "motion": ["application", "petition"],
        "judgment": ["ruling", "decision", "decree"],
        "appeal": ["review"],
        "discovery": ["disclosure"],
        "settlement": ["resolution", "accord"],
        "injunction": ["order", "restraining order"],
        "subpoena": ["summons"],
    }

    # Legal stopwords to PRESERVE (don't remove these)
    LEGAL_PRESERVE_WORDS = {
        "court", "law", "legal", "case", "plaintiff", "defendant",
        "evidence", "testimony", "contract", "agreement", "statute",
        "regulation", "ruling", "judgment", "motion", "appeal",
        "damages", "liability", "negligence", "breach", "violation",
        "attorney", "lawyer", "counsel", "judge", "jury",
        "trial", "hearing", "deposition", "discovery", "settlement",
        "injunction", "subpoena", "warrant", "summons", "complaint",
        "answer", "counterclaim", "cross-claim", "affidavit", "exhibit",
        "precedent", "jurisdiction", "venue", "standing", "cause",
        "action", "remedy", "relief", "petition", "respondent",
    }

    # Citation patterns to preserve
    CITATION_PATTERNS = [
        # Federal reporters: 123 F.3d 456
        r'\d+\s+F\.\s?(?:2d|3d|Supp\.?)\s+\d+',
        # Supreme Court: 123 U.S. 456
        r'\d+\s+U\.S\.\s+\d+',
        # State reporters: 123 N.Y. 456
        r'\d+\s+[A-Z]{2,}\.\s?(?:2d|3d)?\s+\d+',
        # Statute citations: 42 U.S.C. § 1983
        r'\d+\s+U\.S\.C\.\s+§\s+\d+',
        # Code citations: Cal. Civ. Code § 1234
        r'[A-Z][a-z]+\.\s+[A-Z][a-z]+\.\s+Code\s+§\s+\d+',
    ]

    def __init__(
        self,
        expand_synonyms: bool = True,
        preserve_citations: bool = True,
        remove_common_stopwords: bool = False,
        max_synonym_expansions: int = 2,
    ):
        """
        Initialize legal query preprocessor.

        Args:
            expand_synonyms: Whether to expand legal synonyms
            preserve_citations: Whether to detect and preserve citations
            remove_common_stopwords: Whether to remove common stopwords (but preserve legal ones)
            max_synonym_expansions: Maximum number of synonyms to add per term
        """
        self.expand_synonyms = expand_synonyms
        self.preserve_citations = preserve_citations
        self.remove_common_stopwords = remove_common_stopwords
        self.max_synonym_expansions = max_synonym_expansions

        # Compile citation patterns
        self.citation_regex = re.compile(
            '|'.join(self.CITATION_PATTERNS),
            re.IGNORECASE
        )

        # Common English stopwords (but we'll preserve legal ones)
        self.common_stopwords = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
            'that', 'the', 'to', 'was', 'will', 'with',
        }

        logger.info(
            f"Initialized LegalQueryPreprocessor "
            f"(synonyms={expand_synonyms}, citations={preserve_citations})"
        )

    @component.output_types(query=str, metadata=Dict[str, Any])
    def run(self, query: str) -> Dict[str, Any]:
        """
        Preprocess a legal search query.

        Args:
            query: Raw search query

        Returns:
            Dict with 'query' (processed) and 'metadata' (processing info)
        """
        original_query = query
        metadata = {
            "original_query": original_query,
            "citations_found": [],
            "synonyms_added": [],
            "tokens_removed": [],
        }

        # Step 1: Extract and preserve citations
        citations = []
        citation_placeholders = {}

        if self.preserve_citations:
            for match in self.citation_regex.finditer(query):
                citation = match.group(0)
                placeholder = f"__CITATION_{len(citations)}__"
                citations.append(citation)
                citation_placeholders[placeholder] = citation
                query = query.replace(citation, placeholder, 1)

            if citations:
                metadata["citations_found"] = citations
                logger.info(f"Preserved {len(citations)} citations: {citations}")

        # Step 2: Normalize query
        query = query.lower().strip()

        # Step 3: Expand legal synonyms
        if self.expand_synonyms:
            query, synonyms_added = self._expand_synonyms(query)
            metadata["synonyms_added"] = synonyms_added

        # Step 4: Remove stopwords (but preserve legal terms)
        if self.remove_common_stopwords:
            original_tokens = query.split()
            filtered_tokens = []
            removed = []

            for token in original_tokens:
                # Keep if it's a legal term, citation placeholder, or not a stopword
                if (token in self.LEGAL_PRESERVE_WORDS or
                    token.startswith("__CITATION_") or
                    token not in self.common_stopwords):
                    filtered_tokens.append(token)
                else:
                    removed.append(token)

            query = " ".join(filtered_tokens)
            if removed:
                metadata["tokens_removed"] = removed
                logger.debug(f"Removed {len(removed)} common stopwords")

        # Step 5: Restore citations
        for placeholder, citation in citation_placeholders.items():
            query = query.replace(placeholder.lower(), citation)

        # Step 6: Clean up extra whitespace
        query = re.sub(r'\s+', ' ', query).strip()

        logger.info(f"Query preprocessed: '{original_query}' → '{query}'")

        return {
            "query": query,
            "metadata": metadata,
        }

    def _expand_synonyms(self, query: str) -> tuple[str, List[str]]:
        """
        Expand legal synonyms in the query.

        Args:
            query: Query text

        Returns:
            Tuple of (expanded query, list of synonyms added)
        """
        words = query.split()
        expanded_words = []
        synonyms_added = []

        for word in words:
            expanded_words.append(word)

            # Check if word has legal synonyms
            if word in self.LEGAL_SYNONYMS:
                synonyms = self.LEGAL_SYNONYMS[word][:self.max_synonym_expansions]
                expanded_words.extend(synonyms)
                synonyms_added.extend(synonyms)

        if synonyms_added:
            logger.debug(f"Added {len(synonyms_added)} synonyms: {synonyms_added}")

        return " ".join(expanded_words), synonyms_added


@component
class QueryEmbedder:
    """
    Converts query text to dense embeddings using FastEmbed.

    Wrapper around FastEmbedPipeline for use in Haystack pipelines.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
    ):
        """
        Initialize query embedder.

        Args:
            model_name: FastEmbed model name
        """
        from app.workers.pipelines.embeddings import FastEmbedPipeline

        self.model_name = model_name
        self.embed_pipeline = FastEmbedPipeline(model_name=model_name)

        logger.info(f"Initialized QueryEmbedder (model={model_name})")

    @component.output_types(embedding=List[float])
    def run(self, query: str) -> Dict[str, List[float]]:
        """
        Generate embedding for query.

        Args:
            query: Query text

        Returns:
            Dict with 'embedding' key containing vector
        """
        embedding = self.embed_pipeline.generate_single_embedding(query)
        vector = embedding.tolist()

        logger.debug(f"Generated query embedding: {len(vector)} dimensions")

        return {"embedding": vector}


@component
class QuerySparseEncoder:
    """
    Converts query text to BM25 sparse vectors.

    Wrapper around BM25Encoder for use in Haystack pipelines.
    """

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        """
        Initialize query sparse encoder.

        Args:
            k1: BM25 k1 parameter
            b: BM25 b parameter
        """
        from app.workers.pipelines.bm25_encoder import BM25Encoder

        self.bm25_encoder = BM25Encoder(k1=k1, b=b)

        logger.info(f"Initialized QuerySparseEncoder (k1={k1}, b={b})")

    @component.output_types(sparse_vector=Dict[str, Any])
    def run(self, query: str) -> Dict[str, Any]:
        """
        Generate BM25 sparse vector for query.

        Args:
            query: Query text

        Returns:
            Dict with 'sparse_vector' containing indices and values
        """
        indices, values = self.bm25_encoder.encode_to_qdrant_format(query)

        sparse_vector = {
            "indices": indices,
            "values": values,
        }

        logger.debug(f"Generated BM25 sparse vector: {len(indices)} tokens")

        return {"sparse_vector": sparse_vector}
