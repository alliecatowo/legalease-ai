#!/usr/bin/env python3
"""
Marker Parser Test

Focused test to verify MarkerParser works correctly and handles the 3/250 page bug.

Tests:
1. All pages extracted correctly (not 3/250 bug)
2. Bboxes in correct format {l, t, r, b}
3. Text extraction quality
4. Block structure validity
5. Reasonable processing time

Usage:
    mise run test-marker-parser
    # or
    python scripts/test_marker_parser.py
"""

import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.workers.parsers.factory import ParserFactory
from app.workers.parsers.base import ParserType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResult:
    """Simple test result tracker"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def pass_test(self, name: str):
        self.passed += 1
        logger.info(f"✓ PASS: {name}")

    def fail_test(self, name: str, reason: str):
        self.failed += 1
        self.errors.append(f"{name}: {reason}")
        logger.error(f"✗ FAIL: {name} - {reason}")

    def summary(self):
        total = self.passed + self.failed
        logger.info("\n" + "="*60)
        logger.info(f"TEST SUMMARY: {self.passed}/{total} passed")
        if self.errors:
            logger.info("\nFailed Tests:")
            for error in self.errors:
                logger.info(f"  - {error}")
        logger.info("="*60)
        return self.failed == 0


def create_test_pdf() -> bytes:
    """
    Create a simple multi-page PDF for testing.

    Returns:
        PDF bytes
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from io import BytesIO

        logger.info("Creating test PDF with reportlab...")

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)

        # Create 5 test pages with different content
        for page_num in range(1, 6):
            c.drawString(100, 750, f"Test Document - Page {page_num}")
            c.drawString(100, 700, f"This is page {page_num} of the test document.")
            c.drawString(100, 650, "Testing Marker parser functionality:")
            c.drawString(120, 620, f"- Page extraction (page {page_num}/5)")
            c.drawString(120, 590, "- Bounding box extraction")
            c.drawString(120, 560, "- Text quality")
            c.drawString(120, 530, "- Block structure")

            # Add some sample content
            y_pos = 480
            for i in range(5):
                c.drawString(100, y_pos, f"Line {i+1}: Sample text content for testing.")
                y_pos -= 30

            c.showPage()

        c.save()

        pdf_bytes = buffer.getvalue()
        logger.info(f"Created test PDF: {len(pdf_bytes)} bytes, 5 pages")
        return pdf_bytes

    except ImportError:
        logger.warning("reportlab not available, using matplotlib PDF instead")
        # Fallback to matplotlib PDF (simpler)
        return _create_matplotlib_pdf()


def _create_matplotlib_pdf() -> bytes:
    """
    Fallback: Use matplotlib to create a simple PDF.

    Returns:
        PDF bytes
    """
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        from io import BytesIO

        logger.info("Creating test PDF with matplotlib...")

        buffer = BytesIO()

        # Create a simple figure with text
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.text(0.5, 0.5, 'Test Document\n\nMarker Parser Test\n\nPage 1 of 1',
                ha='center', va='center', fontsize=20)
        ax.axis('off')

        plt.savefig(buffer, format='pdf')
        plt.close()

        pdf_bytes = buffer.getvalue()
        logger.info(f"Created matplotlib PDF: {len(pdf_bytes)} bytes")
        return pdf_bytes

    except Exception as e:
        logger.error(f"Failed to create matplotlib PDF: {e}")
        raise RuntimeError("Cannot create test PDF - install reportlab or matplotlib")


def validate_page_count(result: Any, expected_pages: int, test_results: TestResult):
    """
    Test 1: Verify all pages were extracted (not 3/250 bug)
    """
    actual_pages = result.page_count

    if actual_pages == expected_pages:
        test_results.pass_test(f"Page count ({actual_pages}/{expected_pages})")
    else:
        test_results.fail_test(
            "Page count",
            f"Expected {expected_pages} pages, got {actual_pages}"
        )

    # Also check content pages
    content_pages = result.content_page_count
    if content_pages == expected_pages:
        test_results.pass_test(f"Content pages ({content_pages}/{expected_pages})")
    else:
        test_results.fail_test(
            "Content pages",
            f"Expected {expected_pages} content pages, got {content_pages}"
        )


def validate_bboxes(result: Any, test_results: TestResult):
    """
    Test 2: Verify bboxes are in correct format {l, t, r, b}
    """
    bbox_count = 0
    invalid_bboxes = 0

    for page in result.pages:
        for bbox in page.bboxes:
            bbox_count += 1

            # Check required keys
            required_keys = {'l', 't', 'r', 'b', 'page'}
            if not required_keys.issubset(bbox.keys()):
                invalid_bboxes += 1
                logger.debug(f"Invalid bbox on page {page.page_number}: {bbox.keys()}")
                continue

            # Check coordinate validity
            if bbox['l'] > bbox['r']:
                invalid_bboxes += 1
                logger.debug(f"Invalid bbox: left > right on page {page.page_number}")

            if bbox['t'] > bbox['b']:
                invalid_bboxes += 1
                logger.debug(f"Invalid bbox: top > bottom on page {page.page_number}")

    if bbox_count == 0:
        test_results.fail_test("Bbox extraction", "No bboxes found")
    elif invalid_bboxes > 0:
        test_results.fail_test(
            "Bbox format",
            f"{invalid_bboxes}/{bbox_count} bboxes invalid"
        )
    else:
        test_results.pass_test(f"Bbox format ({bbox_count} bboxes valid)")


