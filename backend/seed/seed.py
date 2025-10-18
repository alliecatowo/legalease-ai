"""
Simplified database seeding script for LegalEase.

Seeds the database with 3 demo cases containing real legal PDFs:
- Supreme Court opinion (downloaded)
- NDA template (generated)
- Service agreement (generated)

Each document is:
1. Uploaded to MinIO storage
2. Processed through DocumentProcessor pipeline (Docling, embeddings, chunking)
3. Indexed in Qdrant with dense and sparse vectors
4. Stored in PostgreSQL

Usage:
    python -m backend.seed.seed           # Seed database
    python -m backend.seed.seed --clear-db  # Clear and reseed
"""

import sys
import os
import argparse
import io
from pathlib import Path
from datetime import datetime, UTC

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.case import Case
from app.models.chunk import Chunk
from app.workers.pipelines.document_pipeline import DocumentProcessor
from app.core.minio_client import minio_client
from app.services.page_image_service import PageImageService
from app.core.qdrant import get_qdrant_client, create_collection
from app.core.config import settings
import requests


# Demo documents to seed
DEMO_DOCS = {
    "supreme_court_opinion.pdf": {
        "url": "https://www.supremecourt.gov/opinions/24pdf/23-1275_e2pg.pdf",
        "description": "Supreme Court Opinion - Medina v. Planned Parenthood (2024)",
        "case": "Medina v. Planned Parenthood South Atlantic",
        "type": "Court Opinion",
    },
    "nda_template.pdf": {
        "description": "Non-Disclosure Agreement Template",
        "case": "Acme Corp v. Global Tech Inc",
        "type": "NDA",
        "content": """NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into as of [DATE] ("Effective Date"),
by and between [COMPANY NAME] ("Disclosing Party") and [RECIPIENT NAME] ("Receiving Party").

1. DEFINITION OF CONFIDENTIAL INFORMATION

For purposes of this Agreement, "Confidential Information" shall include all information or
material that has or could have commercial value or other utility in the business in which
Disclosing Party is engaged.

2. OBLIGATIONS OF RECEIVING PARTY

Receiving Party shall hold and maintain the Confidential Information in strictest confidence
for the sole and exclusive benefit of the Disclosing Party. Receiving Party shall carefully
restrict access to Confidential Information to employees, contractors and third parties as is
reasonably required.

3. EXCLUSIONS FROM CONFIDENTIAL INFORMATION

Receiving Party's obligations under this Agreement do not extend to information that is:
(a) Publicly known at the time of disclosure
(b) Discovered or created by the Receiving Party before disclosure
(c) Learned through legitimate means other than from the Disclosing Party

4. TERM

The obligations of Receiving Party hereunder shall survive until such time as all
Confidential Information disclosed hereunder becomes publicly known.

5. GOVERNING LAW

This Agreement shall be governed by and construed in accordance with the laws of the State
of California, without regard to conflicts of laws principles."""
    },
    "service_agreement.pdf": {
        "description": "Professional Services Agreement",
        "case": "Tech Consulting Services LLC",
        "type": "Service Agreement",
        "content": """PROFESSIONAL SERVICES AGREEMENT

This Professional Services Agreement ("Agreement") is made effective as of [DATE], between
[CLIENT NAME] ("Client") and [PROVIDER NAME] ("Provider").

1. SERVICES

Provider agrees to provide the following services ("Services"):
- Software development and engineering services
- System architecture and design consulting
- Technical documentation and training

2. COMPENSATION

Client shall pay Provider for Services rendered at the following rates:
- Senior Software Engineer: $200 per hour
- Software Engineer: $150 per hour
- Technical Writer: $100 per hour

3. TERM AND TERMINATION

This Agreement shall commence on the Effective Date and continue until terminated by either
party with thirty (30) days' written notice.

4. INTELLECTUAL PROPERTY

All work product created by Provider shall be considered "work made for hire" under copyright
law. Provider retains ownership of pre-existing intellectual property.

5. CONFIDENTIALITY

Both parties agree to hold confidential information in strict confidence and not disclose it
to third parties.

6. GOVERNING LAW

This Agreement shall be governed by the laws of the State of California."""
    }
}


def create_pdf_from_text(text: str) -> bytes:
    """Generate a simple PDF from text content."""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    for para in text.split('\n\n'):
        if para.strip():
            style = styles['Heading1'] if para.isupper() and len(para) < 100 else styles['BodyText']
            story.append(Paragraph(para.replace('\n', '<br/>'), style))
            story.append(Spacer(1, 0.2 * inch))

    doc.build(story)
    return buffer.getvalue()


def clear_database(db):
    """Clear all database and Qdrant data."""
    print("Clearing database...\n")

    db.query(Chunk).delete()
    db.query(Document).delete()
    db.query(Case).delete()

    # Clear Qdrant collection
    try:
        qdrant = get_qdrant_client()
        qdrant.delete_collection(settings.QDRANT_COLLECTION)
        print(f"Deleted Qdrant collection: {settings.QDRANT_COLLECTION}")
    except Exception as e:
        print(f"Qdrant deletion warning: {e}")

    db.commit()
    print("Database cleared\n")


