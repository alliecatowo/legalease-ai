"""
Seed script to populate the database with test data for development.
"""
import asyncio
from datetime import datetime, timedelta
import random
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models import Case, Document, Transcription, Entity
from app.core.qdrant import get_qdrant_client


async def seed_cases(db: AsyncSession):
    """Create sample cases"""
    cases_data = [
        {
            "name": "Johnson v. TechCorp",
            "description": "Employment discrimination case involving wrongful termination",
            "status": "ACTIVE",
            "tags": ["employment", "discrimination", "wrongful-termination"],
        },
        {
            "name": "Smith v. MediCare Inc.",
            "description": "Medical malpractice suit regarding surgical complications",
            "status": "ACTIVE",
            "tags": ["medical-malpractice", "negligence"],
        },
        {
            "name": "Anderson Construction Dispute",
            "description": "Contract dispute over construction delays and cost overruns",
            "status": "STAGING",
            "tags": ["contract", "construction", "dispute"],
        },
        {
            "name": "Thompson Estate Planning",
            "description": "Estate planning and trust administration",
            "status": "UNLOADED",
            "tags": ["estate", "trust", "probate"],
        },
    ]

    cases = []
    for case_data in cases_data:
        case = Case(**case_data)
        db.add(case)
        cases.append(case)

    await db.commit()
    for case in cases:
        await db.refresh(case)

    print(f"✓ Created {len(cases)} cases")
    return cases


async def seed_documents(db: AsyncSession, cases: list):
    """Create sample documents"""
    documents_data = [
        # Johnson v. TechCorp documents
        {
            "case_id": cases[0].id,
            "filename": "employment_agreement.pdf",
            "title": "Employment Agreement - TechCorp Inc.",
            "document_type": "contract",
            "file_size": 245000,
            "mime_type": "application/pdf",
            "status": "indexed",
            "summary": "Employment agreement outlining terms of employment, including salary, benefits, termination clauses, and non-compete provisions.",
        },
        {
            "case_id": cases[0].id,
            "filename": "termination_letter.pdf",
            "title": "Notice of Termination",
            "document_type": "general",
            "file_size": 52000,
            "mime_type": "application/pdf",
            "status": "indexed",
            "summary": "Letter notifying employee of immediate termination due to alleged policy violations.",
        },
        {
            "case_id": cases[0].id,
            "filename": "performance_reviews.pdf",
            "title": "Annual Performance Reviews 2022-2023",
            "document_type": "general",
            "file_size": 189000,
            "mime_type": "application/pdf",
            "status": "indexed",
            "summary": "Collection of performance reviews showing consistent positive evaluations prior to termination.",
        },
        # Smith v. MediCare documents
        {
            "case_id": cases[1].id,
            "filename": "medical_records.pdf",
            "title": "Patient Medical Records",
            "document_type": "general",
            "file_size": 512000,
            "mime_type": "application/pdf",
            "status": "indexed",
            "summary": "Complete medical records including surgical notes, complications, and follow-up care.",
        },
        {
            "case_id": cases[1].id,
            "filename": "expert_opinion.pdf",
            "title": "Medical Expert Opinion - Dr. Williams",
            "document_type": "general",
            "file_size": 156000,
            "mime_type": "application/pdf",
            "status": "indexed",
            "summary": "Expert medical testimony regarding standard of care and deviation from accepted practices.",
        },
        # Anderson Construction documents
        {
            "case_id": cases[2].id,
            "filename": "construction_contract.pdf",
            "title": "Master Construction Agreement",
            "document_type": "contract",
            "file_size": 328000,
            "mime_type": "application/pdf",
            "status": "processing",
            "summary": "Primary construction contract with timeline, budget, and deliverables.",
        },
    ]

    documents = []
    for doc_data in documents_data:
        # Add random timestamps in the last 90 days
        days_ago = random.randint(1, 90)
        created_at = datetime.utcnow() - timedelta(days=days_ago)

        doc = Document(
            **doc_data,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(doc)
        documents.append(doc)

    await db.commit()
    for doc in documents:
        await db.refresh(doc)

    print(f"✓ Created {len(documents)} documents")
    return documents


async def seed_transcriptions(db: AsyncSession, cases: list):
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

    await db.commit()
    for trans in transcriptions:
        await db.refresh(trans)

    print(f"✓ Created {len(transcriptions)} transcriptions")
    return transcriptions


async def seed_entities(db: AsyncSession, documents: list):
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

    await db.commit()

    print(f"✓ Created {len(entities)} entities")
    return entities


async def main():
    """Main seed function"""
    print("🌱 Starting database seeding...")

    async with AsyncSessionLocal() as db:
        try:
            # Seed data in order
            cases = await seed_cases(db)
            documents = await seed_documents(db, cases)
            transcriptions = await seed_transcriptions(db, cases)
            entities = await seed_entities(db, documents)

            print("\n✅ Database seeding completed successfully!")
            print(f"   - {len(cases)} cases")
            print(f"   - {len(documents)} documents")
            print(f"   - {len(transcriptions)} transcriptions")
            print(f"   - {len(entities)} entities")

        except Exception as e:
            print(f"\n❌ Error during seeding: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
