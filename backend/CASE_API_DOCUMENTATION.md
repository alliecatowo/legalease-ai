# Case Management API Documentation

## Overview

The Case Management API provides a complete CRUD interface for managing legal cases in the LegalEase system. It follows the RAGFlow load/unload pattern, allowing cases to be activated for processing or unloaded to conserve resources while preserving data.

## Architecture

### Components Created

1. **app/schemas/case.py** - Pydantic schemas for request/response validation
2. **app/services/case_service.py** - Business logic layer for case operations
3. **app/api/v1/cases.py** - FastAPI router with HTTP endpoints

### Integration Points

- **Database**: PostgreSQL via SQLAlchemy for case metadata
- **Qdrant**: Vector database - one collection per case for semantic search
- **MinIO**: Object storage - one bucket per case for document files

## API Endpoints

All endpoints are prefixed with `/api/v1/cases`

### 1. Create Case

**POST** `/api/v1/cases`

Creates a new case with associated Qdrant collection and MinIO bucket.

**Request Body:**
```json
{
  "name": "Johnson v. Smith",
  "case_number": "2024-CV-12345",
  "client": "Johnson Corporation",
  "matter_type": "Contract Dispute"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "name": "Johnson v. Smith",
  "case_number": "2024-CV-12345",
  "client": "Johnson Corporation",
  "matter_type": "Contract Dispute",
  "status": "STAGING",
  "created_at": "2024-10-09T19:30:00Z",
  "updated_at": "2024-10-09T19:30:00Z",
  "archived_at": null,
  "documents": []
}
```

**What Happens:**
- Case record created in database with status `STAGING`
- Qdrant collection created: `case_2024_cv_12345`
- MinIO bucket created: `case-2024-cv-12345`

**Error Responses:**
- `409 Conflict` - Case number already exists
- `500 Internal Server Error` - Qdrant or MinIO resource creation failed

---

### 2. List Cases

**GET** `/api/v1/cases?status={status}&page={page}&page_size={size}`

Retrieves a paginated list of cases with optional status filter.

**Query Parameters:**
- `status` (optional): Filter by case status (STAGING, PROCESSING, ACTIVE, UNLOADED, ARCHIVED)
- `page` (optional, default=1): Page number (1-indexed)
- `page_size` (optional, default=50, max=100): Items per page

**Response:** `200 OK`
```json
{
  "cases": [
    {
      "id": 1,
      "name": "Johnson v. Smith",
      "case_number": "2024-CV-12345",
      "client": "Johnson Corporation",
      "matter_type": "Contract Dispute",
      "status": "ACTIVE",
      "created_at": "2024-10-09T19:30:00Z",
      "updated_at": "2024-10-09T19:35:00Z",
      "archived_at": null,
      "document_count": 5
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50
}
```

---

### 3. Get Case Details

**GET** `/api/v1/cases/{case_id}`

Retrieves detailed information about a specific case, including associated documents.

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "Johnson v. Smith",
  "case_number": "2024-CV-12345",
  "client": "Johnson Corporation",
  "matter_type": "Contract Dispute",
  "status": "ACTIVE",
  "created_at": "2024-10-09T19:30:00Z",
  "updated_at": "2024-10-09T19:35:00Z",
  "archived_at": null,
  "documents": [
    {
      "id": 1,
      "filename": "complaint.pdf",
      "mime_type": "application/pdf",
      "size": 524288,
      "status": "COMPLETED",
      "uploaded_at": "2024-10-09T19:31:00Z"
    }
  ]
}
```

**Error Responses:**
- `404 Not Found` - Case does not exist

---

### 4. Update Case

**PUT** `/api/v1/cases/{case_id}`

Updates case metadata (name, case_number, client, matter_type).

**Request Body:**
```json
{
  "name": "Johnson Corporation v. Smith Enterprises",
  "client": "Johnson Corporation Inc.",
  "matter_type": "Contract & IP Dispute"
}
```

**Response:** `200 OK`
Returns updated case details (same format as Get Case Details)

**Error Responses:**
- `404 Not Found` - Case does not exist
- `409 Conflict` - New case_number conflicts with existing case

---

### 5. Activate Case (Load)

**PUT** `/api/v1/cases/{case_id}/activate`

Changes case status to `ACTIVE`, making it available for:
- Document uploads and processing
- Vector search queries
- Active case management workflows

**Response:** `200 OK`
```json
{
  "id": 1,
  "case_number": "2024-CV-12345",
  "status": "ACTIVE",
  "message": "Case '2024-CV-12345' activated successfully"
}
```

**Error Responses:**
- `404 Not Found` - Case does not exist

---

### 6. Unload Case

**PUT** `/api/v1/cases/{case_id}/unload`

Changes case status to `UNLOADED`, which:
- Removes the case from active processing
- Preserves all data (database, vectors, files)
- Keeps Qdrant collection and MinIO bucket intact
- Can be reactivated later

**Response:** `200 OK`
```json
{
  "id": 1,
  "case_number": "2024-CV-12345",
  "status": "UNLOADED",
  "message": "Case '2024-CV-12345' unloaded successfully"
}
```

**Error Responses:**
- `404 Not Found` - Case does not exist

---

### 7. Delete Case

**DELETE** `/api/v1/cases/{case_id}`

Permanently deletes a case and all associated resources:
- Case record from database
- All documents, chunks, entities (cascade deletion)
- Qdrant collection
- MinIO bucket and all files

**WARNING:** This operation is irreversible!

**Response:** `200 OK`
```json
{
  "id": 1,
  "case_number": "2024-CV-12345",
  "message": "Case '2024-CV-12345' and all associated resources deleted successfully",
  "deleted_at": "2024-10-09T20:00:00Z"
}
```

**Error Responses:**
- `404 Not Found` - Case does not exist

## Case Lifecycle

```
┌──────────┐
│ STAGING  │  ← Case created, resources allocated
└────┬─────┘
     │ activate
     ▼
