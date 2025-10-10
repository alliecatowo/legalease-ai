#!/usr/bin/env python3
"""
Test script for Docling Parser and OCR Pipeline.

This script demonstrates how to use the DoclingParser and OCRPipeline
to extract text from various document formats.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.workers.pipelines.docling_parser import DoclingParser
from app.workers.pipelines.ocr_pipeline import OCRPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_ocr_pipeline():
    """Test the OCR pipeline with a sample PDF."""
    logger.info("=== Testing OCR Pipeline ===")

    # Initialize OCR pipeline
    ocr = OCRPipeline(
        language='eng',
        dpi=300,
        min_confidence=50.0  # Minimum 50% confidence
    )

    # Example: Test with a sample file (you would replace with actual file path)
    sample_file = "/path/to/sample.pdf"

    if Path(sample_file).exists():
        logger.info(f"Processing file: {sample_file}")

        # Process the file
        result = ocr.process(sample_file)

        if result['success']:
            logger.info(f" Successfully processed {result.get('total_pages', 0)} pages")
            logger.info(f"  Total words extracted: {result.get('total_words', 0)}")
            logger.info(f"  Average confidence: {result.get('avg_confidence', 0):.2f}%")
            logger.info(f"  Text preview: {result['text'][:200]}...")
        else:
            logger.error(f" Failed to process: {result.get('error', 'Unknown error')}")
    else:
        logger.warning(f"Sample file not found: {sample_file}")
        logger.info("To test OCR, provide a valid PDF file path")


def test_docling_parser():
    """Test the Docling parser with sample documents."""
    logger.info("\n=== Testing Docling Parser ===")

    # Initialize parser with OCR support
    parser = DoclingParser(use_ocr=True)

    # Example: Test with sample files
    sample_files = [
        "/path/to/sample.pdf",
        "/path/to/sample.docx",
        "/path/to/sample.txt"
    ]

    for sample_file in sample_files:
        if not Path(sample_file).exists():
            logger.warning(f"Sample file not found: {sample_file}")
            continue

        logger.info(f"\nProcessing: {sample_file}")

        try:
            # Read file content
            with open(sample_file, 'rb') as f:
                file_content = f.read()

            # Parse the document
            result = parser.parse(
                file_content=file_content,
                filename=Path(sample_file).name
            )

            logger.info(f" Successfully parsed document")
            logger.info(f"  Type: {result.get('structure', {}).get('type', 'unknown')}")
            logger.info(f"  Pages: {len(result.get('pages', []))}")
            logger.info(f"  Characters: {result.get('metadata', {}).get('char_count', 0)}")
            logger.info(f"  Text preview: {result['text'][:200]}...")

            # Show table information if available
            if 'tables' in result.get('structure', {}):
                tables = result['structure']['tables']
                logger.info(f"  Tables found: {len(tables)}")

        except Exception as e:
            logger.error(f" Error parsing {sample_file}: {e}")


def demonstrate_usage():
    """Demonstrate typical usage patterns."""
    logger.info("\n=== Usage Demonstration ===\n")

    # Example 1: Parse a PDF document
    logger.info("Example 1: Parse PDF with OCR fallback")
    logger.info("-" * 50)
    logger.info("""
    parser = DoclingParser(use_ocr=True)

    with open('document.pdf', 'rb') as f:
        file_content = f.read()

    result = parser.parse(
        file_content=file_content,
        filename='document.pdf'
    )

    print(f"Extracted text: {result['text']}")
    print(f"Number of pages: {len(result['pages'])}")
    print(f"Metadata: {result['metadata']}")
    """)

    # Example 2: OCR a scanned document
    logger.info("\nExample 2: OCR a scanned document")
    logger.info("-" * 50)
    logger.info("""
    ocr = OCRPipeline(
        language='eng',
        dpi=300,
        min_confidence=60.0
    )

    result = ocr.process('scanned_document.pdf')

    if result['success']:
        print(f"Text: {result['text']}")
        print(f"Confidence: {result['avg_confidence']:.2f}%")
        print(f"Pages processed: {result['successful_pages']}")
    """)

    # Example 3: Extract tables from DOCX
    logger.info("\nExample 3: Extract tables from DOCX")
    logger.info("-" * 50)
    logger.info("""
    parser = DoclingParser(use_ocr=False)

    with open('contract.docx', 'rb') as f:
        file_content = f.read()

    result = parser.parse(
        file_content=file_content,
        filename='contract.docx'
    )

    # Access tables from structure
    if 'tables' in result.get('structure', {}):
        for table in result['structure']['tables']:
            print(f"Table {table['index']}: {table['rows']}x{table['cols']}")
            print(f"Data: {table['data']}")
    """)


def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("Docling Parser & OCR Pipeline Test Suite")
    logger.info("=" * 60)

    # Show usage examples
    demonstrate_usage()

    # Run actual tests if sample files are available
    logger.info("\n" + "=" * 60)
    logger.info("Running Tests")
    logger.info("=" * 60)

    # Test OCR Pipeline
    test_ocr_pipeline()

    # Test Docling Parser
    test_docling_parser()

    logger.info("\n" + "=" * 60)
    logger.info("Test suite completed")
    logger.info("=" * 60)

    logger.info("\nNote: To fully test the parsers, provide sample documents:")
    logger.info("  - PDF files (native or scanned)")
    logger.info("  - DOCX files")
    logger.info("  - TXT files")


if __name__ == "__main__":
    main()
