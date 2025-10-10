"""
Integration example showing how to use the chunking pipeline
with the existing document processing workflow.

This module demonstrates how to integrate the RAGFlow-style chunking
into the Celery document processing tasks and save chunks to the database.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk
from app.workers.pipelines import create_pipeline
from app.workers.pipelines.chunking import DocumentChunk


def process_document_with_chunking(
    document: Document,
    document_text: str,
    db: Session,
    template: Optional[str] = None,
    chunk_sizes: List[int] = None,
    overlap: int = 50
) -> int:
    """
    Process a document using the RAGFlow-style chunking pipeline
    and save chunks to the database.

    Args:
        document: Document model instance
        document_text: Extracted text from the document
        db: Database session
        template: Optional template override (auto-detect if None)
        chunk_sizes: List of chunk sizes in tokens (default: [512, 256, 128])
        overlap: Number of tokens to overlap between chunks

    Returns:
        Number of chunks created

    Example:
        >>> db = SessionLocal()
        >>> document = db.query(Document).filter(Document.id == 1).first()
        >>> text = extract_text_from_file(document.file_path)
        >>> chunk_count = process_document_with_chunking(document, text, db)
        >>> print(f"Created {chunk_count} chunks")
    """
    # Create processing pipeline
    pipeline = create_pipeline(
        chunk_sizes=chunk_sizes,
        overlap=overlap
    )

    # Process the document
    result = pipeline.process(
        document_text=document_text,
        document_id=document.id,
        template=template,
        preserve_structure=True
    )

    # Update document metadata with extracted information
    if document.meta_data is None:
        document.meta_data = {}

    # Merge extracted metadata
    document.meta_data.update({
        "document_type": result.metadata.document_type.value,
        "case_number": result.metadata.case_number,
        "parties": result.metadata.parties,
        "court": result.metadata.court,
        "judge": result.metadata.judge,
        "date_filed": result.metadata.date_filed.isoformat() if result.metadata.date_filed else None,
        "contract_parties": result.metadata.contract_parties,
        "effective_date": result.metadata.effective_date.isoformat() if result.metadata.effective_date else None,
        "statute_citation": result.metadata.statute_citation,
        "chunk_count": result.chunk_count,
        "processing_time": result.processing_time,
    })

    # Delete existing chunks if re-processing
    db.query(Chunk).filter(Chunk.document_id == document.id).delete()

    # Create chunk records in database
    created_chunks = []
    for doc_chunk in result.chunks:
        chunk = create_chunk_from_document_chunk(
            document_id=document.id,
            doc_chunk=doc_chunk
        )
        created_chunks.append(chunk)

    # Add all chunks to database
    db.bulk_save_objects(created_chunks)
    db.commit()

    return len(created_chunks)


def create_chunk_from_document_chunk(
    document_id: int,
    doc_chunk: DocumentChunk
) -> Chunk:
    """
    Convert a DocumentChunk to a database Chunk model.

    Args:
        document_id: ID of the parent document
        doc_chunk: DocumentChunk from the processing pipeline

    Returns:
        Chunk model instance
    """
    metadata = doc_chunk.metadata

    # Determine page number if available
    page_number = metadata.page_number

    # Create chunk metadata for storage
    chunk_metadata = {
        "token_count": metadata.token_count,
        "section_title": metadata.section_title,
        "citations": metadata.citations,
        "section_type": metadata.custom_fields.get("section_type"),
        "is_split": metadata.custom_fields.get("is_split", False),
    }

    return Chunk(
        document_id=document_id,
        text=doc_chunk.text,
        chunk_type=metadata.chunk_type,  # e.g., "512token", "256token", "128token"
        position=metadata.position,
        page_number=page_number,
        meta_data=chunk_metadata
    )


# Example usage in a Celery task
def example_celery_task_integration():
    """
    Example of how to integrate chunking into a Celery task.

    This would replace the placeholder in app/workers/tasks/document_processing.py
    """
    example_code = '''
@celery_app.task(name="process_uploaded_document", bind=True)
def process_uploaded_document(self, document_id: int) -> Dict[str, Any]:
    """
    Process an uploaded document - extract text, entities, and create embeddings.
    """
    db = SessionLocal()
    try:
        # Get document from database
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Document {document_id} not found")
            return {"status": "failed", "error": "Document not found"}

        # Update status to PROCESSING
        document.status = DocumentStatus.PROCESSING
        db.commit()

        logger.info(f"Processing document {document_id}: {document.filename}")

        # 1. Download document from MinIO
        storage_service = StorageService()
        file_data = storage_service.download_file(document.file_path)

        # 2. Extract text using appropriate parser
        # (Use existing DoclingParser or other parsers)
        text = extract_text_from_file(file_data, document.mime_type)

        # 3. Chunk text using RAGFlow-style pipeline
        from app.workers.pipelines.integration_example import process_document_with_chunking

        chunk_count = process_document_with_chunking(
            document=document,
            document_text=text,
            db=db,
            template=None,  # Auto-detect
            chunk_sizes=[512, 256, 128],
            overlap=50
        )

        logger.info(f"Created {chunk_count} chunks for document {document_id}")

        # 4. Extract entities using NLP (if needed)
        # entities = extract_entities(text)

        # 5. Generate embeddings and store in Qdrant
        # from app.workers.pipelines import EmbeddingPipeline
        # embedding_pipeline = EmbeddingPipeline()
        # for chunk in document.chunks:
        #     embedding = embedding_pipeline.encode(chunk.text)
        #     # Store in Qdrant

        # Mark as completed
        document.status = DocumentStatus.COMPLETED
        db.commit()

        logger.info(f"Document {document_id} processed successfully")

        return {
            "status": "completed",
            "document_id": document_id,
            "chunk_count": chunk_count,
            "task_id": self.request.id,
        }

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")

        # Update document status to FAILED
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentStatus.FAILED
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update document status: {str(db_error)}")

        return {
            "status": "failed",
            "error": str(e),
            "document_id": document_id,
        }
    finally:
        db.close()
'''
    return example_code


if __name__ == "__main__":
    print("Integration Example for RAGFlow-style Chunking")
    print("=" * 80)
    print()
    print("This module shows how to integrate the chunking pipeline with")
    print("the existing document processing workflow.")
    print()
    print("Key Functions:")
    print("  - process_document_with_chunking(): Process and save chunks")
    print("  - create_chunk_from_document_chunk(): Convert to DB model")
    print()
    print("Example Celery Task Integration:")
    print("-" * 80)
    print(example_celery_task_integration())
