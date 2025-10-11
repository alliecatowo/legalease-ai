"""
Seed database with real PDF legal documents and process through DocumentProcessor pipeline.

This script:
1. Downloads real PDF legal documents from public sources
2. Creates database records with correct Document model fields
3. Uploads PDFs to MinIO storage
4. Processes through complete DocumentProcessor pipeline:
   - Docling parsing (OCR, tables, images, structure)
   - Hierarchical chunking (summary, section, microblock)
   - FastEmbed dense embeddings (BAAI/bge-small-en-v1.5)
   - BM25 sparse vectors for keyword matching
   - Qdrant indexing with named vectors
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.case import Case
from app.workers.pipelines.document_pipeline import DocumentProcessor
from app.core.minio_client import minio_client
from app.services.page_image_service import PageImageService
from datetime import datetime, UTC
import io
import requests

# Real legal documents to download (public domain / free legal resources)
SAMPLE_DOCUMENTS = {
    "supreme_court_opinion_2024.pdf": {
        "url": "https://www.supremecourt.gov/opinions/24pdf/23-1275_e2pg.pdf",
        "description": "Supreme Court Opinion - Medina v. Planned Parenthood (2024)",
        "case": "Medina v. Planned Parenthood South Atlantic",
        "type": "Court Opinion",
    },
    "nda_template.pdf": {
        "url": None,  # Will create from text
        "description": "Non-Disclosure Agreement Template",
        "case": "Acme Corp v. Global Tech Inc",
        "type": "NDA",
        "content": """
NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into as of [DATE] ("Effective Date"),
by and between [COMPANY NAME] ("Disclosing Party") and [RECIPIENT NAME] ("Receiving Party").

1. DEFINITION OF CONFIDENTIAL INFORMATION

For purposes of this Agreement, "Confidential Information" shall include all information or
material that has or could have commercial value or other utility in the business in which
Disclosing Party is engaged. Confidential Information also includes all information of which
unauthorized disclosure could be detrimental to the interests of Disclosing Party, whether or
not such information is identified as Confidential Information by Disclosing Party.

By way of example, and without limitation, Confidential Information includes: (a) any and all
information concerning Disclosing Party's products, business and operations including
information relating to product sales, costs, profits and markets, and information relating
to Disclosing Party's business plans, activities and strategies; (b) plans, designs, drawings,
databases, source code, documentation, engineering information, hardware configuration
information, and test results; (c) information about customers, suppliers, and business
partners; and (d) proprietary or confidential information of any third party who may disclose
such information to Disclosing Party or Receiving Party in the course of Disclosing Party's
business.

2. OBLIGATIONS OF RECEIVING PARTY

Receiving Party shall hold and maintain the Confidential Information in strictest confidence
for the sole and exclusive benefit of the Disclosing Party. Receiving Party shall carefully
restrict access to Confidential Information to employees, contractors and third parties as is
reasonably required and shall require those persons to sign nondisclosure restrictions at
least as protective as those in this Agreement.

Receiving Party shall not, without prior written approval of Disclosing Party:
(a) Disclose any Confidential Information to any third party
(b) Use any Confidential Information for any purpose except as contemplated by this Agreement
(c) Copy or reproduce any Confidential Information

3. EXCLUSIONS FROM CONFIDENTIAL INFORMATION

Receiving Party's obligations under this Agreement do not extend to information that is:
(a) Publicly known at the time of disclosure or subsequently becomes publicly known through
    no fault of the Receiving Party
(b) Discovered or created by the Receiving Party before disclosure by Disclosing Party
(c) Learned by the Receiving Party through legitimate means other than from the Disclosing
    Party or Disclosing Party's representatives
(d) Disclosed by Receiving Party with Disclosing Party's prior written approval

4. TERM

The obligations of Receiving Party hereunder shall survive until such time as all
Confidential Information disclosed hereunder becomes publicly known and made generally
available through no action or inaction of Receiving Party.

5. RETURN OF MATERIALS

All documents and other tangible objects containing or representing Confidential Information
and all copies thereof which are in the possession of Receiving Party shall be and remain
the property of Disclosing Party and shall be promptly returned to Disclosing Party upon
Disclosing Party's request.

6. NO LICENSE

Nothing in this Agreement is intended to grant any rights to Receiving Party under any
patent, trademark, copyright or other intellectual property right, nor shall this Agreement
grant Receiving Party any rights in or to the Confidential Information except as expressly
set forth herein.

7. REMEDIES

