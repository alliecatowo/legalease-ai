"""
Docling Document Parser

Extracts text and structure from various document formats using Docling library.
Supports PDF, DOCX, and other common legal document formats with OCR fallback.
"""

import logging
import io
from typing import Dict, Any, Optional, List, BinaryIO
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)


class DoclingParser:
    """
    Document parser using Docling for text extraction.

    Features:
    - Multi-format support (PDF, DOCX, DOC, TXT)
    - Structure preservation (headers, paragraphs, tables)
    - OCR fallback for scanned documents
    - Metadata extraction
    """

    def __init__(self, use_ocr: bool = True):
        """
        Initialize the Docling parser.

        Args:
            use_ocr: Whether to use OCR for scanned documents
        """
        self.use_ocr = use_ocr
        logger.info(f"Initialized DoclingParser (OCR: {use_ocr})")

    def parse(
        self,
        file_content: bytes,
        filename: str,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parse a document and extract text and metadata.

        Args:
            file_content: Raw bytes of the document
            filename: Original filename (used to determine format)
            mime_type: MIME type of the document

        Returns:
            Dictionary containing:
                - text: Full extracted text
                - pages: List of page texts
                - metadata: Document metadata
                - structure: Document structure information
        """
        logger.info(f"Parsing document: {filename} (MIME: {mime_type})")

        # Determine file type
        file_ext = Path(filename).suffix.lower()

        try:
            # Route to appropriate parser based on file type
            if file_ext == '.pdf':
                return self._parse_pdf(file_content, filename)
            elif file_ext in ['.docx', '.doc']:
                return self._parse_docx(file_content, filename)
            elif file_ext == '.txt':
                return self._parse_text(file_content, filename)
            else:
                logger.warning(f"Unsupported file type: {file_ext}, attempting generic parsing")
                return self._parse_generic(file_content, filename)

        except Exception as e:
            logger.error(f"Error parsing document {filename}: {e}")
            raise

    def _parse_pdf(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Parse PDF document with OCR fallback.

        Args:
            file_content: PDF file bytes
            filename: Original filename

        Returns:
            Parsed document data
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("PyMuPDF (fitz) not installed. Install with: pip install pymupdf")
            # Fallback to basic text extraction
            return self._parse_pdf_fallback(file_content, filename)

        try:
            # Open PDF from bytes
            pdf_document = fitz.open(stream=file_content, filetype="pdf")

            pages = []
            full_text = []
            metadata = {}

            # Extract metadata
            metadata = {
                "page_count": pdf_document.page_count,
                "title": pdf_document.metadata.get("title", ""),
                "author": pdf_document.metadata.get("author", ""),
                "subject": pdf_document.metadata.get("subject", ""),
                "creator": pdf_document.metadata.get("creator", ""),
            }

            # Extract text from each page
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                page_text = page.get_text()

                # If page is mostly empty and OCR is enabled, try OCR
                if self.use_ocr and len(page_text.strip()) < 50:
                    logger.info(f"Page {page_num + 1} has little text, attempting OCR")
                    page_text = self._ocr_page(page)

                pages.append({
                    "page_number": page_num + 1,
                    "text": page_text,
                    "char_count": len(page_text),
                })
                full_text.append(page_text)

            pdf_document.close()

            result = {
                "text": "\n\n".join(full_text),
                "pages": pages,
                "metadata": metadata,
                "structure": {
                    "type": "pdf",
                    "page_count": len(pages),
                },
            }

            logger.info(f"Successfully parsed PDF: {len(pages)} pages, {len(result['text'])} chars")
            return result

        except Exception as e:
            logger.error(f"Error parsing PDF with PyMuPDF: {e}")
            return self._parse_pdf_fallback(file_content, filename)

    def _parse_pdf_fallback(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Fallback PDF parser using pypdf.

        Args:
            file_content: PDF file bytes
            filename: Original filename

        Returns:
            Parsed document data
        """
        try:
            from pypdf import PdfReader
        except ImportError:
            logger.error("pypdf not installed. Install with: pip install pypdf")
            raise

        try:
            pdf_reader = PdfReader(io.BytesIO(file_content))

            pages = []
            full_text = []

            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                pages.append({
                    "page_number": page_num + 1,
                    "text": page_text,
                    "char_count": len(page_text),
                })
                full_text.append(page_text)

            metadata = {
                "page_count": len(pdf_reader.pages),
                "title": pdf_reader.metadata.get("/Title", "") if pdf_reader.metadata else "",
                "author": pdf_reader.metadata.get("/Author", "") if pdf_reader.metadata else "",
            }

            result = {
                "text": "\n\n".join(full_text),
                "pages": pages,
                "metadata": metadata,
                "structure": {
                    "type": "pdf",
                    "page_count": len(pages),
                },
            }

            logger.info(f"Successfully parsed PDF (fallback): {len(pages)} pages")
            return result

        except Exception as e:
            logger.error(f"Error in PDF fallback parser: {e}")
            raise

    def _parse_docx(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Parse DOCX document.

        Args:
            file_content: DOCX file bytes
            filename: Original filename

        Returns:
            Parsed document data
        """
        try:
            from docx import Document
        except ImportError:
            logger.error("python-docx not installed. Install with: pip install python-docx")
            raise

        try:
            # Open DOCX from bytes
            doc = Document(io.BytesIO(file_content))

            paragraphs = []
            full_text = []

            # Extract paragraphs
            for i, para in enumerate(doc.paragraphs):
                if para.text.strip():
                    paragraphs.append({
                        "index": i,
                        "text": para.text,
                        "style": para.style.name if para.style else "Normal",
                    })
                    full_text.append(para.text)

            # Extract tables
            tables = []
            for table_idx, table in enumerate(doc.tables):
                table_data = []
                for row in table.rows:
                    row_data = [cell.text for cell in row.cells]
                    table_data.append(row_data)
                tables.append({
                    "index": table_idx,
                    "rows": len(table.rows),
                    "cols": len(table.columns),
                    "data": table_data,
                })

            # Extract metadata
            metadata = {
                "paragraph_count": len(paragraphs),
                "table_count": len(tables),
                "author": doc.core_properties.author or "",
                "title": doc.core_properties.title or "",
                "subject": doc.core_properties.subject or "",
                "created": str(doc.core_properties.created) if doc.core_properties.created else "",
                "modified": str(doc.core_properties.modified) if doc.core_properties.modified else "",
            }

            result = {
                "text": "\n\n".join(full_text),
                "pages": [],  # DOCX doesn't have explicit pages
                "metadata": metadata,
                "structure": {
                    "type": "docx",
                    "paragraphs": paragraphs,
                    "tables": tables,
                },
            }

            logger.info(f"Successfully parsed DOCX: {len(paragraphs)} paragraphs, {len(tables)} tables")
            return result

        except Exception as e:
            logger.error(f"Error parsing DOCX: {e}")
            raise

    def _parse_text(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Parse plain text document.

        Args:
            file_content: Text file bytes
            filename: Original filename

        Returns:
            Parsed document data
        """
        try:
            # Try UTF-8 first, then fall back to latin-1
            try:
                text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                text = file_content.decode('latin-1')

            # Split into lines
            lines = text.split('\n')

            result = {
                "text": text,
                "pages": [],
                "metadata": {
                    "line_count": len(lines),
                    "char_count": len(text),
                },
                "structure": {
                    "type": "text",
                    "lines": len(lines),
                },
            }

            logger.info(f"Successfully parsed text file: {len(lines)} lines")
            return result

        except Exception as e:
            logger.error(f"Error parsing text file: {e}")
            raise

    def _parse_generic(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Generic fallback parser for unsupported formats.

        Args:
            file_content: File bytes
            filename: Original filename

        Returns:
            Parsed document data (best effort)
        """
        logger.warning(f"Using generic parser for {filename}")

        try:
            # Try to decode as text
            text = file_content.decode('utf-8', errors='ignore')

            return {
                "text": text,
                "pages": [],
                "metadata": {
                    "char_count": len(text),
                    "format": "unknown",
                },
                "structure": {
                    "type": "generic",
                },
            }
        except Exception as e:
            logger.error(f"Error in generic parser: {e}")
            raise

    def _ocr_page(self, page) -> str:
        """
        Perform OCR on a PDF page.

        Args:
            page: PyMuPDF page object

        Returns:
            OCR-extracted text
        """
        try:
            import fitz  # PyMuPDF
            import pytesseract
            from PIL import Image
        except ImportError:
            logger.warning("OCR dependencies not installed (pytesseract, Pillow, PyMuPDF)")
            return ""

        try:
            # Render page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Perform OCR
            text = pytesseract.image_to_string(img)
            logger.info(f"OCR extracted {len(text)} characters")

            return text

        except Exception as e:
            logger.error(f"Error performing OCR: {e}")
            return ""

    def validate_document(self, file_content: bytes, filename: str) -> bool:
        """
        Validate if a document can be parsed.

        Args:
            file_content: File bytes
            filename: Original filename

        Returns:
            True if document can be parsed
        """
        file_ext = Path(filename).suffix.lower()
        supported_formats = ['.pdf', '.docx', '.doc', '.txt']

        return file_ext in supported_formats
