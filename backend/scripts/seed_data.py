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
import io
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models import (
    Case, Document, Transcription, Entity,
    DiscoveryItem, DiscoveryItemType, DiscoveryItemSource, DiscoveryItemFormFactor,
    VisualContent, Category, CategoryType, DiscoveryItemCategory
)
from app.core.minio import minio_client


def clear_all_data(db: Session):
    """Clear all data from the database"""
    print("🗑️  Clearing all data...")

    try:
        # Delete in reverse order of dependencies
        db.execute(text("TRUNCATE entities CASCADE"))
        db.execute(text("TRUNCATE transcriptions CASCADE"))
        db.execute(text("TRUNCATE chunks CASCADE"))
        db.execute(text("TRUNCATE documents CASCADE"))
        db.execute(text("TRUNCATE discovery_item_categories CASCADE"))
        db.execute(text("TRUNCATE visual_content CASCADE"))
        db.execute(text("TRUNCATE discovery_items CASCADE"))
        db.execute(text("TRUNCATE categories CASCADE"))
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


def upload_placeholder_file_to_minio(bucket_name: str, object_name: str, content: bytes, content_type: str) -> bool:
    """Upload a placeholder file to MinIO"""
    try:
        file_data = io.BytesIO(content)
        success = minio_client.upload_file(
            bucket_name=bucket_name,
            object_name=object_name,
            file_data=file_data,
            file_size=len(content),
            content_type=content_type
        )
        return success
    except Exception as e:
        print(f"⚠️  Error uploading file to MinIO: {e}")
        return False


def seed_categories(db: Session, skip_existing=True):
    """Create sample categories for discovery items"""
    categories_data = [
        {"name": "Evidence", "type": CategoryType.MANUAL},
        {"name": "Witness Statements", "type": CategoryType.MANUAL},
        {"name": "Communications", "type": CategoryType.MANUAL},
        {"name": "Social Media", "type": CategoryType.MANUAL},
        {"name": "Surveillance", "type": CategoryType.CASE_SPECIFIC},
        {"name": "Weapons", "type": CategoryType.AUTO_GENERATED},
        {"name": "Vehicles", "type": CategoryType.AUTO_GENERATED},
        {"name": "People", "type": CategoryType.AUTO_GENERATED},
        {"name": "Locations", "type": CategoryType.AUTO_GENERATED},
        {"name": "Threats", "type": CategoryType.AUTO_GENERATED},
    ]

    categories = []
    created_count = 0
    skipped_count = 0

    for cat_data in categories_data:
        existing_cat = db.query(Category).filter_by(name=cat_data["name"]).first()

        if existing_cat:
            if skip_existing:
                categories.append(existing_cat)
                skipped_count += 1
                continue
            else:
                db.delete(existing_cat)
                db.commit()

        category = Category(**cat_data)
        db.add(category)
        categories.append(category)
        created_count += 1

    if created_count > 0:
        db.commit()
        for cat in categories:
            if cat not in db:
                db.refresh(cat)

    if created_count > 0:
        print(f"✓ Created {created_count} categories")
    if skipped_count > 0:
        print(f"ℹ️  Skipped {skipped_count} existing categories")

    return categories


