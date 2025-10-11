"""
Simple Docling bounding box extraction test.
Tests whether Docling can extract bounding boxes from PDF documents.
"""

import sys
import os
import json
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 80)
    print("🔬 Testing Docling Bounding Box Extraction")
    print("=" * 80)

    # Import Docling
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
        from docling.datamodel.base_models import InputFormat
        print("\n✅ Docling imported successfully")
    except ImportError as e:
        print(f"\n❌ Docling import failed: {e}")
        return

    # Create a test PDF
    print("\n📄 Creating test PDF...")
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
    pdf_content = buffer.getvalue()
    print(f"✅ Created test PDF ({len(pdf_content):,} bytes)")

    # Parse with Docling
    print("\n🔍 Parsing PDF with Docling...")
    import tempfile

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        tmp_file.write(pdf_content)
        tmp_path = tmp_file.name

    try:
        result = converter.convert(tmp_path)
        doc = result.document
        print(f"✅ Conversion complete! Pages: {len(doc.pages)}")

        # Check document structure
        print(f"\n📚 Document type: {type(doc).__name__}")
        print(f"📚 Has 'iterate_items': {hasattr(doc, 'iterate_items')}")
        print(f"📚 Has 'body': {hasattr(doc, 'body')}")

        # Export as text/markdown
        if hasattr(doc, 'export_to_markdown'):
            md = doc.export_to_markdown()
            print(f"📝 Markdown export: {len(md)} chars")
            print(f"📝 Preview: {md[:150]}...")

        # Try to iterate items
        total = 0
        with_bbox = 0
        examples = []

        if hasattr(doc, 'iterate_items'):
            print("\n🔍 Iterating through doc.iterate_items()...")
            for item in doc.iterate_items():
                total += 1

                # Items are tuples - inspect them
                if total <= 3:
                    print(f"\n  Item {total}:")
                    print(f"    Type: {type(item)}")
                    if isinstance(item, tuple):
                        print(f"    Tuple length: {len(item)}")
                        for i, element in enumerate(item):
                            print(f"    Element {i}: {type(element).__name__}")
                            if hasattr(element, 'text'):
                                print(f"      text: {str(element.text)[:50]}")
                            if hasattr(element, 'label'):
                                print(f"      label: {element.label}")
                            if hasattr(element, 'prov'):
                                prov = element.prov
                                if prov and len(prov) > 0:
                                    bbox = getattr(prov[0], 'bbox', None)
                                    if bbox:
                                        print(f"      HAS BBOX: l={bbox.l:.2f}, t={bbox.t:.2f}")

                # Try to extract from tuple
                if isinstance(item, tuple) and len(item) >= 2:
                    # Tuple is (TextItem/ListItem/etc, int)
                    obj = item[0]  # First element is the content object
                    text_val = getattr(obj, 'text', '')
                    prov = getattr(obj, 'prov', None)

                    bbox = None
                    if prov and len(prov) > 0:
                        bbox = getattr(prov[0], 'bbox', None)

                    if bbox:
                        with_bbox += 1
                        if len(examples) < 3:
                            examples.append({
                                "type": obj.__class__.__name__,
                                "text": text_val[:50] if text_val else "",
                                "bbox": {
                                    "l": getattr(bbox, 'l', None),
                                    "t": getattr(bbox, 't', None),
                                    "r": getattr(bbox, 'r', None),
                                    "b": getattr(bbox, 'b', None)
                                }
                            })
                else:
                    # Not a tuple, try direct access
                    text_val = getattr(item, 'text', '')
                    prov = getattr(item, 'prov', None)

                    bbox = None
                    if prov and len(prov) > 0:
                        bbox = getattr(prov[0], 'bbox', None)

                    if bbox:
                        with_bbox += 1

        # Summary
        print("\n" + "=" * 80)
        print("📊 RESULTS")
        print("=" * 80)
        print(f"Total items: {total}")
        print(f"Items with bboxes: {with_bbox}")
        if total > 0:
            print(f"Coverage: {with_bbox/total*100:.1f}%")

        if examples:
            print("\n📦 Example Bounding Boxes:")
            for i, ex in enumerate(examples, 1):
                print(f"\n  Example {i}:")
                print(f"  Type: {ex['type']}")
                print(f"  Text: {ex['text']}")
                print(f"  BBox: {json.dumps(ex['bbox'], indent=4)}")

        # Verdict
        print("\n" + "=" * 80)
        print("🎯 VERDICT")
        print("=" * 80)
        if total > 0 and with_bbox / total >= 0.8:
            print("✅ DOCLING CAN EXTRACT BOUNDING BOXES")
            print(f"   Coverage: {with_bbox/total*100:.1f}%")
            print("   ✅ Proceed with Docling-based implementation")
        elif total > 0:
            print(f"⚠️  PARTIAL BBOX SUPPORT ({with_bbox/total*100:.1f}% coverage)")
            print("   Consider alternatives or VLM enhancement")
        else:
            print("❌ NO ITEMS FOUND")
            print("   May need different iteration method or alternative parser")

    finally:
        import os
        try:
            os.unlink(tmp_path)
        except:
            pass


if __name__ == "__main__":
    main()
