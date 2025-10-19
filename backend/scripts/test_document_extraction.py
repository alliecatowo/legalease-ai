#!/usr/bin/env python3
"""Test document extraction with new Marker parser."""

import sys
import os
import asyncio
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.workers.parsers.factory import ParserFactory
from app.workers.parsers.base import ParserType

async def test_marker_parser():
    """Test Marker parser on a sample PDF."""

    # Find a test PDF
    test_files = list(Path("/home/Allie/develop/legalease/backend").rglob("*.pdf"))

    if not test_files:
        print("❌ No PDF files found for testing")
        return False

    test_file = test_files[0]
    print(f"📄 Testing with: {test_file}")

    # Read file
    with open(test_file, 'rb') as f:
        content = f.read()

    print(f"📊 File size: {len(content)/1024:.1f}KB")

    # Create parser
    parser = ParserFactory.create_parser(
        parser_type=ParserType.MARKER,
        config={"use_llm": False}  # Disable VLM for faster test
    )

    print("🔄 Parsing document...")
    result = parser.parse(content, test_file.name)

    print(f"\n✅ Parsing complete!")
    print(f"   Pages: {result.page_count}")
    print(f"   Pages with content: {result.content_page_count}")
    print(f"   Total chars: {result.total_char_count:,}")
    print(f"   Processing time: {result.processing_time:.2f}s")
    print(f"   Parser: {result.parser_type.value}")

    # Check bboxes
    total_bboxes = sum(len(page.bboxes) for page in result.pages)
    print(f"   Total bboxes: {total_bboxes}")

    if result.pages:
        sample_page = result.pages[0]
        print(f"\n📄 Sample page 1:")
        print(f"   Text length: {len(sample_page.text)}")
        print(f"   Blocks: {len(sample_page.blocks)}")
        print(f"   Bboxes: {len(sample_page.bboxes)}")

        if sample_page.bboxes:
            bbox = sample_page.bboxes[0]
            print(f"   Bbox format: {list(bbox.keys())}")

    return True

if __name__ == "__main__":
    success = asyncio.run(test_marker_parser())
    sys.exit(0 if success else 1)
