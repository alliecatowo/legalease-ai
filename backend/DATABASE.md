# LegalEase Database Schema

## Overview

The LegalEase PostgreSQL database schema is designed to support legal document management, processing, and analysis. The schema includes six main tables and two enum types.

## Tables

### 1. Cases
Primary container for legal matters.

**Table:** `cases`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| name | String(255) | Not Null, Indexed | Case name |
| case_number | String(100) | Not Null, Unique, Indexed | Case identifier |
| client | String(255) | Not Null, Indexed | Client name |
| matter_type | String(100) | Nullable | Type of legal matter |
| status | CaseStatus | Not Null, Indexed, Default: STAGING | Current case status |
| created_at | DateTime | Not Null, Default: now() | Creation timestamp |
| updated_at | DateTime | Not Null, Default: now() | Last update timestamp |
| archived_at | DateTime | Nullable | Archival timestamp |

**Status Enum:** `STAGING`, `PROCESSING`, `ACTIVE`, `UNLOADED`, `ARCHIVED`

**Relationships:**
- One-to-Many with Documents (CASCADE DELETE)

---

### 2. Documents
Uploaded files associated with cases.

**Table:** `documents`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| case_id | Integer | Foreign Key → cases.id, Not Null, Indexed | Parent case |
| filename | String(255) | Not Null | Original filename |
| file_path | String(512) | Not Null | Storage path |
| mime_type | String(100) | Nullable | MIME type |
| size | BigInteger | Not Null | File size in bytes |
| status | DocumentStatus | Not Null, Indexed, Default: PENDING | Processing status |
| meta_data | JSON | Nullable | Additional metadata |
| uploaded_at | DateTime | Not Null, Default: now() | Upload timestamp |

**Status Enum:** `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`

**Relationships:**
- Many-to-One with Case
- One-to-Many with Chunks (CASCADE DELETE)
- Many-to-Many with Entities (via document_entities)
- One-to-One with Transcription (CASCADE DELETE)

---

### 3. Chunks
Text segments extracted from documents.

**Table:** `chunks`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| document_id | Integer | Foreign Key → documents.id, Not Null, Indexed | Parent document |
| text | Text | Not Null | Chunk text content |
| chunk_type | String(50) | Nullable | Type (paragraph, page, section) |
| position | Integer | Not Null | Order in document |
| page_number | Integer | Nullable | Source page number |
| meta_data | JSON | Nullable | Embeddings, confidence, etc. |
| created_at | DateTime | Not Null, Default: now() | Creation timestamp |

**Relationships:**
- Many-to-One with Document

---

### 4. Entities
Named entities extracted from documents via NLP.

**Table:** `entities`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| text | String(255) | Not Null, Indexed | Entity text |
| entity_type | String(100) | Not Null, Indexed | Type (PERSON, ORG, DATE, LOCATION) |
| confidence | Float | Nullable | NLP confidence score |
| meta_data | JSON | Nullable | Additional metadata |

**Relationships:**
- Many-to-Many with Documents (via document_entities)

---

### 5. Document-Entities Association
Many-to-many relationship between documents and entities.

**Table:** `document_entities`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| document_id | Integer | Primary Key, Foreign Key → documents.id | Document reference |
| entity_id | Integer | Primary Key, Foreign Key → entities.id | Entity reference |

Both columns form a composite primary key.

---

### 6. Transcriptions
Audio/video transcription results.

**Table:** `transcriptions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| document_id | Integer | Foreign Key → documents.id, Not Null, Unique, Indexed | Parent document |
| format | String(50) | Nullable | Audio/video format |
| duration | Float | Nullable | Duration in seconds |
| speakers | JSON | Nullable | Speaker identification data |
| segments | JSON | Not Null | Transcription segments with timestamps |
| created_at | DateTime | Not Null, Default: now() | Creation timestamp |

**Relationships:**
- One-to-One with Document

---

### 7. Processing Jobs
Asynchronous task tracking.

**Table:** `processing_jobs`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| job_type | String(100) | Not Null, Indexed | Job type (transcription, entity_extraction, ocr) |
| status | String(50) | Not Null, Indexed | Job status (pending, running, completed, failed) |
| entity_id | Integer | Nullable | Generic entity reference |
| result | JSON | Nullable | Job results |
| error | Text | Nullable | Error message |
| created_at | DateTime | Not Null, Indexed, Default: now() | Creation timestamp |
| started_at | DateTime | Nullable | Start timestamp |
| completed_at | DateTime | Nullable | Completion timestamp |

---

## Entity Relationship Diagram

```
┌──────────┐
│  Cases   │
└────┬─────┘
     │ 1:N
     ↓
┌──────────────┐
│  Documents   │◄─────┐
└──┬───┬───┬───┘      │
   │   │   │ 1:N     │ M:N
   │   │   ↓          │
   │   │  ┌─────────┐ │
   │   │  │ Chunks  │ │
   │   │  └─────────┘ │
   │   │              │
   │   │ 1:1          │
   │   ↓              │
   │  ┌──────────────┐│
   │  │Transcription ││
   │  └──────────────┘│
   │                  │
   │ M:N              │
   ↓                  │
┌────────────────┐    │
│document_entities│────┘
└────────┬───────┘
         │ M:N
         ↓
   ┌──────────┐
   │ Entities │
   └──────────┘

Independent:
┌─────────────────┐
│ Processing Jobs │
└─────────────────┘
```

## Indexes

The schema includes strategic indexes on:
- Primary keys (all tables)
- Foreign keys (case_id, document_id, entity_id)
- Status fields (cases.status, documents.status, processing_jobs.status)
- Search fields (case_number, client, entity.text, entity_type)
- Timestamp fields (processing_jobs.created_at)

## Migration

The initial migration is located at:
`/home/Allie/develop/legalease/backend/alembic/versions/ec667c5bb003_initial_schema.py`

To apply migrations:
```bash
cd /home/Allie/develop/legalease/backend
alembic upgrade head
```

To rollback:
```bash
alembic downgrade -1
```

## Notes

- All timestamps use UTC via `datetime.utcnow()`
- Cascade deletes are configured for parent-child relationships
- JSON columns support flexible metadata storage
- Enum types are native PostgreSQL enums for type safety
- The `meta_data` column name is used instead of `metadata` to avoid SQLAlchemy reserved word conflicts
