"""Service for generating page images from PDF documents."""

import io
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from app.core.minio_client import minio_client

logger = logging.getLogger(__name__)


class PageImageService:
    """Service for generating and storing page images from PDFs."""

    DPI = 150  # Standard DPI for page images
    IMAGE_FORMAT = "PNG"

    @staticmethod
    def generate_page_images(
        pdf_content: bytes,
        document_id: int,
        case_id: int,
    ) -> List[str]:
        """
        Generate PNG images for each page of a PDF and upload to MinIO.

        Args:
            pdf_content: PDF file bytes
            document_id: Database document ID
            case_id: Database case ID

        Returns:
            List[str]: List of MinIO paths for generated images

        Raises:
            Exception: If image generation fails
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("PyMuPDF not installed. Install with: pip install pymupdf")
            raise

        image_paths = []

        try:
            # Open PDF from bytes
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            logger.info(f"Generating images for {pdf_document.page_count} pages")

            for page_num in range(pdf_document.page_count):
                try:
                    # Get page
                    page = pdf_document[page_num]

                    # Render page to image at specified DPI
                    # mat = fitz.Matrix(DPI/72, DPI/72)  # 72 is default DPI
                    zoom = PageImageService.DPI / 72
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)

                    # Convert to PNG bytes
                    img_bytes = pix.tobytes(output="png")

                    # Generate MinIO path
                    object_name = PageImageService._generate_image_path(
                        case_id=case_id,
                        document_id=document_id,
                        page_num=page_num + 1,
                    )

                    # Upload to MinIO
                    minio_client.upload_file(
                        file_data=io.BytesIO(img_bytes),
                        object_name=object_name,
                        content_type="image/png",
                        length=len(img_bytes),
                    )

                    image_paths.append(object_name)
                    logger.debug(f"Generated image for page {page_num + 1}: {object_name}")

                except Exception as e:
                    logger.error(f"Error generating image for page {page_num + 1}: {e}")
                    # Continue with other pages
                    continue

            pdf_document.close()

            logger.info(f"Successfully generated {len(image_paths)} page images for document {document_id}")
            return image_paths

        except Exception as e:
            logger.error(f"Error generating page images: {e}")
            raise

    @staticmethod
    def _generate_image_path(case_id: int, document_id: int, page_num: int) -> str:
        """
        Generate MinIO path for a page image.

        Args:
            case_id: Database case ID
            document_id: Database document ID
            page_num: Page number (1-indexed)

        Returns:
            str: MinIO object path
        """
        return f"documents/{case_id}/{document_id}/pages/page_{page_num}.png"

    @staticmethod
    def get_page_image_url(
        case_id: int,
        document_id: int,
        page_num: int,
        expires_in_seconds: int = 3600,
    ) -> str:
        """
        Get presigned URL for a page image.

        Args:
            case_id: Database case ID
            document_id: Database document ID
            page_num: Page number (1-indexed)
            expires_in_seconds: URL expiration time

        Returns:
            str: Presigned URL for the image

        Raises:
            Exception: If URL generation fails
        """
        object_name = PageImageService._generate_image_path(
            case_id=case_id,
            document_id=document_id,
            page_num=page_num,
        )

        return minio_client.get_presigned_url(
            object_name=object_name,
            expires_in_seconds=expires_in_seconds,
        )

    @staticmethod
    def get_all_page_image_urls(
        case_id: int,
        document_id: int,
        page_count: int,
        expires_in_seconds: int = 3600,
    ) -> List[Dict[str, Any]]:
        """
        Get presigned URLs for all page images.

        Args:
            case_id: Database case ID
            document_id: Database document ID
            page_count: Total number of pages
            expires_in_seconds: URL expiration time

        Returns:
            List[Dict]: List of page data with URLs
        """
        pages = []

        for page_num in range(1, page_count + 1):
            try:
                url = PageImageService.get_page_image_url(
                    case_id=case_id,
                    document_id=document_id,
                    page_num=page_num,
                    expires_in_seconds=expires_in_seconds,
                )

                pages.append({
                    "page_number": page_num,
                    "image_url": url,
                })

            except Exception as e:
                logger.warning(f"Failed to get URL for page {page_num}: {e}")
                # Include page without URL
                pages.append({
                    "page_number": page_num,
                    "image_url": None,
                    "error": str(e),
                })

        return pages

    @staticmethod
    def delete_page_images(case_id: int, document_id: int, page_count: int) -> bool:
        """
        Delete all page images for a document.

        Args:
            case_id: Database case ID
            document_id: Database document ID
            page_count: Total number of pages

        Returns:
            bool: True if deletion successful
        """
        success = True

        for page_num in range(1, page_count + 1):
            try:
                object_name = PageImageService._generate_image_path(
                    case_id=case_id,
                    document_id=document_id,
                    page_num=page_num,
                )

                minio_client.delete_file(object_name)
                logger.debug(f"Deleted page image: {object_name}")

            except Exception as e:
                logger.warning(f"Failed to delete page {page_num} image: {e}")
                success = False

        return success
