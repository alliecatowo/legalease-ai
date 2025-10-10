"""
Seed script to populate the database with test data for development.

Usage:
    python scripts/seed_data.py          # Seed data (skip if exists)
    python scripts/seed_data.py --clear  # Clear all data first, then seed
    python scripts/seed_data.py --force  # Delete existing and re-seed
"""
from datetime import datetime, timedelta
import random
import sys
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models import Case, Document, Transcription, Entity


def clear_all_data(db: Session):
    """Clear all data from the database"""
    print("🗑️  Clearing all data...")

    try:
        # Delete in reverse order of dependencies
        db.execute(text("TRUNCATE entities CASCADE"))
        db.execute(text("TRUNCATE transcriptions CASCADE"))
        db.execute(text("TRUNCATE chunks CASCADE"))
        db.execute(text("TRUNCATE documents CASCADE"))
        db.execute(text("TRUNCATE cases CASCADE"))
        db.commit()
        print("✓ All data cleared")
    except Exception as e:
        print(f"⚠️  Error clearing data: {e}")
        db.rollback()
        raise


def seed_cases(db: Session, skip_existing=True):
    """Create sample cases"""
    cases_data = [
        {
            "name": "Johnson v. TechCorp",
            "case_number": "CASE-2024-001",
            "client": "Sarah Johnson",
            "matter_type": "Employment Discrimination",
            "status": "ACTIVE",
        },
        {
            "name": "Smith v. MediCare Inc.",
            "case_number": "CASE-2024-002",
            "client": "Robert Smith",
            "matter_type": "Medical Malpractice",
            "status": "ACTIVE",
        },
        {
            "name": "Anderson Construction Dispute",
            "case_number": "CASE-2024-003",
            "client": "Anderson Builders LLC",
            "matter_type": "Contract Dispute",
            "status": "STAGING",
        },
        {
            "name": "Thompson Estate Planning",
            "case_number": "CASE-2024-004",
            "client": "Thompson Family Trust",
            "matter_type": "Estate Planning",
            "status": "UNLOADED",
        },
    ]

    cases = []
    created_count = 0
    skipped_count = 0

    for case_data in cases_data:
        # Check if case already exists
        existing_case = db.query(Case).filter_by(case_number=case_data["case_number"]).first()

        if existing_case:
            if skip_existing:
                cases.append(existing_case)
                skipped_count += 1
                continue
            else:
                # Delete existing case and its dependencies
                db.delete(existing_case)
                db.commit()

        case = Case(**case_data)
        db.add(case)
        cases.append(case)
        created_count += 1

    if created_count > 0:
        db.commit()
        for case in cases:
            if case not in db:
                db.refresh(case)

    if created_count > 0:
        print(f"✓ Created {created_count} cases")
    if skipped_count > 0:
        print(f"ℹ️  Skipped {skipped_count} existing cases")

    return cases


def seed_documents(db: Session, cases: list, skip_existing=True):
    """Create sample documents"""
    documents_data = [
        # Johnson v. TechCorp documents
        {
            "case_id": cases[0].id,
            "filename": "employment_agreement.pdf",
            "file_path": f"/uploads/case_{cases[0].id}/employment_agreement.pdf",
            "mime_type": "application/pdf",
            "size": 245000,
            "status": "COMPLETED",
            "meta_data": {
                "title": "Employment Agreement - TechCorp Inc.",
                "document_type": "contract",
                "summary": "Employment agreement outlining terms of employment."
            }
        },
        {
            "case_id": cases[0].id,
            "filename": "termination_letter.pdf",
            "file_path": f"/uploads/case_{cases[0].id}/termination_letter.pdf",
            "mime_type": "application/pdf",
            "size": 52000,
            "status": "COMPLETED",
            "meta_data": {
                "title": "Notice of Termination",
                "summary": "Letter notifying employee of immediate termination."
            }
        },
        {
            "case_id": cases[0].id,
            "filename": "performance_reviews.pdf",
            "file_path": f"/uploads/case_{cases[0].id}/performance_reviews.pdf",
            "mime_type": "application/pdf",
            "size": 189000,
            "status": "COMPLETED",
            "meta_data": {
                "title": "Annual Performance Reviews 2022-2023",
                "summary": "Collection of performance reviews."
            }
        },
        # Smith v. MediCare documents
        {
            "case_id": cases[1].id,
            "filename": "medical_records.pdf",
            "file_path": f"/uploads/case_{cases[1].id}/medical_records.pdf",
            "mime_type": "application/pdf",
            "size": 512000,
            "status": "COMPLETED",
            "meta_data": {
                "title": "Patient Medical Records",
                "summary": "Complete medical records including surgical notes."
            }
        },
        {
            "case_id": cases[1].id,
            "filename": "expert_opinion.pdf",
            "file_path": f"/uploads/case_{cases[1].id}/expert_opinion.pdf",
            "mime_type": "application/pdf",
            "size": 156000,
            "status": "COMPLETED",
            "meta_data": {
                "title": "Medical Expert Opinion - Dr. Williams",
                "summary": "Expert medical testimony regarding standard of care."
            }
        },
        # Anderson Construction documents
        {
            "case_id": cases[2].id,
            "filename": "construction_contract.pdf",
            "file_path": f"/uploads/case_{cases[2].id}/construction_contract.pdf",
            "mime_type": "application/pdf",
            "size": 328000,
            "status": "PROCESSING",
            "meta_data": {
                "title": "Master Construction Agreement",
                "document_type": "contract",
                "summary": "Primary construction contract with timeline and budget."
            }
        },
    ]

    documents = []
    created_count = 0
    skipped_count = 0

    for doc_data in documents_data:
        # Check if document already exists (by case_id and filename)
        existing_doc = db.query(Document).filter_by(
            case_id=doc_data["case_id"],
            filename=doc_data["filename"]
        ).first()

        if existing_doc:
            if skip_existing:
                documents.append(existing_doc)
                skipped_count += 1
                continue
            else:
                # Delete existing document
                db.delete(existing_doc)
                db.commit()

        doc = Document(**doc_data)
        db.add(doc)
        documents.append(doc)
        created_count += 1

    if created_count > 0:
        db.commit()
        for doc in documents:
            if doc not in db:
                db.refresh(doc)

    if created_count > 0:
        print(f"✓ Created {created_count} documents")
    if skipped_count > 0:
        print(f"ℹ️  Skipped {skipped_count} existing documents")

    return documents


