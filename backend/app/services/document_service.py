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
    def _generate_object_name(case_id: int, filename: str) -> str:
        """
        Generate a unique object name for MinIO storage.

        Args:
            case_id: ID of the case
            filename: Original filename

        Returns:
            str: Unique object name in format: cases/{case_id}/{uuid}_{filename}
        """
        unique_id = uuid.uuid4().hex[:8]
        # Sanitize filename to prevent path traversal
        safe_filename = filename.replace("/", "_").replace("\\", "_")
        return f"cases/{case_id}/{unique_id}_{safe_filename}"

    @staticmethod
    async def upload_documents(
        case_id: int,
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
            case_id: ID of the case
            files: List of uploaded files
            db: Database session

        Returns:
            List[Document]: List of created document records

        Raises:
            HTTPException: If case not found or upload fails
        """
        # Validate case exists
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            logger.error(f"Case {case_id} not found")
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        uploaded_documents = []

        for file in files:
            try:
                # Read file content
                content = await file.read()
                file_size = len(content)

                # Generate unique object name
                object_name = DocumentService._generate_object_name(case_id, file.filename)

                # Upload to MinIO
                logger.info(f"Uploading {file.filename} to MinIO as {object_name}")
                minio_client.upload_file(
                    file_data=io.BytesIO(content),
                    object_name=object_name,
                    content_type=file.content_type,
                    length=file_size,
                )

                # Create database record
                document = Document(
                    case_id=case_id,
                    filename=file.filename,
                    file_path=object_name,
                    mime_type=file.content_type,
                    size=file_size,
                    status=DocumentStatus.PENDING,
                    uploaded_at=datetime.utcnow(),
                )
                db.add(document)
                db.flush()  # Get the document ID

                logger.info(f"Created document record {document.id} for {file.filename}")

                # Enqueue processing task
                process_uploaded_document.delay(document.id)
                logger.info(f"Enqueued processing task for document {document.id}")

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

        logger.info(f"Successfully uploaded {len(uploaded_documents)} documents for case {case_id}")
        return uploaded_documents

    @staticmethod
    def get_document(document_id: int, db: Session) -> Document:
        """
        Get a document by ID.

        Args:
            document_id: ID of the document
            db: Database session

        Returns:
            Document: Document record

        Raises:
            HTTPException: If document not found
        """
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Document {document_id} not found")
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

        return document

    @staticmethod
    def list_case_documents(case_id: int, db: Session) -> List[Document]:
        """
        List all documents for a case.

        Args:
            case_id: ID of the case
            db: Database session

        Returns:
            List[Document]: List of documents

        Raises:
            HTTPException: If case not found
        """
        # Validate case exists
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            logger.error(f"Case {case_id} not found")
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        documents = db.query(Document).filter(Document.case_id == case_id).all()
        logger.info(f"Found {len(documents)} documents for case {case_id}")

        return documents

    @staticmethod
    def download_document(document_id: int, db: Session) -> tuple[bytes, str, str]:
        """
        Download a document from MinIO.

        Args:
            document_id: ID of the document
            db: Database session

        Returns:
            tuple: (file_content, filename, content_type)

        Raises:
            HTTPException: If document not found or download fails
        """
        # Get document from database
        document = DocumentService.get_document(document_id, db)

        try:
            # Download from MinIO
            logger.info(f"Downloading document {document_id} from MinIO: {document.file_path}")
            content = minio_client.download_file(document.file_path)

            return content, document.filename, document.mime_type or "application/octet-stream"

        except S3Error as e:
            logger.error(f"MinIO error downloading document {document_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download document from storage: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Error downloading document {document_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download document: {str(e)}",
            )

    @staticmethod
    def delete_document(document_id: int, db: Session) -> Document:
        """
        Delete a document (from both database and MinIO).

        Args:
            document_id: ID of the document
            db: Database session

        Returns:
            Document: Deleted document record

        Raises:
            HTTPException: If document not found or deletion fails
        """
        # Get document from database
        document = DocumentService.get_document(document_id, db)

        try:
            # Delete from MinIO
            logger.info(f"Deleting document {document_id} from MinIO: {document.file_path}")
            minio_client.delete_file(document.file_path)

            # Delete from database (cascade will handle related records)
            db.delete(document)
            db.commit()

            logger.info(f"Successfully deleted document {document_id}")
            return document

        except S3Error as e:
            logger.error(f"MinIO error deleting document {document_id}: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete document from storage: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete document: {str(e)}",
            )