def validate_text_quality(result: Any, test_results: TestResult):
    """
    Test 3: Verify text extraction quality
    """
    total_text = result.text

    if not total_text or len(total_text.strip()) < 10:
        test_results.fail_test("Text extraction", "No meaningful text extracted")
        return

    # Check for expected content
    expected_phrases = ["Test Document", "page", "testing"]
    found_phrases = sum(1 for phrase in expected_phrases if phrase.lower() in total_text.lower())

    if found_phrases == 0:
        test_results.fail_test(
            "Text extraction quality",
            "None of the expected phrases found in extracted text"
        )
    else:
        test_results.pass_test(
            f"Text extraction ({len(total_text)} chars, {found_phrases}/{len(expected_phrases)} phrases found)"
        )

    # Check per-page text
    pages_with_text = sum(1 for page in result.pages if page.has_content)
    if pages_with_text > 0:
        test_results.pass_test(f"Per-page text ({pages_with_text} pages with content)")
    else:
        test_results.fail_test("Per-page text", "No pages have content")


def validate_block_structure(result: Any, test_results: TestResult):
    """
    Test 4: Verify block structure is valid
    """
    total_blocks = 0
    invalid_blocks = 0

    for page in result.pages:
        for block in page.blocks:
            total_blocks += 1

            # Check required fields
            if 'block_type' not in block:
                invalid_blocks += 1
                logger.debug(f"Block missing block_type on page {page.page_number}")

    if total_blocks == 0:
        # Blocks are optional depending on output format
        logger.info("No blocks found (may be expected for markdown format)")
        test_results.pass_test("Block structure (no blocks, acceptable)")
    elif invalid_blocks > 0:
        test_results.fail_test(
            "Block structure",
            f"{invalid_blocks}/{total_blocks} blocks invalid"
        )
    else:
        test_results.pass_test(f"Block structure ({total_blocks} blocks valid)")


def validate_processing_time(result: Any, test_results: TestResult, max_time: float = 120.0):
    """
    Test 5: Verify processing time is reasonable

    Args:
        result: Parsed document result
        test_results: Test result tracker
        max_time: Maximum acceptable processing time in seconds
    """
    processing_time = result.processing_time

    if processing_time <= max_time:
        test_results.pass_test(f"Processing time ({processing_time:.2f}s <= {max_time}s)")
    else:
        test_results.fail_test(
            "Processing time",
            f"Took {processing_time:.2f}s (max: {max_time}s)"
        )

    # Log performance metrics
    if result.page_count > 0:
        time_per_page = processing_time / result.page_count
        logger.info(f"Performance: {time_per_page:.2f}s per page")


def run_tests(use_llm: bool = False):
    """
    Run all Marker parser tests

    Args:
        use_llm: Whether to use LLM enhancement (slower but more accurate)
    """
    test_results = TestResult()

    logger.info("\n" + "="*60)
    logger.info(f"MARKER PARSER TEST (LLM={'ON' if use_llm else 'OFF'})")
    logger.info("="*60 + "\n")

    try:
        # Step 1: Create test PDF
        logger.info("Step 1: Creating test PDF...")
        pdf_bytes = create_test_pdf()
        expected_pages = 5  # Our test PDF has 5 pages

        # Step 2: Create parser
        logger.info("\nStep 2: Creating Marker parser...")
        config = {
            "use_llm": use_llm,
            "batch_multiplier": 2,
            "output_format": "json",
            "debug": False,
        }
        parser = ParserFactory.create_parser(ParserType.MARKER, config)
        logger.info(f"Parser info: {parser.get_parser_info()}")

        # Step 3: Parse document
        logger.info("\nStep 3: Parsing document...")
        start_time = time.time()
        result = parser.parse(pdf_bytes, "test_document.pdf")
        parse_time = time.time() - start_time
        logger.info(f"Parsing completed in {parse_time:.2f}s")

        # Step 4: Run validation tests
        logger.info("\nStep 4: Running validation tests...\n")

        validate_page_count(result, expected_pages, test_results)
        validate_bboxes(result, test_results)
        validate_text_quality(result, test_results)
        validate_block_structure(result, test_results)
        validate_processing_time(result, test_results)

        # Step 5: Print detailed results
        logger.info("\n" + "-"*60)
        logger.info("DETAILED RESULTS:")
        logger.info("-"*60)
        logger.info(f"Pages: {result.page_count}")
        logger.info(f"Content pages: {result.content_page_count}")
        logger.info(f"Total characters: {result.total_char_count}")
        logger.info(f"Total words: {result.total_word_count}")
        logger.info(f"Processing time: {result.processing_time:.2f}s")
        logger.info(f"Parser: {result.parser_type.value}")
        logger.info(f"Metadata: {result.metadata}")

        # Show per-page stats
        logger.info("\nPer-Page Statistics:")
        for page in result.pages:
            logger.info(
                f"  Page {page.page_number}: "
                f"{page.char_count} chars, "
                f"{page.word_count} words, "
                f"{len(page.bboxes)} bboxes, "
                f"{len(page.blocks)} blocks"
            )

        # Show sample text from first page
        if result.pages:
            first_page_text = result.pages[0].text[:200]
            logger.info(f"\nSample text (first 200 chars):")
            logger.info(f"  {first_page_text}...")

    except Exception as e:
        logger.error(f"\nTest execution failed: {e}", exc_info=True)
        test_results.fail_test("Test execution", str(e))

    # Print summary
    success = test_results.summary()

    return 0 if success else 1


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Test Marker parser")
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Enable LLM enhancement (slower, requires GOOGLE_API_KEY)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run tests
    exit_code = run_tests(use_llm=args.with_llm)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
