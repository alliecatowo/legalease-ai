"""
OCR Pipeline for extracting text from scanned documents.

This module provides a tiered OCR system with:
- Automatic scanned document detection
- Primary Tesseract integration
- Pytesseract fallback support
- Confidence scoring
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image
from pdf2image import convert_from_path
import pytesseract

logger = logging.getLogger(__name__)


class OCRPipeline:
    """
    OCR Pipeline for extracting text from scanned documents.

    Features:
    - Detects if document is scanned (image-based)
    - Uses Tesseract OCR engine
    - Returns text with confidence scores
    - Handles multi-page PDFs
    """

    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        language: str = "eng",
        dpi: int = 300,
        min_confidence: float = 0.0
    ):
        """
        Initialize the OCR pipeline.

        Args:
            tesseract_cmd: Path to Tesseract executable (auto-detect if None)
            language: OCR language code (default: English)
            dpi: DPI for PDF to image conversion (default: 300)
            min_confidence: Minimum confidence threshold for text extraction
        """
        self.language = language
        self.dpi = dpi
        self.min_confidence = min_confidence

        # Configure Tesseract
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        # Verify Tesseract is available
        try:
            pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR initialized successfully")
        except Exception as e:
            logger.warning(f"Tesseract not found or not working: {e}")

    def detect_if_scanned(self, file_path: str) -> bool:
        """
        Detect if a PDF is scanned (image-based) or contains native text.

        This is a simplified heuristic - a more robust implementation would
        check if the PDF contains text layers.

        Args:
            file_path: Path to the PDF file

        Returns:
            True if document appears to be scanned, False otherwise
        """
        try:
            # For now, we'll use a simple heuristic:
            # Try to extract text from first page. If very little text is found,
            # it's likely scanned

            # This is a placeholder - in production you'd use a library like
            # PyPDF2 or pdfplumber to check for text layers

            # For this implementation, we'll assume PDFs with .scan. in name
            # or check file size heuristics
            file_name = os.path.basename(file_path).lower()

            # Simple heuristic: if filename contains 'scan' or 'image'
            if 'scan' in file_name or 'image' in file_name:
                logger.info(f"Document {file_name} detected as scanned (filename heuristic)")
                return True

            # Default to False - assume native PDF
            # In production, implement actual text layer detection
            logger.info(f"Document {file_name} assumed to be native PDF")
            return False

        except Exception as e:
            logger.error(f"Error detecting if scanned: {e}")
            # Default to attempting OCR if uncertain
            return True

    def extract_text_from_image(
        self,
        image: Image.Image,
        page_num: int = 0
    ) -> Dict[str, any]:
        """
        Extract text from a single image using OCR.

        Args:
            image: PIL Image object
            page_num: Page number (for logging/tracking)

        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            # Get detailed OCR data with confidence scores
            ocr_data = pytesseract.image_to_data(
                image,
                lang=self.language,
                output_type=pytesseract.Output.DICT
            )

            # Extract text with confidence filtering
            text_parts = []
            total_confidence = 0
            word_count = 0

            for i, conf in enumerate(ocr_data['conf']):
                # Filter out low confidence results
                if conf != -1 and float(conf) >= self.min_confidence:
                    text = ocr_data['text'][i].strip()
                    if text:
                        text_parts.append(text)
                        total_confidence += float(conf)
                        word_count += 1

            # Calculate average confidence
            avg_confidence = total_confidence / word_count if word_count > 0 else 0.0

            # Combine text with proper spacing
            extracted_text = ' '.join(text_parts)

            logger.info(
                f"Page {page_num}: Extracted {word_count} words "
                f"with avg confidence {avg_confidence:.2f}%"
            )

            return {
                'text': extracted_text,
                'page_num': page_num,
                'word_count': word_count,
                'confidence': avg_confidence,
                'success': True
            }

        except Exception as e:
            logger.error(f"Error extracting text from page {page_num}: {e}")
            return {
                'text': '',
                'page_num': page_num,
                'word_count': 0,
                'confidence': 0.0,
                'success': False,
                'error': str(e)
            }

    def process_pdf(self, file_path: str) -> Dict[str, any]:
        """
        Process a PDF file with OCR.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            logger.info(f"Converting PDF to images: {file_path}")

            # Convert PDF to images
            images = convert_from_path(
                file_path,
                dpi=self.dpi,
                fmt='jpeg'
            )

            logger.info(f"Processing {len(images)} pages with OCR")

            # Process each page
            results = []
            for i, image in enumerate(images):
                result = self.extract_text_from_image(image, page_num=i + 1)
                results.append(result)

            # Combine all text
            full_text = '\n\n'.join(
                [r['text'] for r in results if r['success'] and r['text']]
            )

            # Calculate overall statistics
            total_words = sum([r['word_count'] for r in results])
            avg_confidence = sum(
                [r['confidence'] for r in results if r['success']]
            ) / len(results) if results else 0.0

            successful_pages = sum([1 for r in results if r['success']])

            return {
                'text': full_text,
                'total_pages': len(images),
                'successful_pages': successful_pages,
                'total_words': total_words,
                'avg_confidence': avg_confidence,
                'page_results': results,
                'success': successful_pages > 0
            }

        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            return {
                'text': '',
                'total_pages': 0,
                'successful_pages': 0,
                'total_words': 0,
                'avg_confidence': 0.0,
                'success': False,
                'error': str(e)
            }

    def process_image(self, file_path: str) -> Dict[str, any]:
        """
        Process a single image file with OCR.

        Args:
            file_path: Path to the image file

        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            logger.info(f"Opening image: {file_path}")
            image = Image.open(file_path)

            result = self.extract_text_from_image(image, page_num=1)

            return {
                'text': result['text'],
                'total_pages': 1,
                'successful_pages': 1 if result['success'] else 0,
                'total_words': result['word_count'],
                'avg_confidence': result['confidence'],
                'page_results': [result],
                'success': result['success']
            }

        except Exception as e:
            logger.error(f"Error processing image {file_path}: {e}")
            return {
                'text': '',
                'total_pages': 1,
                'successful_pages': 0,
                'total_words': 0,
                'avg_confidence': 0.0,
                'success': False,
                'error': str(e)
            }

    def process(self, file_path: str) -> Dict[str, any]:
        """
        Main entry point for OCR processing.

        Automatically detects file type and processes accordingly.

        Args:
            file_path: Path to the file (PDF or image)

        Returns:
            Dictionary with extracted text and metadata
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return {
                'text': '',
                'success': False,
                'error': 'File not found'
            }

        file_ext = Path(file_path).suffix.lower()

        if file_ext == '.pdf':
            return self.process_pdf(file_path)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
            return self.process_image(file_path)
        else:
            logger.error(f"Unsupported file type: {file_ext}")
            return {
                'text': '',
                'success': False,
                'error': f'Unsupported file type: {file_ext}'
            }