def seed_transcriptions(db: Session, cases: list):
    """Create sample transcriptions"""
    transcriptions_data = [
        {
            "case_id": cases[0].id,
            "title": "Deposition - Sarah Johnson",
            "filename": "deposition_johnson.mp3",
            "duration": 5415,  # 1h 30m 15s
            "status": "completed",
            "speaker_count": 3,
            "transcript_text": "Q: Can you state your name for the record? A: Sarah Johnson. Q: And how long were you employed at TechCorp? A: I worked there for 8 years...",
        },
        {
            "case_id": cases[0].id,
            "title": "Client Meeting - Initial Consultation",
            "filename": "client_meeting_01.mp3",
            "duration": 2700,  # 45m
            "status": "completed",
            "speaker_count": 2,
        },
        {
            "case_id": cases[1].id,
            "title": "Deposition - Dr. Martinez",
            "filename": "deposition_martinez.mp3",
            "duration": 7200,  # 2h
            "status": "processing",
            "speaker_count": 4,
        },
    ]

    transcriptions = []
    for trans_data in transcriptions_data:
        days_ago = random.randint(1, 60)
        created_at = datetime.utcnow() - timedelta(days=days_ago)

        trans = Transcription(
            **trans_data,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(trans)
        transcriptions.append(trans)

    db.commit()
    for trans in transcriptions:
        db.refresh(trans)

    print(f"✓ Created {len(transcriptions)} transcriptions")
    return transcriptions


def seed_entities(db: Session, documents: list):
    """Create sample entities extracted from documents"""
    entities_data = [
        # Entities from Johnson case
        {
            "document_id": documents[0].id,
            "entity_type": "PERSON",
            "entity_text": "Sarah Johnson",
            "confidence": 0.98,
            "mentions": 45,
        },
        {
            "document_id": documents[0].id,
            "entity_type": "ORGANIZATION",
            "entity_text": "TechCorp Inc.",
            "confidence": 0.99,
            "mentions": 67,
        },
        {
            "document_id": documents[0].id,
            "entity_type": "DATE",
            "entity_text": "January 15, 2024",
            "confidence": 0.95,
            "mentions": 3,
        },
        {
            "document_id": documents[0].id,
            "entity_type": "MONEY",
            "entity_text": "$125,000",
            "confidence": 0.97,
            "mentions": 8,
        },
        {
            "document_id": documents[1].id,
            "entity_type": "PERSON",
            "entity_text": "Michael Chen",
            "confidence": 0.96,
            "mentions": 12,
            "metadata": {"role": "HR Director"},
        },
        # Entities from Smith case
        {
            "document_id": documents[3].id,
            "entity_type": "PERSON",
            "entity_text": "Dr. Robert Williams",
            "confidence": 0.98,
            "mentions": 34,
        },
        {
            "document_id": documents[3].id,
            "entity_type": "ORGANIZATION",
            "entity_text": "MediCare Inc.",
            "confidence": 0.99,
            "mentions": 56,
        },
    ]

    entities = []
    for ent_data in entities_data:
        entity = Entity(**ent_data)
        db.add(entity)
        entities.append(entity)

    db.commit()

    print(f"✓ Created {len(entities)} entities")
    return entities


def main():
    """Main seed function"""
    # Parse command-line arguments
    clear_first = "--clear" in sys.argv
    force_reseed = "--force" in sys.argv
    skip_existing = not force_reseed

    print("🌱 Starting database seeding...")
    if clear_first:
        print("⚠️  Mode: Clear all data first, then seed")
    elif force_reseed:
        print("⚠️  Mode: Force re-seed (delete existing entries)")
    else:
        print("ℹ️  Mode: Skip existing entries (safe)")

    db = SessionLocal()
    try:
        # Clear data if requested
        if clear_first:
            clear_all_data(db)

        # Seed data in order
        cases = seed_cases(db, skip_existing=skip_existing)
        documents = seed_documents(db, cases, skip_existing=skip_existing)
        # transcriptions = seed_transcriptions(db, cases)
        # entities = seed_entities(db, documents)

        print("\n✅ Database seeding completed successfully!")
        print(f"   - {len(cases)} cases")
        print(f"   - {len(documents)} documents")
        # print(f"   - {len(transcriptions)} transcriptions")
        # print(f"   - {len(entities)} entities")

    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
