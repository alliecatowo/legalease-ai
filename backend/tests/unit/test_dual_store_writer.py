"""Unit tests for the DualStoreWriter component."""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.infrastructure.ai.haystack.stores.dual_store_writer import DualStoreWriter
from app.domain.evidence.value_objects.chunk import Chunk, ChunkType


def _make_chunks(count: int = 2):
    """Helper to create sample chunk objects."""
    return [
        Chunk(
            text=f"Chunk {i}",
            chunk_type=ChunkType.PARAGRAPH,
            position=i,
            metadata={"page": i + 1},
        )
        for i in range(count)
    ]


@pytest.mark.asyncio
async def test_dual_store_writer_succeeds_for_documents():
    """DualStoreWriter should write to both stores and report success."""
    qdrant_repo = AsyncMock()
    qdrant_repo.index_document = AsyncMock(return_value=True)

    opensearch_repo = AsyncMock()
    opensearch_repo.index_document_chunks = AsyncMock(return_value=2)

    writer = DualStoreWriter(
        evidence_type="document",
        qdrant_document_repo=qdrant_repo,
        opensearch_document_repo=opensearch_repo,
    )

    case_id = uuid4()
    document_id = uuid4()
    chunks = _make_chunks()
    embeddings = {
        "summary": [[0.1, 0.2, 0.3] for _ in chunks],
        "section": [[0.1, 0.2, 0.3] for _ in chunks],
        "microblock": [[0.1, 0.2, 0.3] for _ in chunks],
    }

    result = await writer.run(
        documents=[],
        case_id=case_id,
        document_id=document_id,
        chunks=chunks,
        embeddings=embeddings,
    )

    assert result["success"] is True
    assert result["documents_written"] == len(chunks)
    qdrant_repo.index_document.assert_awaited_once()
    opensearch_repo.index_document_chunks.assert_awaited_once()


@pytest.mark.asyncio
async def test_dual_store_writer_rolls_back_on_opensearch_failure():
    """If OpenSearch indexing fails, the Qdrant write should be rolled back."""
    qdrant_repo = AsyncMock()
    qdrant_repo.index_document = AsyncMock(return_value=True)
    qdrant_repo.delete_document = AsyncMock()

    opensearch_repo = AsyncMock()
    opensearch_repo.index_document_chunks = AsyncMock(side_effect=RuntimeError("boom"))

    writer = DualStoreWriter(
        evidence_type="document",
        qdrant_document_repo=qdrant_repo,
        opensearch_document_repo=opensearch_repo,
    )

    case_id = uuid4()
    document_id = uuid4()
    chunks = _make_chunks()
    embeddings = {
        "summary": [[0.1, 0.2] for _ in chunks],
        "section": [[0.1, 0.2] for _ in chunks],
        "microblock": [[0.1, 0.2] for _ in chunks],
    }

    result = await writer.run(
        documents=[],
        case_id=case_id,
        document_id=document_id,
        chunks=chunks,
        embeddings=embeddings,
    )

    assert result["success"] is False
    assert result["documents_written"] == 0
    assert result["errors"], "Expected error messages when OpenSearch fails"
    qdrant_repo.delete_document.assert_awaited_once_with(document_id)
