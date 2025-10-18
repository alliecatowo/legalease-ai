"""Document service for managing document operations."""

import io
import logging
import uuid
from datetime import datetime
from typing import List, Optional, BinaryIO
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from minio.error import S3Error

from app.models.document import Document, DocumentStatus
from app.models.case import Case
from app.core.minio_client import minio_client
from app.workers.tasks.document_processing import process_uploaded_document

logger = logging.getLogger(__name__)


class DocumentService:
    """Service class for document operations."""

    @staticmethod
    def _generate_object_name(case_gid: str, document_gid: str, filename: str) -> str:
        """
        Generate a unique object name for MinIO storage.

        Args:
            case_gid: GID of the case
            document_gid: GID of the document
            filename: Original filename

        Returns:
            str: Unique object name in format: cases/{case_gid}/{doc_gid}_{filename}
        """
        # Sanitize filename to prevent path traversal
        safe_filename = filename.replace("/", "_").replace("\\", "_")
        return f"cases/{case_gid}/{document_gid}_{safe_filename}"

    @staticmethod
    async def upload_documents(
        case_gid: str,
        files: List[UploadFile],
        db: Session,
    ) -> List[Document]:
        """
        Upload multiple documents for a case.

        This method:
        1. Validates the case exists
        2. Uploads files to MinIO
        3. Creates database records
        4. Enqueues processing tasks

        Args:
            case_gid: GID of the case
            files: List of uploaded files
            db: Database session

        Returns:
            List[Document]: List of created document records

        Raises:
            HTTPException: If case not found or upload fails
        """
        # Validate case exists
        case = db.query(Case).filter(Case.gid == case_gid).first()
        if not case:
            logger.error(f"Case {case_gid} not found")
            raise HTTPException(status_code=404, detail=f"Case {case_gid} not found")

        uploaded_documents = []

        for file in files:
            try:
                # Read file content
                content = await file.read()
                file_size = len(content)

                # Create database record first to get GID
                document = Document(
                    case_id=case.id,
                    filename=file.filename,
                    file_path="",  # Will be set after upload
                    mime_type=file.content_type,
                    size=file_size,
                    status=DocumentStatus.PENDING,
                    uploaded_at=datetime.utcnow(),
                )
                db.add(document)
                db.flush()  # Get the document ID and GID

                # Generate unique object name using GIDs
                object_name = DocumentService._generate_object_name(case.gid, document.gid, file.filename)

                # Upload to MinIO
                logger.info(f"Uploading {file.filename} to MinIO as {object_name}")
                minio_client.upload_file(
                    file_data=io.BytesIO(content),
                    object_name=object_name,
                    content_type=file.content_type,
                    length=file_size,
                )

                # Update file path
                document.file_path = object_name
                db.flush()

                logger.info(f"Created document record {document.gid} for {file.filename}")

                # Enqueue processing task only for document files (not audio/video)
                # Audio/video files should be processed by transcription tasks instead
                if file.content_type and not (
                    file.content_type.startswith("audio/") or
                    file.content_type.startswith("video/")
                ):
                    process_uploaded_document.delay(document.id)
                    logger.info(f"Enqueued document processing task for {document.gid}")
                else:
                    logger.info(f"Skipping document processing for audio/video file {document.gid}")

                uploaded_documents.append(document)

            except S3Error as e:
                logger.error(f"MinIO error uploading {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload {file.filename} to storage: {str(e)}",
                )
            except Exception as e:
                logger.error(f"Error uploading {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload {file.filename}: {str(e)}",
                )

        # Commit all documents
        db.commit()

        # Refresh to get relationships
        for doc in uploaded_documents:
            db.refresh(doc)

        logger.info(f"Successfully uploaded {len(uploaded_documents)} documents for case {case_gid}")
        return uploaded_documents

    @staticmethod
    def get_document(document_gid: str, db: Session) -> Document:
        """
        Get a document by GID.

        Args:
            document_gid: GID of the document
            db: Database session

        Returns:
            Document: Document record

        Raises:
            HTTPException: If document not found
        """
        document = db.query(Document).filter(Document.gid == document_gid).first()
        if not document:
            logger.error(f"Document {document_gid} not found")
            raise HTTPException(status_code=404, detail=f"Document {document_gid} not found")

        return document

    @staticmethod
    def list_case_documents(case_gid: str, db: Session) -> List[Document]:
        """
        List all documents for a case.

        Args:
            case_gid: GID of the case
            db: Database session

        Returns:
            List[Document]: List of documents

        Raises:
            HTTPException: If case not found
        """
        # Validate case exists
        case = db.query(Case).filter(Case.gid == case_gid).first()
        if not case:
            logger.error(f"Case {case_gid} not found")
            raise HTTPException(status_code=404, detail=f"Case {case_gid} not found")

        documents = db.query(Document).filter(Document.case_id == case.id).all()
        logger.info(f"Found {len(documents)} documents for case {case_gid}")

        return documents

    @staticmethod
    def list_all_documents(
        page: int = 1,
        page_size: int = 50,
        case_gid: Optional[str] = None,
        db: Session = None
    ) -> tuple[List[dict], int]:
        """
        List all documents across all cases with pagination.

        Uses an efficient JOIN query to include case information without N+1 queries.

        Args:
            page: Page number (starting from 1)
            page_size: Number of items per page (max 100)
            case_gid: Optional case GID to filter documents
            db: Database session

        Returns:
            tuple: (list of document dicts with case info, total count)
        """
        # Build base query with join to Case table to get case name, number, and gid
        query = db.query(
            Document,
            Case.name.label('case_name'),
            Case.case_number.label('case_number'),
            Case.gid.label('case_gid')
        ).join(
            Case, Document.case_id == Case.id
        )

        # Apply case filter if provided
        if case_gid is not None:
            query = query.filter(Case.gid == case_gid)

        # Get total count before pagination
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        results = query.order_by(Document.uploaded_at.desc()).offset(offset).limit(page_size).all()

        logger.info(f"Found {total} total documents, returning {len(results)} for page {page}")

        # Convert to dicts with case information
        document_dicts = []
        for doc, case_name, case_number, case_gid in results:
            doc_dict = {
                'id': doc.id,
                'gid': doc.gid,
                'case_id': doc.case_id,
                'case_gid': case_gid,
                'case_name': case_name,
                'case_number': case_number,
                'filename': doc.filename,
                'file_path': doc.file_path,
                'mime_type': doc.mime_type,
                'size': doc.size,
                'status': doc.status,
                'meta_data': doc.meta_data,
                'uploaded_at': doc.uploaded_at,
            }
            document_dicts.append(doc_dict)

        return document_dicts, total

    @staticmethod
    def download_document(document_gid: str, db: Session) -> tuple[bytes, str, str]:
        """
        Download a document from MinIO.

        Args:
            document_gid: GID of the document
            db: Database session

        Returns:
            tuple: (file_content, filename, content_type)

        Raises:
            HTTPException: If document not found or download fails
        """
        # Get document from database
        document = DocumentService.get_document(document_gid, db)

        try:
            # Download from MinIO
            logger.info(f"Downloading document {document_gid} from MinIO: {document.file_path}")
            content = minio_client.download_file(document.file_path)

            return content, document.filename, document.mime_type or "application/octet-stream"

        except S3Error as e:
            logger.error(f"MinIO error downloading document {document_gid}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download document from storage: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Error downloading document {document_gid}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download document: {str(e)}",
            )

    @staticmethod
    def get_document_content(document_gid: str, db: Session) -> dict:
        """
        Get parsed document content including text, pages, and bounding boxes.

        Args:
            document_gid: GID of the document
            db: Database session

        Returns:
            dict: Document content with structure:
                {
                    "text": str,  # Full document text
                    "pages": List[dict],  # Page-level content with items and bboxes
                    "metadata": dict,  # Document metadata
                }

        Raises:
            HTTPException: If document not found or content not available
        """
        from app.models.chunk import Chunk

        # Get document from database
        document = DocumentService.get_document(document_gid, db)

        # Check if document has been processed
        if document.status != DocumentStatus.COMPLETED:
            logger.warning(f"Document {document_gid} not yet processed (status: {document.status})")
            raise HTTPException(
                status_code=400,
                detail=f"Document is not processed yet. Current status: {document.status.value}",
            )

        # Get all chunks for this document ordered by page/position
        chunks = (
            db.query(Chunk)
            .filter(Chunk.document_id == document.id)
            .order_by(Chunk.page_number, Chunk.position)
            .all()
        )

        if not chunks:
            logger.warning(f"No chunks found for document {document_gid}")
            # Return basic structure with document metadata
            return {
                "text": "",
                "pages": [],
                "metadata": document.meta_data or {},
                "filename": document.filename,
                "document_gid": document_gid,
                "total_chunks": 0,
                "total_pages": 0,
            }

        # Group chunks by page
        pages_dict = {}
        full_text = []

        for chunk in chunks:
            page_num = chunk.page_number or 1

            if page_num not in pages_dict:
                pages_dict[page_num] = {
                    "page_number": page_num,
                    "items": [],
                    "text": [],
                }

            # Extract bbox data from chunk metadata
            chunk_meta = chunk.meta_data or {}
            item_data = {
                "text": chunk.text,
                "type": chunk.chunk_type,
                "chunk_id": chunk.id,
                "bboxes": [],
            }

            # Add bboxes if available in metadata (handle nested)
            bbs = []
            if isinstance(chunk_meta, dict):
                if "bboxes" in chunk_meta and chunk_meta["bboxes"]:
                    bbs = chunk_meta["bboxes"] or []
                elif "additional_metadata" in chunk_meta and isinstance(chunk_meta["additional_metadata"], dict):
                    bbs = chunk_meta["additional_metadata"].get("bboxes", []) or []
            item_data["bboxes"] = bbs

            pages_dict[page_num]["items"].append(item_data)
            pages_dict[page_num]["text"].append(chunk.text)
            full_text.append(chunk.text)

        # Build ordered pages list
        pages = []
        for page_num in sorted(pages_dict.keys()):
            page_data = pages_dict[page_num]
            page_data["text"] = "\n".join(page_data["text"])
            # Debug: count item bboxes per page
            try:
                bbox_counts = sum(len(item.get("bboxes", []) or []) for item in page_data.get("items", []))
                logger.info(f"Document {document_gid} page {page_num}: {bbox_counts} item bboxes")
            except Exception as _:
                pass
            pages.append(page_data)

        result = {
            "text": "\n\n".join(full_text),
            "pages": pages,
            "metadata": document.meta_data or {},
            "filename": document.filename,
            "document_gid": document_gid,
            "total_chunks": len(chunks),
            "total_pages": len(pages),
        }

        logger.info(
            f"Retrieved content for document {document_gid}: "
            f"{len(pages)} pages, {len(chunks)} chunks"
        )

        return result

    @staticmethod
    def delete_document(document_gid: str, db: Session) -> Document:
        """
        Delete a document (from both database and MinIO).

        Args:
            document_gid: GID of the document
            db: Database session

        Returns:
            Document: Deleted document record

        Raises:
            HTTPException: If document not found or deletion fails
        """
        # Get document from database
        document = DocumentService.get_document(document_gid, db)

        try:
            # Delete from MinIO
            logger.info(f"Deleting document {document_gid} from MinIO: {document.file_path}")
            minio_client.delete_file(document.file_path)

            # Delete from database (cascade will handle related records)
            db.delete(document)
            db.commit()

            logger.info(f"Successfully deleted document {document_gid}")
            return document

        except S3Error as e:
            logger.error(f"MinIO error deleting document {document_gid}: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete document from storage: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Error deleting document {document_gid}: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete document: {str(e)}",
            )
