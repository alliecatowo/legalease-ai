"""MinIO client configuration and utilities."""

import io
import logging
from typing import BinaryIO, Optional
from minio import Minio
from minio.error import S3Error
from app.core.config import settings

logger = logging.getLogger(__name__)


class MinIOClient:
    """MinIO client wrapper for file storage operations."""

    def __init__(self):
        """Initialize MinIO client."""
        self.client = None
        self.bucket_name = settings.MINIO_BUCKET
        self._initialized = False

    def _initialize(self) -> None:
        """Initialize the MinIO client connection (lazy loading)."""
        if self._initialized:
            return

        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self._ensure_bucket()
        self._initialized = True

    def _ensure_bucket(self) -> None:
        """Ensure the bucket exists, create if it doesn't."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
            else:
                logger.info(f"MinIO bucket exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise

    def upload_file(
        self,
        file_data: BinaryIO,
        object_name: str,
        content_type: Optional[str] = None,
        length: int = -1,
    ) -> str:
        """
        Upload a file to MinIO.

        Args:
            file_data: File-like object to upload
            object_name: Name/path for the object in MinIO
            content_type: MIME type of the file
            length: Length of the file data (-1 for unknown)

        Returns:
            str: The object name/path in MinIO

        Raises:
            S3Error: If upload fails
        """
        self._initialize()
        try:
            # If length is -1, read all data into memory
            if length == -1:
                if hasattr(file_data, 'read'):
                    data = file_data.read()
                    length = len(data)
                    file_data = io.BytesIO(data)
                else:
                    raise ValueError("Cannot determine file length")

            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_data,
                length=length,
                content_type=content_type,
            )
            logger.info(f"Uploaded file to MinIO: {object_name}")
            return object_name
        except S3Error as e:
            logger.error(f"Error uploading file to MinIO: {e}")
            raise

    def download_file(self, object_name: str) -> bytes:
        """
        Download a file from MinIO.

        WARNING: This loads the entire file into memory. Use download_file_to_path()
        for large files to avoid memory issues.

        Args:
            object_name: Name/path of the object in MinIO

        Returns:
            bytes: File content

        Raises:
            S3Error: If download fails
        """
        self._initialize()
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            logger.info(f"Downloaded file from MinIO: {object_name}")
            return data
        except S3Error as e:
            logger.error(f"Error downloading file from MinIO: {e}")
            raise

    def download_file_to_path(self, object_name: str, local_path: str, chunk_size: int = 8192) -> str:
        """
        Download a file from MinIO directly to disk using streaming (memory-efficient).

        This method streams the file in chunks without loading it entirely into memory,
        making it suitable for large files.

        Args:
            object_name: Name/path of the object in MinIO
            local_path: Local file path to write to
            chunk_size: Size of chunks to read at a time (default: 8KB)

        Returns:
            str: Local file path where file was saved

        Raises:
            S3Error: If download fails
        """
        self._initialize()
        try:
            logger.info(f"Streaming download from MinIO: {object_name} -> {local_path}")
            response = self.client.get_object(self.bucket_name, object_name)

            # Stream to file in chunks
            with open(local_path, 'wb') as f:
                for chunk in response.stream(chunk_size):
                    f.write(chunk)

            response.close()
            response.release_conn()
            logger.info(f"Streamed file from MinIO to {local_path}")
            return local_path
        except S3Error as e:
            logger.error(f"Error streaming file from MinIO: {e}")
            raise
        except IOError as e:
            logger.error(f"Error writing file to {local_path}: {e}")
            raise

    def get_object_range(self, object_name: str, offset: int, length: int) -> bytes:
        """
        Get a specific byte range from a MinIO object without loading the entire file.

        This enables true HTTP Range request support for video/audio streaming,
        allowing instant playback start and efficient seeking.

        Args:
            object_name: Name/path of the object in MinIO
            offset: Starting byte position (0-indexed)
            length: Number of bytes to read

        Returns:
            bytes: Requested byte range

        Raises:
            S3Error: If range request fails
        """
        self._initialize()
        try:
            logger.debug(f"Fetching range from MinIO: {object_name} (offset={offset}, length={length})")
            response = self.client.get_object(
                self.bucket_name,
                object_name,
                offset=offset,
                length=length
            )

            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Error fetching range from MinIO: {e}")
            raise

    def get_object_size(self, object_name: str) -> int:
        """
        Get the size of an object in MinIO without downloading it.

        Args:
            object_name: Name/path of the object in MinIO

        Returns:
            int: Object size in bytes

        Raises:
            S3Error: If stat fails
        """
        self._initialize()
        try:
            stat = self.client.stat_object(self.bucket_name, object_name)
            return stat.size
        except S3Error as e:
            logger.error(f"Error getting object size from MinIO: {e}")
            raise

    def delete_file(self, object_name: str) -> None:
        """
        Delete a file from MinIO.

        Args:
            object_name: Name/path of the object in MinIO

        Raises:
            S3Error: If deletion fails
        """
        self._initialize()
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"Deleted file from MinIO: {object_name}")
        except S3Error as e:
            logger.error(f"Error deleting file from MinIO: {e}")
            raise

    def file_exists(self, object_name: str) -> bool:
        """
        Check if a file exists in MinIO.

        Args:
            object_name: Name/path of the object in MinIO

        Returns:
            bool: True if file exists, False otherwise
        """
        self._initialize()
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False

    def get_presigned_url(
        self, object_name: str, expires_in_seconds: int = 3600
    ) -> str:
        """
        Generate a presigned URL for temporary access to a file.

        Args:
            object_name: Name/path of the object in MinIO
            expires_in_seconds: URL expiration time in seconds

        Returns:
            str: Presigned URL

        Raises:
            S3Error: If URL generation fails
        """
        self._initialize()
        try:
            from datetime import timedelta

            url = self.client.presigned_get_object(
                self.bucket_name, object_name, expires=timedelta(seconds=expires_in_seconds)
            )
            logger.info(f"Generated presigned URL for: {object_name}")
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise


# Singleton instance
minio_client = MinIOClient()