Receiving Party agrees that any violation or threatened violation of this Agreement may
cause irreparable injury to Disclosing Party, entitling Disclosing Party to seek injunctive
relief in addition to all legal remedies.

8. GOVERNING LAW

This Agreement shall be governed by and construed in accordance with the laws of the State
of California, without regard to conflicts of laws principles.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the Effective Date.

DISCLOSING PARTY: _______________________

RECEIVING PARTY: _______________________
        """.strip()
    },
    "service_agreement_sample.pdf": {
        "url": None,
        "description": "Professional Services Agreement",
        "case": "Tech Consulting Services LLC",
        "type": "Service Agreement",
        "content": """
PROFESSIONAL SERVICES AGREEMENT

This Professional Services Agreement ("Agreement") is made effective as of [DATE], between
[CLIENT NAME] ("Client") and [PROVIDER NAME] ("Provider").

1. SERVICES

Provider agrees to provide the following services ("Services"):
- Software development and engineering services
- System architecture and design consulting
- Technical documentation and training
- Code review and quality assurance

The specific scope of Services for each engagement will be outlined in a Statement of Work
("SOW") executed by both parties. Each SOW will reference this Agreement and shall be
incorporated herein by reference.

2. COMPENSATION

Client shall pay Provider for Services rendered at the following rates:
- Senior Software Engineer: $200 per hour
- Software Engineer: $150 per hour
- Technical Writer: $100 per hour

Invoices will be submitted monthly and are due within thirty (30) days of receipt. Late
payments shall accrue interest at the rate of 1.5% per month or the maximum amount allowed
by law, whichever is less.

3. EXPENSES

Client shall reimburse Provider for all pre-approved, reasonable out-of-pocket expenses
incurred in connection with the performance of Services, including but not limited to:
travel, lodging, meals, and materials. Provider shall submit expense reports with
supporting documentation.

4. TERM AND TERMINATION

This Agreement shall commence on the Effective Date and continue until terminated by either
party. Either party may terminate this Agreement:
(a) For convenience with thirty (30) days' written notice
(b) For cause immediately if the other party materially breaches this Agreement

Upon termination, Client shall pay Provider for all Services performed through the date of
termination and all expenses incurred.

5. INTELLECTUAL PROPERTY

All work product created by Provider in the course of performing Services ("Work Product")
shall be considered "work made for hire" under copyright law. To the extent any Work Product
does not qualify as work made for hire, Provider hereby assigns to Client all right, title,
and interest in and to such Work Product, including all intellectual property rights therein.

Provider retains ownership of: (a) pre-existing intellectual property, (b) general skills
and knowledge, and (c) methodologies and processes developed independent of this engagement.

6. CONFIDENTIALITY

Both parties acknowledge that they may have access to certain confidential information of the
other party. Each party agrees to hold such confidential information in strict confidence and
not to disclose it to third parties or use it for any purpose other than performance under
this Agreement.

7. WARRANTIES

Provider warrants that:
(a) Services will be performed in a professional and workmanlike manner consistent with
    industry standards
(b) Provider has the necessary skills, qualifications, and resources to perform Services
(c) Work Product will not infringe upon the intellectual property rights of any third party

8. LIMITATION OF LIABILITY

Provider's total liability arising out of or related to this Agreement shall not exceed the
total amount paid by Client to Provider in the twelve (12) months preceding the claim. In
no event shall either party be liable for indirect, incidental, consequential, special, or
punitive damages.

9. INDEPENDENT CONTRACTOR

Provider is an independent contractor and not an employee of Client. Provider is responsible
for all taxes, insurance, and benefits. Provider may engage subcontractors with Client's
prior written consent.

10. GOVERNING LAW

This Agreement shall be governed by the laws of the State of California.

IN WITNESS WHEREOF, the parties have executed this Agreement.

CLIENT: _______________________

PROVIDER: _______________________
        """.strip()
    },
}


def create_pdf_from_text(text: str) -> bytes:
    """
    Create a simple PDF from text.
    For production, we would use real PDFs, but this allows testing without external files.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import inch

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Split text into paragraphs
    paragraphs = text.split('\n\n')

    for para in paragraphs:
        if para.strip():
            # Check if it's a title (all caps or short)
            if para.isupper() and len(para) < 100:
                p = Paragraph(para, styles['Heading1'])
            else:
                p = Paragraph(para.replace('\n', '<br/>'), styles['BodyText'])
            story.append(p)
            story.append(Spacer(1, 0.2 * inch))

    doc.build(story)
    return buffer.getvalue()


