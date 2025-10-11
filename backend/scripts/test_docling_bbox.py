"""
Deep investigation: Test Docling's bounding box extraction capabilities.

This script tests whether Docling can reliably extract bounding boxes from documents.
We'll test on multiple document types and compare output structure.
"""

import sys
import os
from pathlib import Path
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from io import BytesIO


def test_docling_bbox_extraction():
    """Test Docling's actual bounding box extraction capabilities."""
    print("=" * 80)
    print("🔬 DEEP INVESTIGATION: Docling Bounding Box Extraction")
    print("=" * 80)

    # Test 1: Check if Docling is properly installed
    print("\n📦 Test 1: Checking Docling installation...")
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
        from docling.datamodel.base_models import InputFormat
        print("   ✅ Docling imports successful")
    except ImportError as e:
        print(f"   ❌ Docling import failed: {e}")
        print("   💡 Installing docling...")
        import subprocess
        subprocess.run(["uv", "add", "docling"], check=True)
        return

    # Test 2: Create a test PDF document
    print("\n📄 Test 2: Creating test PDF document...")
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import inch

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        test_text = """
NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into as of January 1, 2024.

1. DEFINITION OF CONFIDENTIAL INFORMATION

For purposes of this Agreement, "Confidential Information" shall include all information
or material that has or could have commercial value or other utility in the business in
which Disclosing Party is engaged. Confidential Information also includes all information
of which unauthorized disclosure could be detrimental to the interests of Disclosing Party.

By way of example, and without limitation, Confidential Information includes: (a) any and
all information concerning Disclosing Party's products, business and operations including
information relating to product sales, costs, profits and markets.

2. OBLIGATIONS OF RECEIVING PARTY

Receiving Party shall hold and maintain the Confidential Information in strictest confidence
for the sole and exclusive benefit of the Disclosing Party. Receiving Party shall carefully
restrict access to Confidential Information to employees, contractors and third parties as
is reasonably required.

Receiving Party shall not, without prior written approval of Disclosing Party:
(a) Disclose any Confidential Information to any third party
(b) Use any Confidential Information for any purpose except as contemplated by this Agreement
(c) Copy or reproduce any Confidential Information

3. TERM

The obligations of Receiving Party hereunder shall survive until such time as all
Confidential Information disclosed hereunder becomes publicly known and made generally
available through no action or inaction of Receiving Party.
        """.strip()

        for para in test_text.split('\n\n'):
            if para.strip():
                if para.isupper() and len(para) < 100:
                    p = Paragraph(para, styles['Heading1'])
                else:
                    p = Paragraph(para.replace('\n', '<br/>'), styles['BodyText'])
                story.append(p)
                story.append(Spacer(1, 0.2 * inch))

        doc.build(story)
        pdf_content = buffer.getvalue()
        print(f"   ✅ Created test PDF ({len(pdf_content):,} bytes)")

    except Exception as e:
        print(f"   ❌ Failed to create test PDF: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 3: Parse with Docling and extract bounding boxes
    print("\n🔍 Test 3: Parsing with Docling DocumentConverter...")
    try:
        import tempfile

        # Configure pipeline options
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True

        # Configure OCR options
        ocr_options = EasyOcrOptions(force_full_page_ocr=False)
        pipeline_options.ocr_options = ocr_options

        # Create document converter
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        # Write to temporary file (Docling needs file path)
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            tmp_path = tmp_file.name

        print(f"   📂 Temporary file: {tmp_path}")
        print("   ⏳ Converting document (this may take 10-30 seconds)...")

        try:
            # Convert document
            result = converter.convert(tmp_path)
            doc = result.document

            print(f"   ✅ Conversion complete!")
            print(f"   📄 Pages: {len(doc.pages)}")

            # Test 4: Inspect the document structure
            print("\n🔎 Test 4: Inspecting Docling output structure...")
            print(f"   📚 Document type: {type(doc)}")
            print(f"   📚 Document attributes: {dir(doc)[:10]}...")

            # Try to get the document as markdown/text
            if hasattr(doc, 'export_to_markdown'):
                md_text = doc.export_to_markdown()
                print(f"   📝 Markdown export length: {len(md_text)} chars")
                print(f"   📝 Markdown preview: {md_text[:200]}...")

            if hasattr(doc, 'export_to_text'):
                text = doc.export_to_text()
                print(f"   📝 Text export length: {len(text)} chars")

            # Check for main_text and body content
            if hasattr(doc, 'main_text'):
                print(f"\n   📝 Main text length: {len(doc.main_text) if doc.main_text else 0}")

            # Look for body/content
            if hasattr(doc, 'body'):
                print(f"   📚 Body type: {type(doc.body)}")
                print(f"   📚 Body dir: {[a for a in dir(doc.body) if not a.startswith('_')][:20]}")

            # Try to iterate through document items
            total_items = 0
            items_with_bbox = 0
            items_with_text = 0
            bbox_examples = []

            # Method 1: Try doc.iterate_items()
            if hasattr(doc, 'iterate_items'):
                print("\n   🔍 Method 1: Using doc.iterate_items()...")
                for item in doc.iterate_items():
                    total_items += 1

                    # Check for text
                    text = getattr(item, 'text', None)
                    if text:
                        items_with_text += 1

                    # Check for bbox
                    prov = getattr(item, 'prov', None)
                    if prov:
                        bbox = getattr(prov[0] if prov else None, 'bbox', None)
                        if bbox:
                            items_with_bbox += 1

                            if len(bbox_examples) < 3:
                                bbox_examples.append({
                                    "page": getattr(prov[0], 'page', 'N/A') if prov else 'N/A',
                                    "item_type": item.__class__.__name__,
                                    "text": text[:50] if text else "",
                                    "bbox": {
                                        "x0": bbox.l if hasattr(bbox, 'l') else None,
                                        "y0": bbox.t if hasattr(bbox, 't') else None,
                                        "x1": bbox.r if hasattr(bbox, 'r') else None,
                                        "y1": bbox.b if hasattr(bbox, 'b') else None,
                                    }
                                })

                    if total_items <= 5:
                        print(f"      Item {total_items}: {item.__class__.__name__}, has_text={bool(text)}, has_bbox={bool(bbox) if prov else False}")

            # Method 2: Try accessing body elements
            elif hasattr(doc, 'body') and hasattr(doc.body, '__iter__'):
                print("\n   🔍 Method 2: Using doc.body iteration...")
                for item in doc.body:
                    if total_items <= 5:
                        print(f"\n   📦 Item {total_items + 1}:")
                        print(f"      - Type: {type(item)}")
                        print(f"      - Attributes: {[a for a in dir(item) if not a.startswith('_')][:10]}")

                    total_items += 1

                    # Check for text
                    has_text = hasattr(item, 'text') and item.text
                        if has_text:
                            items_with_text += 1

                        # Check for bounding box
                        has_bbox = hasattr(item, 'bbox') and item.bbox
                        if has_bbox:
                            items_with_bbox += 1
                            bbox = item.bbox

                            # Store example
                            if len(bbox_examples) < 3:
                                bbox_examples.append({
                                    "page": page_num + 1,
                                    "item_type": item.__class__.__name__,
                                    "text": item.text[:50] if has_text else "",
                                    "bbox": {
                                        "left": bbox.l if hasattr(bbox, 'l') else None,
                                        "top": bbox.t if hasattr(bbox, 't') else None,
                                        "right": bbox.r if hasattr(bbox, 'r') else None,
                                        "bottom": bbox.b if hasattr(bbox, 'b') else None,
                                    }
                                })

                        # Print item details
                        if i == 0:
                            print(f"      - Item type: {item.__class__.__name__}")
                            print(f"      - Has text: {has_text}")
                            print(f"      - Has bbox: {has_bbox}")

                            if has_text:
                                text_preview = item.text[:100].replace('\n', ' ')
                                print(f"      - Text preview: {text_preview}...")

                            if has_bbox:
                                print(f"      - BBox coordinates: l={bbox.l:.2f}, t={bbox.t:.2f}, r={bbox.r:.2f}, b={bbox.b:.2f}")

            # Test 5: Summary and verdict
            print("\n" + "=" * 80)
            print("📊 BOUNDING BOX EXTRACTION SUMMARY")
            print("=" * 80)
            print(f"Total items processed: {total_items}")
            print(f"Items with text: {items_with_text} ({items_with_text/total_items*100:.1f}%)" if total_items > 0 else "")
            print(f"Items with bounding boxes: {items_with_bbox} ({items_with_bbox/total_items*100:.1f}%)" if total_items > 0 else "")

            if bbox_examples:
                print("\n📦 Example Bounding Boxes:")
                for i, example in enumerate(bbox_examples, 1):
                    print(f"\n   Example {i}:")
                    print(f"   - Page: {example['page']}")
                    print(f"   - Type: {example['item_type']}")
                    print(f"   - Text: {example['text']}...")
                    print(f"   - BBox: {json.dumps(example['bbox'], indent=6)}")

            # Verdict
            print("\n" + "=" * 80)
            print("🎯 VERDICT:")
            print("=" * 80)

            if items_with_bbox >= total_items * 0.8:  # 80%+ coverage
                print("✅ DOCLING IS SUITABLE")
                print(f"   - Bounding box coverage: {items_with_bbox/total_items*100:.1f}%")
                print("   - Recommendation: Use Docling for bbox extraction")
                print("   - Next step: Refactor docling_parser.py to use DocumentConverter")
            elif items_with_bbox >= total_items * 0.5:  # 50-80% coverage
                print("⚠️  DOCLING IS PARTIALLY SUITABLE")
                print(f"   - Bounding box coverage: {items_with_bbox/total_items*100:.1f}%")
                print("   - Recommendation: Test on more documents or consider Surya")
            else:
                print("❌ DOCLING IS INSUFFICIENT")
                print(f"   - Bounding box coverage: {items_with_bbox/total_items*100:.1f}%")
                print("   - Recommendation: Evaluate Surya OCR as alternative")

        finally:
            # Clean up temporary file
            import os
            try:
                os.unlink(tmp_path)
            except:
                pass

    except Exception as e:
        print(f"   ❌ Error during Docling parsing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_docling_bbox_extraction()
