"""
Document Processing Tasks

Celery tasks for document generation, processing, and analysis.
These are stub implementations - full functionality will be implemented in Phase 3.
"""
from typing import Dict, Any
import logging

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus

logger = logging.getLogger(__name__)


@celery_app.task(name="process_document", bind=True)
def process_document(
    self,
    document_id: str,
    case_id: str,
    template: str
) -> Dict[str, Any]:
    """
    Process a document for a case using a specified template.

    This is a placeholder task that will be fully implemented in Phase 3.
    It will handle document parsing, entity extraction, and indexing.

    Args:
        document_id: Unique identifier for the document
        case_id: Unique identifier for the case
        template: Template type to use for processing

    Returns:
        Dict containing processing status and document_id
    """
    # Placeholder - will implement in Phase 3
    # Future implementation will:
    # 1. Fetch document from MinIO
    # 2. Extract text and metadata
    # 3. Run NLP entity extraction
    # 4. Index document chunks in Qdrant
    # 5. Update database status

    return {
        "status": "pending",
        "document_id": document_id,
        "case_id": case_id,
        "template": template,
        "task_id": self.request.id,
    }


@celery_app.task(name="generate_document", bind=True)
def generate_document(
    self,
    case_id: str,
    template_name: str,
    context_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a document from a template with provided context.

    This is a placeholder task that will be fully implemented in Phase 3.
    It will handle template rendering and document generation.

    Args:
        case_id: Unique identifier for the case
        template_name: Name of the template to use
        context_data: Dictionary of data to populate the template

    Returns:
        Dict containing generation status and document details
    """
    # Placeholder - will implement in Phase 3
    # Future implementation will:
    # 1. Load template from storage
    # 2. Render template with context data
    # 3. Generate DOCX file
    # 4. Upload to MinIO
    # 5. Create document record in database

    return {
        "status": "pending",
        "case_id": case_id,
        "template_name": template_name,
        "task_id": self.request.id,
    }


@celery_app.task(name="process_uploaded_document", bind=True)
def process_uploaded_document(self, document_id: int) -> Dict[str, Any]:
    """
    Process an uploaded document - extract text, entities, and create embeddings.

    This task is triggered after a document is uploaded to MinIO and the database record is created.

    Full pipeline:
    1. Download document from MinIO
    2. Parse document (extract text with Docling)
    3. Chunk text (hierarchical: summary, section, microblock)
    4. Generate embeddings (dense + sparse)
    5. Index to Qdrant (vector storage)
    6. Create chunk records in database
    7. Update document status

    Args:
        document_id: ID of the document to process

    Returns:
        Dict containing processing status and details
    """
    from app.core.minio_client import minio_client
    from app.models.chunk import Chunk
    from app.workers.pipelines.document_pipeline import DocumentProcessor

    db = SessionLocal()
    try:
        # Get document from database
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Document {document_id} not found")
            return {
                "status": "failed",
                "error": "Document not found",
                "document_id": document_id,
            }

        # Update status to PROCESSING
        document.status = DocumentStatus.PROCESSING
        db.commit()

        logger.info(f"Processing document {document_id}: {document.filename}")

        # Step 1: Download document from MinIO
        logger.info(f"Downloading document from MinIO: {document.file_path}")
        try:
            file_content = minio_client.download_file(document.file_path)
            logger.info(f"Downloaded {len(file_content)} bytes from MinIO")
        except Exception as e:
            logger.error(f"Failed to download document from MinIO: {e}")
            raise Exception(f"MinIO download failed: {str(e)}")

        # Step 2-5: Process document through pipeline
        logger.info("Starting document processing pipeline")
        processor = DocumentProcessor(
            use_ocr=True,  # Enable OCR for scanned documents
            use_bm25=True,  # Enable BM25 sparse vectors
            embedding_model="BAAI/bge-small-en-v1.5",  # 384 dims (matches Qdrant collection)
        )

        result = processor.process(
            file_content=file_content,
            filename=document.filename,
            document_id=document.id,
            case_id=document.case_id,
            mime_type=document.mime_type,
        )

        if not result.success:
            logger.error(f"Document processing failed: {result.message}")
            raise Exception(f"Processing failed at stage {result.stage}: {result.error}")

        logger.info(f"Document processing successful: {result.message}")

        # Step 6: Generate page images (for PDFs only)
        pages_count = result.data.get("pages_count", 0)
        if document.mime_type == "application/pdf" and pages_count > 0:
            logger.info(f"Generating page images for {pages_count} pages")
            try:
                from app.services.page_image_service import PageImageService

                image_paths = PageImageService.generate_page_images(
                    pdf_content=file_content,
                    document_id=document.id,
                    case_id=document.case_id,
                )
                logger.info(f"Generated {len(image_paths)} page images")

            except Exception as e:
                logger.warning(f"Failed to generate page images: {e}")
                # Continue processing even if image generation fails

        # Step 7: Create chunk records in database
        logger.info("Creating chunk records in database")
        chunks_data = result.data
        chunks_count = chunks_data.get("chunks_count", 0)

        # Fetch chunks from Qdrant and save to PostgreSQL for document viewer
        from app.core.qdrant import get_qdrant_client
        from app.core.config import settings

        try:
            qdrant_client = get_qdrant_client()
            collection_name = settings.QDRANT_COLLECTION

            # Scroll through all points for this document
            scroll_result = qdrant_client.scroll(
                collection_name=collection_name,
                scroll_filter={
                    "must": [
                        {"key": "document_id", "match": {"value": document.id}}
                    ]
                },
                limit=1000,
                with_payload=True,
                with_vectors=False,
            )

            points = scroll_result[0]

            for point in points:
                payload = point.payload
                chunk = Chunk(
                    document_id=document.id,
                    text=payload.get("text", ""),
                    chunk_type=payload.get("chunk_type", "section"),
                    position=payload.get("position", 0),
                    page_number=payload.get("page_number"),
                    meta_data={
                        "bbox": payload.get("bbox"),
                        **payload.get("metadata", {}),
                    },
                )
                db.add(chunk)

            db.flush()
            logger.info(f"Saved {len(points)} chunks to database")

        except Exception as e:
            logger.warning(f"Failed to save chunks to database: {e}")
            # Continue processing even if chunk saving fails

        # Step 8: Update document status to COMPLETED (successful completion)
        document.status = DocumentStatus.COMPLETED
        document.meta_data = {
            "chunks_count": chunks_count,
            "text_length": chunks_data.get("text_length", 0),
            "pages_count": pages_count,
            "page_count": pages_count,  # Also use 'page_count' for compatibility
            "processing_stage": result.stage,
            "processed_at": str(db.query(Document).filter(Document.id == document_id).first().uploaded_at),
        }
        db.commit()

        logger.info(f"Document {document_id} processed successfully: {chunks_count} chunks created")

        return {
            "status": "completed",
            "document_id": document_id,
            "filename": document.filename,
            "chunks_count": chunks_count,
            "text_length": chunks_data.get("text_length", 0),
            "pages_count": chunks_data.get("pages_count", 0),
            "task_id": self.request.id,
        }

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}", exc_info=True)

        # Update document status to FAILED
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentStatus.FAILED
                document.meta_data = {
                    "error": str(e),
                    "error_stage": "processing",
                }
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update document status: {str(db_error)}")

        return {
            "status": "failed",
            "error": str(e),
            "document_id": document_id,
            "task_id": self.request.id,
        }
    finally:
        db.close()
