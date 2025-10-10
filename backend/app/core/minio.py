"""
MinIO Object Storage Client
"""
from minio import Minio
from minio.error import S3Error
from typing import Optional, BinaryIO, Callable
from datetime import timedelta
from io import BytesIO
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class MinioClient:
    """Singleton MinIO client for object storage operations"""

    _instance: Optional['MinioClient'] = None
    _client: Optional[Minio] = None

    def __new__(cls) -> 'MinioClient':
        """Ensure only one instance of MinioClient exists"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize MinIO client with configuration settings"""
        if self._client is None:
            self._client = Minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            logger.info(f"MinIO client initialized for endpoint: {settings.MINIO_ENDPOINT}")

    @property
    def client(self) -> Minio:
        """Get the underlying MinIO client instance"""
        if self._client is None:
            raise RuntimeError("MinIO client not initialized")
        return self._client

    def create_bucket(self, bucket_name: str) -> bool:
        """
        Create a new bucket for storing case files

        Args:
            bucket_name: Name of the bucket to create (e.g., 'case-123')

        Returns:
            bool: True if bucket was created or already exists, False on error
        """
        try:
            # Check if bucket already exists
            if self.client.bucket_exists(bucket_name):
                logger.info(f"Bucket '{bucket_name}' already exists")
                return True

            # Create the bucket
            self.client.make_bucket(bucket_name)
            logger.info(f"Successfully created bucket '{bucket_name}'")
            return True

        except S3Error as e:
            logger.error(f"Error creating bucket '{bucket_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating bucket '{bucket_name}': {e}")
            return False

    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_data: BinaryIO,
        file_size: int,
        content_type: str = "application/octet-stream",
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """
        Upload a file to MinIO with optional progress tracking

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object (file) in storage
            file_data: File-like object containing the data
            file_size: Size of the file in bytes
            content_type: MIME type of the file
            progress_callback: Optional callback function for progress tracking

        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            # Ensure bucket exists
            if not self.client.bucket_exists(bucket_name):
                self.create_bucket(bucket_name)

            # Create a wrapper for progress tracking if callback provided
            if progress_callback:
                original_read = file_data.read
                bytes_uploaded = [0]  # Use list to allow modification in nested function

                def progress_read(size=-1):
                    data = original_read(size)
                    if data:
                        bytes_uploaded[0] += len(data)
                        progress_callback(bytes_uploaded[0])
                    return data

                file_data.read = progress_read

            # Upload the file
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type,
            )

            logger.info(f"Successfully uploaded '{object_name}' to bucket '{bucket_name}'")
            return True

        except S3Error as e:
            logger.error(f"S3 error uploading '{object_name}' to '{bucket_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading '{object_name}': {e}")
            return False

    def download_file(
        self,
        bucket_name: str,
        object_name: str,
    ) -> Optional[BytesIO]:
        """
        Download a file from MinIO storage

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object (file) to download

        Returns:
            BytesIO: File data as BytesIO object, or None if error
        """
        try:
            # Get the object
            response = self.client.get_object(bucket_name, object_name)

            # Read data into BytesIO
            file_data = BytesIO(response.read())
            file_data.seek(0)  # Reset to beginning

            # Close the response
            response.close()
            response.release_conn()

            logger.info(f"Successfully downloaded '{object_name}' from bucket '{bucket_name}'")
            return file_data

        except S3Error as e:
            logger.error(f"S3 error downloading '{object_name}' from '{bucket_name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading '{object_name}': {e}")
            return None

    def delete_file(
        self,
        bucket_name: str,
        object_name: str,
    ) -> bool:
        """
        Delete a file from MinIO storage

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object (file) to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            self.client.remove_object(bucket_name, object_name)
            logger.info(f"Successfully deleted '{object_name}' from bucket '{bucket_name}'")
            return True

        except S3Error as e:
            logger.error(f"S3 error deleting '{object_name}' from '{bucket_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting '{object_name}': {e}")
            return False

    def get_presigned_url(
        self,
        bucket_name: str,
        object_name: str,
        expiry: timedelta = timedelta(hours=1),
    ) -> Optional[str]:
        """
        Generate a presigned URL for temporary access to a file

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object (file)
            expiry: Duration for which the URL is valid (default: 1 hour)

        Returns:
            str: Presigned URL, or None if error
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=expiry,
            )
            logger.info(f"Generated presigned URL for '{object_name}' in bucket '{bucket_name}'")
            return url

        except S3Error as e:
            logger.error(f"S3 error generating presigned URL for '{object_name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {e}")
            return None

    def list_objects(
        self,
        bucket_name: str,
        prefix: Optional[str] = None,
    ) -> list[dict]:
        """
        List all objects in a bucket with optional prefix filter

        Args:
            bucket_name: Name of the bucket
            prefix: Optional prefix to filter objects

        Returns:
            list[dict]: List of object metadata dictionaries
        """
        try:
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)

            object_list = []
            for obj in objects:
                object_list.append({
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                    "content_type": obj.content_type,
                })

            logger.info(f"Listed {len(object_list)} objects from bucket '{bucket_name}'")
            return object_list

        except S3Error as e:
            logger.error(f"S3 error listing objects in '{bucket_name}': {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing objects: {e}")
            return []

    def delete_bucket(self, bucket_name: str) -> bool:
        """
        Delete an empty bucket

        Args:
            bucket_name: Name of the bucket to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            self.client.remove_bucket(bucket_name)
            logger.info(f"Successfully deleted bucket '{bucket_name}'")
            return True

        except S3Error as e:
            logger.error(f"S3 error deleting bucket '{bucket_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting bucket: {e}")
            return False


# Create singleton instance
minio_client = MinioClient()
