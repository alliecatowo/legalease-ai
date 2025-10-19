"""
Storage Service for Managing Case Documents in MinIO
"""
from typing import Optional, BinaryIO, Callable
from datetime import timedelta
from io import BytesIO
import logging

from app.core.minio import minio_client

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing document storage in MinIO"""

    def __init__(self):
        """Initialize the storage service with MinIO client"""
        self.client = minio_client

    @staticmethod
    def _get_bucket_name(case_gid: str) -> str:
        """
        Generate bucket name for a case

        Args:
            case_gid: GID of the case

        Returns:
            str: Bucket name in format 'case-{case_gid}'
        """
        # MinIO bucket names must be lowercase, alphanumeric + hyphens
        # GIDs are already in a compatible format (lowercase letters + numbers)
        return f"case-{case_gid}"

    def store_document(
        self,
        case_gid: str,
        file: BinaryIO,
        filename: str,
        file_size: int,
        content_type: str = "application/octet-stream",
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """
        Store a document for a specific case

        Args:
            case_gid: GID of the case
            file: File-like object containing the document data
            filename: Name to store the file as
            file_size: Size of the file in bytes
            content_type: MIME type of the file
            progress_callback: Optional callback function for upload progress

        Returns:
            bool: True if storage successful, False otherwise
        """
        bucket_name = self._get_bucket_name(case_gid)

        try:
            # Ensure the bucket exists
            if not self.client.create_bucket(bucket_name):
                logger.error(f"Failed to create/verify bucket for case {case_gid}")
                return False

            # Upload the file
            success = self.client.upload_file(
                bucket_name=bucket_name,
                object_name=filename,
                file_data=file,
                file_size=file_size,
                content_type=content_type,
                progress_callback=progress_callback,
            )

            if success:
                logger.info(f"Stored document '{filename}' for case {case_gid}")
            else:
                logger.error(f"Failed to store document '{filename}' for case {case_gid}")

            return success

        except Exception as e:
            logger.error(f"Error storing document '{filename}' for case {case_gid}: {e}")
            return False

    def retrieve_document(
        self,
        case_gid: str,
        filename: str,
    ) -> Optional[BytesIO]:
        """
        Retrieve a document from a specific case

        Args:
            case_gid: GID of the case
            filename: Name of the file to retrieve

        Returns:
            BytesIO: File data, or None if not found or error
        """
        bucket_name = self._get_bucket_name(case_gid)

        try:
            file_data = self.client.download_file(
                bucket_name=bucket_name,
                object_name=filename,
            )

            if file_data:
                logger.info(f"Retrieved document '{filename}' from case {case_gid}")
            else:
                logger.warning(f"Document '{filename}' not found for case {case_gid}")

            return file_data

        except Exception as e:
            logger.error(f"Error retrieving document '{filename}' from case {case_gid}: {e}")
            return None

    def delete_document(
        self,
        case_gid: str,
        filename: str,
    ) -> bool:
        """
        Delete a document from a specific case

        Args:
            case_gid: GID of the case
            filename: Name of the file to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        bucket_name = self._get_bucket_name(case_gid)

        try:
            success = self.client.delete_file(
                bucket_name=bucket_name,
                object_name=filename,
            )

            if success:
                logger.info(f"Deleted document '{filename}' from case {case_gid}")
            else:
                logger.error(f"Failed to delete document '{filename}' from case {case_gid}")

            return success

        except Exception as e:
            logger.error(f"Error deleting document '{filename}' from case {case_gid}: {e}")
            return False

    def list_case_files(
        self,
        case_gid: str,
        prefix: Optional[str] = None,
    ) -> list[dict]:
        """
        List all files for a specific case

        Args:
            case_gid: GID of the case
            prefix: Optional prefix to filter files

        Returns:
            list[dict]: List of file metadata dictionaries
        """
        bucket_name = self._get_bucket_name(case_gid)

        try:
            # Check if bucket exists first
            if not self.client.client.bucket_exists(bucket_name):
                logger.info(f"Bucket for case {case_gid} does not exist yet")
                return []

            files = self.client.list_objects(
                bucket_name=bucket_name,
                prefix=prefix,
            )

            logger.info(f"Listed {len(files)} files for case {case_gid}")
            return files

        except Exception as e:
            logger.error(f"Error listing files for case {case_gid}: {e}")
            return []

    def get_temporary_url(
        self,
        case_gid: str,
        filename: str,
        expiry: timedelta = timedelta(hours=1),
    ) -> Optional[str]:
        """
        Generate a temporary presigned URL for accessing a document

        Args:
            case_gid: GID of the case
            filename: Name of the file
            expiry: Duration for which the URL is valid (default: 1 hour)

        Returns:
            str: Presigned URL, or None if error
        """
        bucket_name = self._get_bucket_name(case_gid)

        try:
            url = self.client.get_presigned_url(
                bucket_name=bucket_name,
                object_name=filename,
                expiry=expiry,
            )

            if url:
                logger.info(f"Generated temporary URL for '{filename}' in case {case_gid}")
            else:
                logger.error(f"Failed to generate URL for '{filename}' in case {case_gid}")

            return url

        except Exception as e:
            logger.error(f"Error generating URL for '{filename}' in case {case_gid}: {e}")
            return None

    def delete_case_storage(
        self,
        case_gid: str,
    ) -> bool:
        """
        Delete all documents and the bucket for a case

        Args:
            case_gid: GID of the case

        Returns:
            bool: True if deletion successful, False otherwise
        """
        bucket_name = self._get_bucket_name(case_gid)

        try:
            # Check if bucket exists
            if not self.client.client.bucket_exists(bucket_name):
                logger.info(f"Bucket for case {case_gid} does not exist")
                return True

            # List and delete all objects first
            files = self.list_case_files(case_gid)
            for file_info in files:
                self.delete_document(case_gid, file_info['name'])

            # Delete the bucket
            success = self.client.delete_bucket(bucket_name)

            if success:
                logger.info(f"Deleted storage for case {case_gid}")
            else:
                logger.error(f"Failed to delete storage for case {case_gid}")

            return success

        except Exception as e:
            logger.error(f"Error deleting storage for case {case_gid}: {e}")
            return False

    def get_document_metadata(
        self,
        case_gid: str,
        filename: str,
    ) -> Optional[dict]:
        """
        Get metadata for a specific document

        Args:
            case_gid: GID of the case
            filename: Name of the file

        Returns:
            dict: File metadata, or None if not found
        """
        files = self.list_case_files(case_gid)
        for file_info in files:
            if file_info['name'] == filename:
                return file_info
        return None


# Create singleton instance
storage_service = StorageService()