def seed_discovery_items(db: Session, cases: list, categories: list, skip_existing=True):
    """Create sample discovery items with various types and sources"""

    # Define sample discovery items
    discovery_items_data = [
        # PHOTO items
        {
            "case_id": cases[0].id,
            "type": DiscoveryItemType.PHOTO,
            "source": DiscoveryItemSource.CELLEBRITE,
            "form_factor": DiscoveryItemFormFactor.SINGLE_ITEM,
            "original_filename": "suspect_phone_photo_001.jpg",
            "file_path": f"case-{cases[0].id}/discovery/photos/suspect_phone_photo_001.jpg",
            "processed": True,
            "importance_score": 0.85,
            "item_metadata": {
                "exif_data": {
                    "timestamp": "2024-01-15T14:30:00Z",
                    "device": "iPhone 13 Pro",
                    "location": {"lat": 37.7749, "lon": -122.4194}
                },
                "extracted_from": "iPhone - Sarah Johnson",
                "evidence_tag": "EVID-001-A"
            }
        },
        {
            "case_id": cases[0].id,
            "type": DiscoveryItemType.PHOTO,
            "source": DiscoveryItemSource.SURVEILLANCE,
            "form_factor": DiscoveryItemFormFactor.SINGLE_ITEM,
            "original_filename": "office_cctv_frame_0045.jpg",
            "file_path": f"case-{cases[0].id}/discovery/photos/office_cctv_frame_0045.jpg",
            "processed": True,
            "importance_score": 0.92,
            "item_metadata": {
                "camera_id": "CCTV-LOBBY-02",
                "timestamp": "2024-01-15T09:15:00Z",
                "evidence_tag": "EVID-001-B"
            }
        },
        # VIDEO items
        {
            "case_id": cases[1].id,
            "type": DiscoveryItemType.VIDEO,
            "source": DiscoveryItemSource.SURVEILLANCE,
            "form_factor": DiscoveryItemFormFactor.LONG_FORM,
            "original_filename": "hospital_hallway_cam3.mp4",
            "file_path": f"case-{cases[1].id}/discovery/videos/hospital_hallway_cam3.mp4",
            "processed": False,
            "importance_score": 0.78,
            "item_metadata": {
                "duration_seconds": 3600,
                "camera_id": "HOSP-HALL-03",
                "timestamp": "2024-02-10T08:00:00Z",
                "resolution": "1920x1080",
                "fps": 30
            }
        },
        {
            "case_id": cases[1].id,
            "type": DiscoveryItemType.VIDEO,
            "source": DiscoveryItemSource.BODY_CAM,
            "form_factor": DiscoveryItemFormFactor.LONG_FORM,
            "original_filename": "officer_bodycam_incident.mp4",
            "file_path": f"case-{cases[1].id}/discovery/videos/officer_bodycam_incident.mp4",
            "processed": True,
            "importance_score": 0.95,
            "item_metadata": {
                "duration_seconds": 1800,
                "officer_id": "BADGE-4521",
                "timestamp": "2024-02-10T14:22:00Z",
                "resolution": "1280x720",
                "fps": 60
            }
        },
        # SOCIAL_POST items
        {
            "case_id": cases[0].id,
            "type": DiscoveryItemType.SOCIAL_POST,
            "source": DiscoveryItemSource.CELLEBRITE,
            "form_factor": DiscoveryItemFormFactor.SHORT_FORM,
            "original_filename": "tiktok_post_20240115.mp4",
            "file_path": f"case-{cases[0].id}/discovery/social/tiktok_post_20240115.mp4",
            "processed": True,
            "importance_score": 0.65,
            "item_metadata": {
                "platform": "TikTok",
                "username": "@sarah_j_tech",
                "post_id": "7234567890123456789",
                "posted_at": "2024-01-15T18:30:00Z",
                "likes": 1234,
                "comments": 56,
                "shares": 23,
                "caption": "Another day at the office... not for long! #corporatelife #techcorp"
            }
        },
        {
            "case_id": cases[0].id,
            "type": DiscoveryItemType.SOCIAL_POST,
            "source": DiscoveryItemSource.CELLEBRITE,
            "form_factor": DiscoveryItemFormFactor.SINGLE_ITEM,
            "original_filename": "instagram_post_screenshot.jpg",
            "file_path": f"case-{cases[0].id}/discovery/social/instagram_post_screenshot.jpg",
            "processed": True,
            "importance_score": 0.45,
            "item_metadata": {
                "platform": "Instagram",
                "username": "@sarahjohnson",
                "post_id": "CxYzAbC123",
                "posted_at": "2024-01-14T12:00:00Z",
                "likes": 456,
                "caption": "Celebrating my work anniversary! 8 years at @techcorp"
            }
        },
        # EMAIL items
        {
            "case_id": cases[0].id,
            "type": DiscoveryItemType.EMAIL,
            "source": DiscoveryItemSource.PROSECUTOR,
            "form_factor": DiscoveryItemFormFactor.SINGLE_ITEM,
            "original_filename": "termination_notice_email.eml",
            "file_path": f"case-{cases[0].id}/discovery/emails/termination_notice_email.eml",
            "processed": True,
            "importance_score": 0.98,
            "item_metadata": {
                "from": "hr@techcorp.com",
                "to": "sarah.johnson@techcorp.com",
                "subject": "Notice of Employment Termination",
                "sent_at": "2024-01-15T16:00:00Z",
                "has_attachments": True,
                "attachments": ["termination_letter.pdf"]
            }
        },
        {
            "case_id": cases[1].id,
            "type": DiscoveryItemType.EMAIL,
            "source": DiscoveryItemSource.EVIDENCE,
            "form_factor": DiscoveryItemFormFactor.SINGLE_ITEM,
            "original_filename": "medical_records_request.eml",
            "file_path": f"case-{cases[1].id}/discovery/emails/medical_records_request.eml",
            "processed": False,
            "importance_score": 0.72,
            "item_metadata": {
                "from": "robert.smith@email.com",
                "to": "records@medicare.com",
                "subject": "Request for Medical Records - Patient ID 12345",
                "sent_at": "2024-02-08T10:30:00Z",
                "has_attachments": False
            }
        },
        # CALL_LOG items
        {
            "case_id": cases[0].id,
            "type": DiscoveryItemType.CALL_LOG,
            "source": DiscoveryItemSource.CELLEBRITE,
            "form_factor": DiscoveryItemFormFactor.SINGLE_ITEM,
            "original_filename": "phone_call_logs_jan2024.json",
            "file_path": f"case-{cases[0].id}/discovery/calls/phone_call_logs_jan2024.json",
            "processed": True,
            "importance_score": 0.55,
            "item_metadata": {
                "total_calls": 47,
                "period_start": "2024-01-01T00:00:00Z",
                "period_end": "2024-01-31T23:59:59Z",
                "device": "iPhone 13 Pro",
                "owner": "Sarah Johnson"
            }
        },
        {
            "case_id": cases[1].id,
            "type": DiscoveryItemType.CALL_LOG,
            "source": DiscoveryItemSource.PROSECUTOR,
            "form_factor": DiscoveryItemFormFactor.SINGLE_ITEM,
            "original_filename": "hospital_phone_records.csv",
            "file_path": f"case-{cases[1].id}/discovery/calls/hospital_phone_records.csv",
            "processed": True,
            "importance_score": 0.68,
            "item_metadata": {
                "total_calls": 156,
                "period_start": "2024-02-01T00:00:00Z",
                "period_end": "2024-02-28T23:59:59Z",
                "phone_number": "+1-555-HOSPITAL"
            }
        },
    ]

    discovery_items = []
    created_count = 0
    skipped_count = 0

    for item_data in discovery_items_data:
        # Check if item already exists (by case_id and original_filename)
        existing_item = db.query(DiscoveryItem).filter_by(
            case_id=item_data["case_id"],
            original_filename=item_data["original_filename"]
        ).first()

        if existing_item:
            if skip_existing:
                discovery_items.append(existing_item)
                skipped_count += 1
                continue
            else:
                db.delete(existing_item)
                db.commit()

        # Upload placeholder file to MinIO
        bucket_name = f"case-{item_data['case_id']}"

        # Create placeholder content based on type
        if item_data["type"] in [DiscoveryItemType.PHOTO, DiscoveryItemType.SOCIAL_POST]:
            # Placeholder image data (1x1 pixel PNG)
            placeholder_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            content_type = "image/jpeg"
        elif item_data["type"] == DiscoveryItemType.VIDEO:
            # Placeholder text for video
            placeholder_content = b"Placeholder video content"
            content_type = "video/mp4"
        elif item_data["type"] == DiscoveryItemType.EMAIL:
            # Placeholder email
            placeholder_content = b"From: sender@example.com\nTo: recipient@example.com\nSubject: Test\n\nPlaceholder email content"
            content_type = "message/rfc822"
        else:
            # Generic placeholder
            placeholder_content = b"Placeholder content"
            content_type = "application/octet-stream"

        # Upload to MinIO
        upload_success = upload_placeholder_file_to_minio(
            bucket_name=bucket_name,
            object_name=item_data["file_path"].split('/', 1)[1] if '/' in item_data["file_path"] else item_data["file_path"],
            content=placeholder_content,
            content_type=content_type
        )

        if not upload_success:
            print(f"⚠️  Failed to upload {item_data['original_filename']} to MinIO, skipping...")
            continue

        # Create discovery item
        item = DiscoveryItem(**item_data)
        db.add(item)
        discovery_items.append(item)
        created_count += 1

    if created_count > 0:
        db.commit()
        for item in discovery_items:
            if item not in db:
                db.refresh(item)

    if created_count > 0:
        print(f"✓ Created {created_count} discovery items")
    if skipped_count > 0:
        print(f"ℹ️  Skipped {skipped_count} existing discovery items")

    return discovery_items


