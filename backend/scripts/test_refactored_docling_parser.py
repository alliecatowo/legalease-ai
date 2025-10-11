"""
Test the refactored Docling parser with GPU acceleration and proper bbox extraction.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from io import BytesIO
import json


def create_test_pdf() -> bytes:
    """Create a simple test PDF."""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch

    buffer = BytesIO()
    doc_pdf = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    text = """NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into as of January 1, 2024.

1. DEFINITION OF CONFIDENTIAL INFORMATION

For purposes of this Agreement, "Confidential Information" shall include all information or material that has or could have commercial value.

2. OBLIGATIONS OF RECEIVING PARTY

Receiving Party shall hold and maintain the Confidential Information in strictest confidence."""

    for para in text.split('\n\n'):
        if para.strip():
            p = Paragraph(para.replace('\n', '<br/>'), styles['BodyText'])
            story.append(p)
            story.append(Spacer(1, 0.2 * inch))

    doc_pdf.build(story)
    return buffer.getvalue()


def main():
    print("=" * 80)
    print("Testing Refactored Docling Parser")
    print("=" * 80)

    # Check GPU availability
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        print(f"\nGPU Status: {'CUDA Available' if gpu_available else 'CPU Only'}")
        if gpu_available:
            print(f"GPU Device: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("\nWarning: PyTorch not installed, GPU detection will fail")
        gpu_available = False

    # Create test PDF
    print("\nCreating test PDF...")
    pdf_content = create_test_pdf()
    print(f"PDF created: {len(pdf_content):,} bytes")

    # Import and test parser
    print("\nImporting DoclingParser...")
    from app.workers.pipelines.docling_parser import DoclingParser

    # Initialize parser
    parser = DoclingParser(use_ocr=True, force_full_page_ocr=False)
    print("Parser initialized")

    # Parse document
    print("\nParsing document...")
    try:
        result = parser.parse(
            file_content=pdf_content,
            filename="test_nda.pdf",
            mime_type="application/pdf"
        )

        # Display results
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)

        print(f"\nText Length: {len(result['text'])} characters")
        print(f"Pages: {len(result['pages'])}")
        print(f"Device Used: {result['metadata'].get('device', 'unknown')}")

        # Count items and bboxes
        total_items = 0
        items_with_bbox = 0

        for page in result['pages']:
            page_items = page.get('items', [])
            total_items += len(page_items)
            items_with_bbox += sum(1 for item in page_items if 'bbox' in item)

        print(f"\nTotal Items: {total_items}")
        print(f"Items with BBoxes: {items_with_bbox}")
        if total_items > 0:
            coverage = (items_with_bbox / total_items) * 100
            print(f"BBox Coverage: {coverage:.1f}%")

        # Show sample items
        if result['pages'] and result['pages'][0].get('items'):
            print("\nSample Items (first 3):")
            for i, item in enumerate(result['pages'][0]['items'][:3], 1):
                print(f"\n  Item {i}:")
                print(f"  Type: {item.get('type', 'unknown')}")
                print(f"  Text: {item.get('text', '')[:50]}...")
                if 'bbox' in item:
                    bbox = item['bbox']
                    print(f"  BBox: l={bbox['l']:.2f}, t={bbox['t']:.2f}, r={bbox['r']:.2f}, b={bbox['b']:.2f}")
                else:
                    print(f"  BBox: None")

        # Verdict
        print("\n" + "=" * 80)
        print("VERDICT")
        print("=" * 80)

        if total_items > 0 and items_with_bbox / total_items >= 0.8:
            print("SUCCESS: Bounding boxes extracted properly")
            print(f"  Coverage: {items_with_bbox/total_items*100:.1f}%")
            print(f"  GPU Used: {result['metadata'].get('device', 'unknown') == 'cuda'}")
            return 0
        elif total_items > 0:
            print(f"PARTIAL: Only {items_with_bbox/total_items*100:.1f}% coverage")
            return 1
        else:
            print("FAILED: No items found")
            return 2

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
