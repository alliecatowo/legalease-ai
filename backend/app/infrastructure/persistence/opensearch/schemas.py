"""
Index schema definitions for OpenSearch.

This module defines mappings and settings for each index type:
- documents: Legal document chunks
- transcripts: Audio/video transcript segments
- communications: Digital communications
- findings: Research findings
"""

from typing import Dict, Any

from app.core.config import settings
from app.infrastructure.persistence.opensearch.analyzers import get_analysis_settings


def get_index_name(base_name: str) -> str:
    """
    Get fully qualified index name with prefix.

    Args:
        base_name: Base name of the index (e.g., "documents")

    Returns:
        Full index name with prefix (e.g., "legalease-documents")
    """
    return f"{settings.OPENSEARCH_INDEX_PREFIX}-{base_name}"


def get_documents_index_config() -> Dict[str, Any]:
    """
    Get configuration for documents index.

    This index stores document chunks with:
    - Full-text search on text content
    - Filtering by case, document, chunk type
    - Citation analysis
    - Page and position tracking

    Returns:
        Index configuration with mappings and settings
    """
    return {
        "mappings": {
            "properties": {
                "id": {
                    "type": "keyword",
                    "doc_values": True,
                },
                "case_id": {
                    "type": "keyword",
                    "doc_values": True,
                },
                "document_id": {
                    "type": "keyword",
                    "doc_values": True,
                },
                "chunk_type": {
                    "type": "keyword",
                    "doc_values": True,
                },
                "text": {
                    "type": "text",
                    "analyzer": "legal_analyzer",
                    "search_analyzer": "legal_analyzer",
                    "fields": {
                        "exact": {
                            "type": "keyword",
                            "ignore_above": 256,
                        },
                        "shingles": {
                            "type": "text",
                            "analyzer": "shingle_analyzer",
                        },
                        "citation": {
                            "type": "text",
                            "analyzer": "citation_analyzer",
                        },
                    }
                },
                "page_number": {
                    "type": "integer",
                },
                "position": {
                    "type": "integer",
                },
                "metadata": {
                    "type": "object",
                    "enabled": False,  # Don't index, just store
                },
                "created_at": {
                    "type": "date",
                },
            }
        },
        "settings": {
            "number_of_shards": 2,
            "number_of_replicas": 1,
            "refresh_interval": "1s",
            **get_analysis_settings(),
        }
    }


def get_transcripts_index_config() -> Dict[str, Any]:
    """
    Get configuration for transcripts index.

    This index stores transcript segments with:
    - Full-text search on speech content
    - Speaker identification
    - Timecode-based filtering
    - Exact quote matching

    Returns:
        Index configuration with mappings and settings
    """
    return {
        "mappings": {
            "properties": {
                "id": {
                    "type": "keyword",
                    "doc_values": True,
                },
                "case_id": {
                    "type": "keyword",
                    "doc_values": True,
                },
                "transcript_id": {
                    "type": "keyword",
                    "doc_values": True,
                },
                "segment_id": {
                    "type": "keyword",
                    "doc_values": True,
                },
                "text": {
                    "type": "text",
                    "analyzer": "legal_analyzer",
                    "search_analyzer": "legal_analyzer",
                    "fields": {
                        "exact": {
                            "type": "keyword",
                            "ignore_above": 512,
                        },
                        "shingles": {
                            "type": "text",
                            "analyzer": "shingle_analyzer",
                        },
                    }
                },
                "speaker": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                        }
                    }
                },
                "speaker_id": {
                    "type": "keyword",
                },
                "timecode_start": {
                    "type": "float",
                },
                "timecode_end": {
                    "type": "float",
                },
                "duration": {
                    "type": "float",
                },
                "confidence": {
                    "type": "float",
                },
                "position": {
                    "type": "integer",
                },
                "metadata": {
                    "type": "object",
                    "enabled": False,
                },
                "created_at": {
                    "type": "date",
                },
            }
        },
        "settings": {
            "number_of_shards": 2,
            "number_of_replicas": 1,
            "refresh_interval": "1s",
            **get_analysis_settings(),
        }
    }


def get_communications_index_config() -> Dict[str, Any]:
    """
    Get configuration for communications index.

    This index stores digital communications with:
    - Full-text search on message body
    - Thread grouping
    - Participant filtering
    - Temporal queries
    - Platform identification

    Returns:
        Index configuration with mappings and settings
    """
    return {
        "mappings": {
            "properties": {
                "id": {
                    "type": "keyword",
                    "doc_values": True,
                },
                "case_id": {
                    "type": "keyword",
                    "doc_values": True,
                },
                "thread_id": {
                    "type": "keyword",
                    "doc_values": True,
                },
                "body": {
                    "type": "text",
                    "analyzer": "standard",  # Use standard for casual text
                    "fields": {
                        "exact": {
                            "type": "keyword",
                            "ignore_above": 512,
                        },
                    }
                },
                "sender": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                        }
                    }
                },
                "sender_identifier": {
                    "type": "keyword",
                },
                "participants": {
                    "type": "keyword",
                },
                "participant_names": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                        }
                    }
                },
                "timestamp": {
                    "type": "date",
                },
                "platform": {
                    "type": "keyword",
                },
                "communication_type": {
                    "type": "keyword",
                },
                "device_id": {
                    "type": "keyword",
                },
                "has_attachments": {
                    "type": "boolean",
                },
                "attachment_count": {
                    "type": "integer",
                },
                "metadata": {
                    "type": "object",
                    "enabled": False,
                },
                "created_at": {
                    "type": "date",
                },
            }
        },
        "settings": {
            "number_of_shards": 2,
            "number_of_replicas": 1,
            "refresh_interval": "1s",
            **get_analysis_settings(),
        }
    }


def get_findings_index_config() -> Dict[str, Any]:
    """
    Get configuration for findings index.

    This index stores research findings with:
    - Full-text search on finding text
    - Filtering by type, confidence, relevance
    - Tag-based organization
    - Entity and citation linking

    Returns:
        Index configuration with mappings and settings
    """
    return {
        "mappings": {
            "properties": {
                "id": {
                    "type": "keyword",
                    "doc_values": True,
                },
                "research_run_id": {
                    "type": "keyword",
                    "doc_values": True,
                },
                "finding_type": {
                    "type": "keyword",
                    "doc_values": True,
                },
                "text": {
                    "type": "text",
                    "analyzer": "legal_analyzer",
                    "search_analyzer": "legal_analyzer",
                    "fields": {
                        "exact": {
                            "type": "keyword",
                            "ignore_above": 512,
                        },
                    }
                },
                "entities": {
                    "type": "keyword",
                },
                "citations": {
                    "type": "keyword",
                },
                "confidence": {
                    "type": "float",
                },
                "relevance": {
                    "type": "float",
                },
                "tags": {
                    "type": "keyword",
                },
                "metadata": {
                    "type": "object",
                    "enabled": False,
                },
                "created_at": {
                    "type": "date",
                },
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "refresh_interval": "1s",
            **get_analysis_settings(),
        }
    }


# Index name constants
DOCUMENTS_INDEX = get_index_name("documents")
TRANSCRIPTS_INDEX = get_index_name("transcripts")
COMMUNICATIONS_INDEX = get_index_name("communications")
FINDINGS_INDEX = get_index_name("findings")


# Index configurations
INDEX_CONFIGS = {
    DOCUMENTS_INDEX: get_documents_index_config(),
    TRANSCRIPTS_INDEX: get_transcripts_index_config(),
    COMMUNICATIONS_INDEX: get_communications_index_config(),
    FINDINGS_INDEX: get_findings_index_config(),
}