def seed_visual_content(db: Session, discovery_items: list):
    """Create sample visual content (VLM captions) for photos and videos"""
    visual_content_data = []

    for item in discovery_items:
        # Add visual content for photos
        if item.type == DiscoveryItemType.PHOTO:
            if "suspect_phone" in item.original_filename:
                visual_content_data.append({
                    "discovery_item_id": item.id,
                    "frame_number": None,
                    "timestamp_in_video": None,
                    "vlm_caption": "A photograph showing the interior of an office building with modern furnishings. Two people are visible in business attire near a water cooler. Overhead fluorescent lighting illuminates a gray carpeted floor.",
                    "detected_objects": ["person", "water cooler", "office furniture", "fluorescent lights"],
                    "detected_scenes": ["office", "interior", "workplace"],
                    "detected_activities": ["standing", "conversation"],
                    "sensitive_flags": None,
                    "is_meme": False
                })
            elif "cctv" in item.original_filename:
                visual_content_data.append({
                    "discovery_item_id": item.id,
                    "frame_number": None,
                    "timestamp_in_video": None,
                    "vlm_caption": "Security camera footage showing a building lobby. A person wearing a dark jacket is visible near the elevator bank. Timestamp visible in corner: 09:15:23. Image is grainy with slight motion blur.",
                    "detected_objects": ["person", "elevator", "security camera timestamp"],
                    "detected_scenes": ["lobby", "interior", "security footage"],
                    "detected_activities": ["walking", "waiting"],
                    "sensitive_flags": None,
                    "is_meme": False
                })
            elif "instagram" in item.original_filename:
                visual_content_data.append({
                    "discovery_item_id": item.id,
                    "frame_number": None,
                    "timestamp_in_video": None,
                    "vlm_caption": "Instagram post screenshot showing a smiling person in business attire holding a commemorative plaque. Office setting with company logo visible in background. Social media interface elements visible including like button and comment count.",
                    "detected_objects": ["person", "plaque", "company logo", "social media UI"],
                    "detected_scenes": ["office", "social media", "celebration"],
                    "detected_activities": ["posing", "holding award"],
                    "sensitive_flags": None,
                    "is_meme": False
                })

        # Add visual content for video items (sample frames)
        elif item.type == DiscoveryItemType.VIDEO and item.processed:
            if "bodycam" in item.original_filename:
                # Add a few sample frames from body camera footage
                visual_content_data.extend([
                    {
                        "discovery_item_id": item.id,
                        "frame_number": 0,
                        "timestamp_in_video": 0.0,
                        "vlm_caption": "Body camera view of a hospital hallway. Fluorescent lighting, white walls with room number signs. Medical equipment cart visible on the right side.",
                        "detected_objects": ["hallway", "medical equipment", "room signs"],
                        "detected_scenes": ["hospital", "interior", "corridor"],
                        "detected_activities": ["walking"],
                        "sensitive_flags": None,
                        "is_meme": False
                    },
                    {
                        "discovery_item_id": item.id,
                        "frame_number": 300,
                        "timestamp_in_video": 10.0,
                        "vlm_caption": "Body camera footage shows officer approaching a hospital room door marked '324'. Person in medical scrubs visible in background.",
                        "detected_objects": ["door", "room number", "person", "medical scrubs"],
                        "detected_scenes": ["hospital", "interior"],
                        "detected_activities": ["walking", "approaching"],
                        "sensitive_flags": None,
                        "is_meme": False
                    }
                ])

        # Add visual content for social media posts with video
        elif item.type == DiscoveryItemType.SOCIAL_POST and "tiktok" in item.original_filename:
            visual_content_data.append({
                "discovery_item_id": item.id,
                "frame_number": 0,
                "timestamp_in_video": 0.0,
                "vlm_caption": "TikTok video thumbnail showing person in office environment. Corporate setting with cubicles visible. Text overlay present with trending audio indicator.",
                "detected_objects": ["person", "cubicles", "text overlay", "office"],
                "detected_scenes": ["office", "social media", "corporate"],
                "detected_activities": ["recording video", "posing"],
                "sensitive_flags": None,
                "is_meme": False
            })

    # Create visual content records
    visual_contents = []
    for vc_data in visual_content_data:
        visual_content = VisualContent(**vc_data)
        db.add(visual_content)
        visual_contents.append(visual_content)

    if visual_contents:
        db.commit()
        print(f"✓ Created {len(visual_contents)} visual content records")

    return visual_contents