def process_document(db, case: Case, filename: str, doc_info: dict, processor: DocumentProcessor) -> bool:
    """Process a single document through the pipeline."""
    print(f"\nProcessing: {filename}")
    print(f"  Case: {doc_info['case']}")

    # Get PDF content
    if doc_info.get("url"):
        print("  Downloading from URL...")
        response = requests.get(doc_info["url"], timeout=30)
        response.raise_for_status()
        pdf_content = response.content
    elif doc_info.get("content"):
        print("  Generating PDF...")
        pdf_content = create_pdf_from_text(doc_info["content"])
    else:
        print("  No content source, skipping")
        return False

    # Create document record
    # Note: case.id is now a UUID, and case.gid is used for storage paths
    doc = Document(
        case_id=case.id,  # UUID foreign key
        filename=filename,
        file_path="",  # Will be set after flush to get gid
        mime_type="application/pdf",
        size=len(pdf_content),
        status=DocumentStatus.PENDING,
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)
    db.flush()  # Flush to generate UUID and gid

    # Now set file_path using gids
    file_path = f"cases/{case.gid}/{doc.gid}_{filename}"
    doc.file_path = file_path

    # Upload to MinIO
    print("  Uploading to MinIO...")
    minio_client.upload_file(
        io.BytesIO(pdf_content),
        file_path,
        content_type="application/pdf",
        length=len(pdf_content),
    )

    # Process through pipeline
    print("  Processing through DocumentProcessor...")
    result = processor.process(
        file_content=pdf_content,
        filename=filename,
        document_id=doc.id,
        case_id=case.id,
        mime_type="application/pdf",
    )

    if not result.success:
        doc.status = DocumentStatus.FAILED
        db.commit()
        print(f"  Failed: {result.error}")
        return False

    # Save chunks to database
    print("  Saving chunks...")
    qdrant = get_qdrant_client()
    # Filter by document_id (UUID string) since document_gid may be null during indexing
    scroll_result = qdrant.scroll(
        collection_name=settings.QDRANT_COLLECTION,
        scroll_filter={"must": [{"key": "document_id", "match": {"value": str(doc.id)}}]},
        limit=1000,
        with_payload=True,
        with_vectors=False,
    )

    for point in scroll_result[0]:
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
    db.flush()

    # Generate page images
    print("  Generating page images...")
    try:
        page_image_service = PageImageService()
        image_count = page_image_service.generate_page_images(
            document_gid=doc.gid,
            case_gid=case.gid,
            pdf_content=pdf_content
        )
        print(f"  Generated {image_count} page images")
    except Exception as e:
        print(f"  Image generation warning: {e}")

    # Update status
    doc.status = DocumentStatus.COMPLETED
    db.commit()

    print(f"  Success! {result.data.get('chunks_count', 0)} chunks, {result.data.get('pages_count', 0)} pages")
    return True


def main():
    """Seed database with demo legal documents."""
    parser = argparse.ArgumentParser(description="Seed LegalEase database")
    parser.add_argument("--clear-db", action="store_true", help="Clear database before seeding")
    args = parser.parse_args()

    print("Seeding LegalEase database...\n")

    db = SessionLocal()

    try:
        # Clear if requested
        if args.clear_db:
            clear_database(db)

        # Ensure Qdrant collection exists
        print("Ensuring Qdrant collection exists...")
        create_collection(
            summary_vector_size=384,
            section_vector_size=384,
            microblock_vector_size=384,
            recreate=False,
        )

        # Initialize processor
        processor = DocumentProcessor(
            embedding_model="BAAI/bge-small-en-v1.5",
            use_bm25=True,
            use_ocr=True,
        )
        print("Initialized DocumentProcessor\n")

        # Create cases
        cases = {}
        for doc_info in DEMO_DOCS.values():
            case_name = doc_info["case"]
            if case_name not in cases:
                case = db.query(Case).filter(Case.name == case_name).first()
                if not case:
                    case = Case(
                        name=case_name,
                        case_number=f"CASE-{len(cases) + 1:03d}",
                        client=case_name.split(" v. ")[0] if " v. " in case_name else case_name,
                        status="ACTIVE",
                        matter_type=doc_info["type"],
                        created_at=datetime.now(UTC),
                    )
                    db.add(case)
                    db.flush()
                    print(f"Created case: {case_name} ({case.case_number})")
                cases[case_name] = case
        db.commit()

        # Process documents
        success_count = 0
        for filename, doc_info in DEMO_DOCS.items():
            case = cases[doc_info["case"]]
            try:
                if process_document(db, case, filename, doc_info, processor):
                    success_count += 1
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                db.rollback()

        print(f"\n{'='*70}")
        print(f"Seeding complete!")
        print(f"  Processed: {success_count}/{len(DEMO_DOCS)} documents")
        print(f"  Cases: {len(cases)}")
        print(f"\nTest the API:")
        print(f"  curl 'http://localhost:8000/api/v1/search?q=agreement&limit=5'")

    except Exception as e:
        print(f"\nError: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