def clear_database(db):
    """Clear all data from the database."""
    from app.models.chunk import Chunk
    from app.models.entity import Entity
    from app.core.qdrant import get_qdrant_client
    from app.core.config import settings

    print("🗑️  Clearing database...\n")

    try:
        # Delete in order to respect foreign key constraints
        print("   Deleting chunks...")
        db.query(Chunk).delete()
        print("   Deleting documents...")
        db.query(Document).delete()
        print("   Deleting cases...")
        db.query(Case).delete()
        print("   Deleting entities...")
        db.query(Entity).delete()

        # Reset Qdrant collection
        try:
            qdrant_client = get_qdrant_client()
            collection_name = settings.QDRANT_COLLECTION
            qdrant_client.delete_collection(collection_name)
            print(f"   ✅ Deleted Qdrant collection: {collection_name}")
        except Exception as e:
            print(f"   ⚠️  Qdrant collection deletion: {e}")

        db.commit()
        print("   ✅ Database cleared\n")
    except Exception as e:
        print(f"   ❌ Error clearing database: {e}\n")
        db.rollback()
        raise


def main():
    """Seed database with real PDF documents and process through pipeline."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Seed database with legal documents")
    parser.add_argument(
        "--clear-db",
        action="store_true",
        help="Clear the database before seeding"
    )
    args = parser.parse_args()

    print("🌱 Seeding database with real PDF legal documents...\n")

    db = SessionLocal()

    # Clear database if requested
    if args.clear_db:
        clear_database(db)
    try:
        # Ensure Qdrant collection exists (create if needed after clear)
        from app.core.qdrant import create_collection
        print("📊 Ensuring Qdrant collection exists...")
        create_collection(
            summary_vector_size=384,  # BAAI/bge-small-en-v1.5 embedding size
            section_vector_size=384,
            microblock_vector_size=384,
            recreate=False,  # Don't recreate if already exists
        )
        print("✅ Qdrant collection ready\n")

        # Initialize DocumentProcessor pipeline
        processor = DocumentProcessor(
            embedding_model="BAAI/bge-small-en-v1.5",
            use_bm25=True,
            use_ocr=True,
        )

        print("✅ Initialized MinIO and DocumentProcessor pipeline\n")

        # Get or create cases
        cases_dict = {}
        existing_case_count = db.query(Case).count()

        for doc_info in SAMPLE_DOCUMENTS.values():
            case_name = doc_info["case"]
            if case_name not in cases_dict:
                case = db.query(Case).filter(Case.name == case_name).first()
                if not case:
                    # Use a unique case number based on existing cases
                    case_number = f"CASE-{existing_case_count + len(cases_dict) + 1:03d}"
                    case = Case(
                        name=case_name,
                        case_number=case_number,
                        client=case_name.split(" v. ")[0] if " v. " in case_name else case_name,
                        status="ACTIVE",
                        matter_type=doc_info["type"],
                        created_at=datetime.now(UTC),
                    )
                    db.add(case)
                    db.flush()
                    print(f"📁 Created case: {case_name} (ID: {case.id}, Number: {case_number})")
                else:
                    print(f"📁 Found existing case: {case_name} (ID: {case.id})")
                cases_dict[case_name] = case

        db.commit()

        # Process each document
        total_processed = 0
        total_failed = 0

        for filename, doc_info in SAMPLE_DOCUMENTS.items():
            print(f"\n{'='*80}")
            print(f"📄 Processing: {filename}")
            print(f"   Description: {doc_info['description']}")
            print(f"   Case: {doc_info['case']}")

            try:
                # Get PDF content
                if doc_info.get("url"):
                    print(f"   📥 Downloading from URL...")
                    response = requests.get(doc_info["url"], timeout=30)
                    response.raise_for_status()
                    pdf_content = response.content
                elif doc_info.get("content"):
                    print(f"   📝 Generating PDF from text...")
                    pdf_content = create_pdf_from_text(doc_info["content"])
                else:
                    print(f"   ⚠️  No content source, skipping")
                    continue

                # Create database record
                case = cases_dict[doc_info["case"]]
                file_path = f"documents/{case.id}/{filename}"

                doc = Document(
                    case_id=case.id,
                    filename=filename,
                    file_path=file_path,
                    mime_type="application/pdf",
                    size=len(pdf_content),
                    status=DocumentStatus.PENDING,
                    uploaded_at=datetime.now(UTC),
                )
                db.add(doc)
                db.flush()

                print(f"   ✅ Created DB record (ID: {doc.id})")

                # Upload to MinIO
                print(f"   ☁️  Uploading to MinIO...")
                minio_client.upload_file(
                    io.BytesIO(pdf_content),
                    file_path,
                    content_type="application/pdf",
                    length=len(pdf_content),
                )
                print(f"   ✅ Uploaded to MinIO: {file_path}")

                # Process through DocumentProcessor pipeline
                print(f"   🔄 Processing through DocumentProcessor pipeline...")
                result = processor.process(
                    file_content=pdf_content,
                    filename=filename,
                    document_id=doc.id,
                    case_id=case.id,
                    mime_type="application/pdf",
                )

                if result.success:
                    # Save chunks to database (DocumentProcessor only indexes to Qdrant)
                    print(f"   💾 Saving chunks to database...")
                    from app.models.chunk import Chunk
                    from app.core.qdrant import get_qdrant_client
                    from app.core.config import settings

                    # Fetch chunks from Qdrant to save to database
                    qdrant_client = get_qdrant_client()
                    collection_name = settings.QDRANT_COLLECTION

                    # Scroll through all points for this document
                    scroll_result = qdrant_client.scroll(
                        collection_name=collection_name,
                        scroll_filter={
                            "must": [
                                {"key": "document_id", "match": {"value": doc.id}}
                            ]
                        },
                        limit=1000,
                        with_payload=True,
                        with_vectors=False,
                    )

                    points = scroll_result[0]
                    chunks_saved = 0

                    for point in points:
                        payload = point.payload
                        chunk = Chunk(
                            document_id=doc.id,
                            text=payload.get("text", ""),
                            chunk_type=payload.get("chunk_type", "section"),
                            position=payload.get("position", 0),
                            page_number=payload.get("page_number"),
                            meta_data={
                                "bboxes": payload.get("bboxes", []),
                                **payload.get("metadata", {}),
                            },
                        )
                        db.add(chunk)
                        chunks_saved += 1

                    db.flush()
                    print(f"   ✅ Saved {chunks_saved} chunks to database")
                    # Generate page images for PDF documents
                    print(f"   🖼️  Generating page images...")
                    try:
                        page_image_service = PageImageService()
                        image_count = page_image_service.generate_page_images(
                            document_id=doc.id,
                            case_id=case.id,
                            pdf_content=pdf_content
                        )
                        print(f"   ✅ Generated {image_count} page images")
                    except Exception as e:
                        print(f"   ⚠️  Page image generation failed: {e}")
                        # Don't fail the entire process if image generation fails

                    # Update document status
                    doc.status = DocumentStatus.COMPLETED
                    db.commit()

                    print(f"   ✅ Processing complete!")
                    print(f"      - Chunks created: {result.data.get('chunks_count', 0)}")
                    print(f"      - Text length: {result.data.get('text_length', 0)} chars")
                    print(f"      - Pages: {result.data.get('pages_count', 0)}")

                    total_processed += 1
                else:
                    doc.status = DocumentStatus.FAILED
                    db.commit()
                    print(f"   ❌ Processing failed: {result.error}")
                    total_failed += 1

            except Exception as e:
                print(f"   ❌ Error processing document: {e}")
                if 'doc' in locals():
                    doc.status = DocumentStatus.FAILED
                    db.commit()
                total_failed += 1
                import traceback
                traceback.print_exc()

        # Summary
        print(f"\n{'='*80}")
        print(f"\n✨ Processing Complete!")
        print(f"   Successfully processed: {total_processed}/{len(SAMPLE_DOCUMENTS)}")
        print(f"   Failed: {total_failed}/{len(SAMPLE_DOCUMENTS)}")
        print(f"\n📊 Cases created: {len(cases_dict)}")
        print(f"\n✅ Documents are now indexed in Qdrant with:")
        print(f"   - Dense embeddings via FastEmbed (BAAI/bge-small-en-v1.5)")
        print(f"   - Sparse vectors (BM25) for keyword matching")
        print(f"   - Parsed with Docling (GPU-accelerated, OCR, bounding boxes)")
        print(f"   - Hierarchical chunking (summary, section, microblock)")
        print(f"   - Bounding boxes preserved in chunk metadata")
        print(f"   - Page images generated and stored in MinIO")
        print(f"\n🔍 Test the APIs:")
        print(f"   Search: curl 'http://localhost:8000/api/v1/search?q=agreement&limit=5'")
        print(f"   Content: curl 'http://localhost:8000/api/v1/documents/1/content?include_images=true'")
        print(f"   Page Image: curl 'http://localhost:8000/api/v1/documents/1/pages/1'")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