def seed_discovery_item_categories(db: Session, discovery_items: list, categories: list):
    """Associate discovery items with categories"""

    # Map category names for easy lookup
    category_map = {cat.name: cat for cat in categories}

    associations = []

    for item in discovery_items:
        # Assign categories based on item characteristics
        item_categories = []

        # Evidence category for high importance items
        if item.importance_score and item.importance_score > 0.8:
            item_categories.append({
                "category": category_map["Evidence"],
                "confidence": 0.95,
                "auto_generated": True
            })

        # Social Media category
        if item.type == DiscoveryItemType.SOCIAL_POST:
            item_categories.append({
                "category": category_map["Social Media"],
                "confidence": 1.0,
                "auto_generated": False
            })

        # Surveillance category
        if item.source == DiscoveryItemSource.SURVEILLANCE or item.source == DiscoveryItemSource.BODY_CAM:
            item_categories.append({
                "category": category_map["Surveillance"],
                "confidence": 1.0,
                "auto_generated": False
            })

        # Communications category
        if item.type in [DiscoveryItemType.EMAIL, DiscoveryItemType.CALL_LOG, DiscoveryItemType.SMS]:
            item_categories.append({
                "category": category_map["Communications"],
                "confidence": 1.0,
                "auto_generated": False
            })

        # Auto-generated categories based on content
        if "suspect_phone" in item.original_filename or "bodycam" in item.original_filename:
            item_categories.append({
                "category": category_map["People"],
                "confidence": 0.87,
                "auto_generated": True
            })

        if "office" in item.original_filename or "hospital" in item.original_filename:
            item_categories.append({
                "category": category_map["Locations"],
                "confidence": 0.92,
                "auto_generated": True
            })

        # Create associations
        for cat_info in item_categories:
            association = DiscoveryItemCategory(
                discovery_item_id=item.id,
                category_id=cat_info["category"].id,
                confidence_score=cat_info["confidence"],
                auto_generated=cat_info["auto_generated"]
            )
            db.add(association)
            associations.append(association)

    if associations:
        db.commit()
        print(f"✓ Created {len(associations)} discovery item-category associations")

    return associations


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
        categories = seed_categories(db, skip_existing=skip_existing)
        discovery_items = seed_discovery_items(db, cases, categories, skip_existing=skip_existing)
        visual_contents = seed_visual_content(db, discovery_items)
        associations = seed_discovery_item_categories(db, discovery_items, categories)
        # transcriptions = seed_transcriptions(db, cases)
        # entities = seed_entities(db, documents)

        print("\n✅ Database seeding completed successfully!")
        print(f"   - {len(cases)} cases")
        print(f"   - {len(documents)} documents")
        print(f"   - {len(categories)} categories")
        print(f"   - {len(discovery_items)} discovery items")
        print(f"   - {len(visual_contents)} visual content records")
        print(f"   - {len(associations)} category associations")
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