┌──────────┐
│ ACTIVE   │  ← Processing documents, searchable
└────┬─────┘
     │ unload
     ▼
┌──────────┐
│ UNLOADED │  ← Inactive, data preserved
└────┬─────┘
     │ activate (can reactivate)
     ▼
┌──────────┐
│ ACTIVE   │
└──────────┘
```

## Resource Naming Conventions

### Qdrant Collections
- Format: `case_{normalized_case_number}`
- Example: Case `2024-CV-12345` → Collection `case_2024_cv_12345`
- Normalization: lowercase, hyphens → underscores

### MinIO Buckets
- Format: `case-{normalized_case_number}`
- Example: Case `2024-CV-12345` → Bucket `case-2024-cv-12345`
- Normalization: lowercase, underscores → hyphens

## Service Layer (CaseService)

The `CaseService` class in `app/services/case_service.py` provides:

### Public Methods

- `create_case(name, case_number, client, matter_type)` - Create case + resources
- `get_case(case_id)` - Retrieve case by ID
- `get_case_by_number(case_number)` - Retrieve case by case number
- `list_cases(status, skip, limit)` - List cases with pagination
- `update_case(case_id, ...)` - Update case metadata
- `activate_case(case_id)` - Change status to ACTIVE
- `unload_case(case_id)` - Change status to UNLOADED
- `delete_case(case_id)` - Full deletion

### Exception Handling

- `CaseNotFoundError` - Case not found
- `CaseAlreadyExistsError` - Duplicate case_number
- `ResourceCreationError` - Qdrant/MinIO operation failed

## Example Usage (Python Client)

```python
import httpx

base_url = "http://localhost:8000/api/v1"

# Create a case
response = httpx.post(
    f"{base_url}/cases",
    json={
        "name": "My Case v. Defendant",
        "case_number": "2024-CV-001",
        "client": "Client Inc.",
        "matter_type": "Litigation"
    }
)
case = response.json()
case_id = case["id"]

# List all active cases
response = httpx.get(f"{base_url}/cases?status=ACTIVE")
cases = response.json()

# Activate the case
response = httpx.put(f"{base_url}/cases/{case_id}/activate")

# Unload the case
response = httpx.put(f"{base_url}/cases/{case_id}/unload")

# Delete the case
response = httpx.delete(f"{base_url}/cases/{case_id}")
```

## Example Usage (cURL)

```bash
# Create a case
curl -X POST http://localhost:8000/api/v1/cases \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Case v. Defendant",
    "case_number": "2024-CV-001",
    "client": "Client Inc.",
    "matter_type": "Litigation"
  }'

# List cases
curl http://localhost:8000/api/v1/cases

# Get specific case
curl http://localhost:8000/api/v1/cases/1

# Activate case
curl -X PUT http://localhost:8000/api/v1/cases/1/activate

# Unload case
curl -X PUT http://localhost:8000/api/v1/cases/1/unload

# Delete case
curl -X DELETE http://localhost:8000/api/v1/cases/1
```

## Testing

A test script is provided at `test_case_api.py`:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests
python test_case_api.py
```

**Note:** Tests that create/delete cases require Qdrant and MinIO to be running.

## Running the Server

```bash
# Activate virtual environment
source .venv/bin/activate

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or use the main.py directly
python -m app.main
```

## API Documentation

FastAPI provides auto-generated interactive documentation:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

## Database Schema

The Case model includes:

- `id` - Primary key
- `name` - Case name
- `case_number` - Unique identifier (indexed)
- `client` - Client name (indexed)
- `matter_type` - Type of legal matter
- `status` - Case status enum (indexed)
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp
- `archived_at` - Archival timestamp (nullable)

Relationships:
- `documents` - One-to-many with Document model (cascade delete)

## Dependencies

All required packages are in `pyproject.toml`:

- `fastapi` - Web framework
- `pydantic` - Data validation
- `sqlalchemy` - Database ORM
- `qdrant-client` - Vector database client
- `minio` - Object storage client
- `psycopg2-binary` - PostgreSQL driver

Install with:
```bash
uv sync
```

## Environment Variables

Configure in `.env` file:

```bash
# Database
DATABASE_URL=postgresql://legalease:legalease@localhost:5432/legalease

# Qdrant
QDRANT_URL=http://localhost:6333

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
```

## Next Steps

The Case Management API is ready for:

1. **Document Management** - Upload documents to cases
2. **Processing Pipeline** - Extract text, entities, create embeddings
3. **Search** - Semantic search across case documents
4. **Chat** - RAG-based Q&A over case materials

## Files Created

- `/home/Allie/develop/legalease/backend/app/schemas/case.py` (153 lines)
- `/home/Allie/develop/legalease/backend/app/services/case_service.py` (450 lines)
- `/home/Allie/develop/legalease/backend/app/api/v1/cases.py` (359 lines)
- `/home/Allie/develop/legalease/backend/test_case_api.py` (219 lines)

## Files Modified

- `/home/Allie/develop/legalease/backend/app/api/v1/router.py` - Added cases router
- `/home/Allie/develop/legalease/backend/app/schemas/__init__.py` - Exported case schemas
- `/home/Allie/develop/legalease/backend/app/services/__init__.py` - Added CaseService export
