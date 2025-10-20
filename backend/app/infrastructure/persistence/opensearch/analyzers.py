"""
Custom analyzers for legal document processing in OpenSearch.

This module defines specialized text analyzers for legal documents:
- legal_analyzer: For general legal text with legal stopwords and synonyms
- shingle_analyzer: For phrase matching
- citation_analyzer: For legal citations (case law, statutes, etc.)
"""

from typing import Dict, Any


# Common legal stopwords to filter out (in addition to English stopwords)
LEGAL_STOPWORDS = [
    "plaintiff", "defendant", "court", "case", "appeal", "petition",
    "motion", "order", "judgment", "decree", "complaint", "answer",
    "whereas", "hereby", "thereof", "therein", "thereto", "aforesaid",
    "hereafter", "hereinafter", "pursuant", "notwithstanding",
]

# Legal synonym pairs for query expansion
LEGAL_SYNONYMS = [
    "contract, agreement, covenant",
    "terminate, cancel, rescind",
    "plaintiff, claimant, petitioner",
    "defendant, respondent",
    "attorney, lawyer, counsel, advocate",
    "damages, compensation, restitution",
    "guilty, liable, culpable",
    "evidence, proof, testimony",
    "witness, testify, depose",
    "fraud, misrepresentation, deceit",
    "negligence, malpractice, breach of duty",
    "injunction, restraining order",
    "verdict, judgment, ruling, decision",
    "statute, law, regulation, code",
    "precedent, case law, jurisprudence",
]


def get_legal_analyzer() -> Dict[str, Any]:
    """
    Get analyzer configuration for legal documents.

    This analyzer:
    - Uses standard tokenizer
    - Lowercases tokens
    - Removes common legal stopwords
    - Applies stemming (snowball)
    - Expands synonyms for legal terms

    Returns:
        Analyzer configuration dictionary
    """
    return {
        "type": "custom",
        "tokenizer": "standard",
        "filter": [
            "lowercase",
            "legal_stopwords",
            "snowball",
            "legal_synonyms",
        ]
    }


def get_shingle_analyzer() -> Dict[str, Any]:
    """
    Get analyzer for phrase matching using shingles.

    Shingles are n-gram phrases (2-3 word combinations) that help
    with finding exact phrases and improve relevance.

    Returns:
        Shingle analyzer configuration dictionary
    """
    return {
        "type": "custom",
        "tokenizer": "standard",
        "filter": [
            "lowercase",
            "shingle_filter",
        ]
    }


def get_citation_analyzer() -> Dict[str, Any]:
    """
    Get analyzer for legal citations.

    This analyzer preserves:
    - Case numbers (e.g., "123 F.3d 456")
    - Statute references (e.g., "18 U.S.C. § 1001")
    - Court identifiers (e.g., "9th Cir.")

    Returns:
        Citation analyzer configuration dictionary
    """
    return {
        "type": "pattern",
        "pattern": r"[\s,;]+",  # Split on whitespace, commas, semicolons
        "lowercase": False,  # Preserve case for citations
    }


def get_token_filters() -> Dict[str, Any]:
    """
    Get custom token filter definitions.

    Returns:
        Dictionary of token filter configurations
    """
    return {
        "legal_stopwords": {
            "type": "stop",
            "stopwords": ["_english_"] + LEGAL_STOPWORDS,
        },
        "legal_synonyms": {
            "type": "synonym",
            "synonyms": LEGAL_SYNONYMS,
        },
        "shingle_filter": {
            "type": "shingle",
            "min_shingle_size": 2,
            "max_shingle_size": 3,
            "output_unigrams": True,  # Include original tokens
        },
    }


def get_analysis_settings() -> Dict[str, Any]:
    """
    Get complete analysis settings for index creation.

    Returns:
        Analysis settings with all analyzers and filters
    """
    return {
        "analysis": {
            "analyzer": {
                "legal_analyzer": get_legal_analyzer(),
                "shingle_analyzer": get_shingle_analyzer(),
                "citation_analyzer": get_citation_analyzer(),
            },
            "filter": get_token_filters(),
        }
    }
