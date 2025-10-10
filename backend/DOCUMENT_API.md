# Document Upload and Management API

This document provides an overview of the Document Upload and Management API implemented for the LegalEase backend.

## Overview

The Document API provides comprehensive functionality for uploading, managing, and processing legal documents within cases. Documents are stored in MinIO object storage, tracked in PostgreSQL, and automatically queued for processing via Celery.

## Architecture

### Components

1. **Pydantic Schemas** (`app/schemas/document.py`)
   - `DocumentUpload` - Request schema for document metadata
   - `DocumentResponse` - Response schema with document details
   - `DocumentListResponse` - Response schema for listing documents
   - `DocumentDeleteResponse` - Response schema for deletion confirmation

2. **MinIO Client** (`app/core/minio_client.py`)
   - Singleton client with lazy initialization
   - Handles file upload, download, deletion
   - Automatic bucket creation and management
   - Presigned URL generation for temporary access

3. **Document Service** (`app/services/document_service.py`)
   - Business logic layer for document operations
   - Methods:
     - `upload_documents()` - Upload multiple files to a case
     - `get_document()` - Retrieve document by ID
     - `list_case_documents()` - List all documents in a case
     - `download_document()` - Download file from storage
     - `delete_document()` - Delete document and file

4. **Celery Tasks** (`app/workers/tasks/document_processing.py`)
   - `process_uploaded_document` - Async task for document processing
   - Updates document status (PENDING → PROCESSING → COMPLETED/FAILED)
   - Placeholder for future NLP processing (Phase 3)

5. **FastAPI Router** (`app/api/v1/documents.py`)
   - RESTful API endpoints
   - Integrated with FastAPI dependency injection
   - Automatic OpenAPI documentation

## API Endpoints

### 1. Upload Documents to a Case

**POST** `/api/v1/cases/{case_id}/documents`

Upload one or more documents to a case.

**Parameters:**
- `case_id` (path) - ID of the case to upload documents to

**Request Body:**
- Form data with file uploads (multipart/form-data)
- Field name: `files` (array of files)

**Response:**
```json
[
  {
    "id": 1,
    "case_id": 1,
    "filename": "contract.pdf",
    "file_path": "cases/1/a1b2c3d4_contract.pdf",
    "mime_type": "application/pdf",
    "size": 1048576,
    "status": "PENDING",
    "meta_data": null,
    "uploaded_at": "2025-10-09T19:30:00Z"
  }
]
```

**Status Codes:**
- `201 Created` - Documents uploaded successfully
- `400 Bad Request` - No files provided
- `404 Not Found` - Case not found
- `500 Internal Server Error` - Upload or storage error

### 2. List Documents in a Case

**GET** `/api/v1/cases/{case_id}/documents`

Get all documents associated with a case.

**Parameters:**
- `case_id` (path) - ID of the case

**Response:**
```json
{
  "documents": [
    {
      "id": 1,
      "case_id": 1,
      "filename": "contract.pdf",
      "file_path": "cases/1/a1b2c3d4_contract.pdf",
      "mime_type": "application/pdf",
      "size": 1048576,
      "status": "COMPLETED",
      "meta_data": null,
      "uploaded_at": "2025-10-09T19:30:00Z"
    }
  ],
  "total": 1,
  "case_id": 1
}
```

**Status Codes:**
- `200 OK` - Documents retrieved successfully
- `404 Not Found` - Case not found

### 3. Get Document Details

**GET** `/api/v1/documents/{document_id}`

Get detailed information about a specific document.

**Parameters:**
- `document_id` (path) - ID of the document

**Response:**
```json
{
  "id": 1,
  "case_id": 1,
  "filename": "contract.pdf",
  "file_path": "cases/1/a1b2c3d4_contract.pdf",
  "mime_type": "application/pdf",
  "size": 1048576,
  "status": "COMPLETED",
  "meta_data": null,
  "uploaded_at": "2025-10-09T19:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Document retrieved successfully
- `404 Not Found` - Document not found

### 4. Download Document

**GET** `/api/v1/documents/{document_id}/download`

Download the actual file content from storage.

**Parameters:**
- `document_id` (path) - ID of the document

**Response:**
- Binary file stream with appropriate Content-Type header
- `Content-Disposition: attachment; filename="contract.pdf"`

**Status Codes:**
- `200 OK` - File downloaded successfully
- `404 Not Found` - Document not found
- `500 Internal Server Error` - Download or storage error

### 5. Delete Document

**DELETE** `/api/v1/documents/{document_id}`

Delete a document from both storage and database. This action cannot be undone.

**Parameters:**
- `document_id` (path) - ID of the document

**Response:**
```json
{
  "id": 1,
  "filename": "contract.pdf",
  "message": "Document 'contract.pdf' deleted successfully"
}
```

**Status Codes:**
- `200 OK` - Document deleted successfully
- `404 Not Found` - Document not found
- `500 Internal Server Error` - Deletion error

## Document Processing Flow

1. **Upload**
   - User uploads files via POST endpoint
   - Files are validated and stored in MinIO
   - Database records are created with status `PENDING`
   - Celery task is enqueued for each document

2. **Processing** (Async via Celery)
   - Task retrieves document from database
   - Status is updated to `PROCESSING`
   - Document is processed (text extraction, NLP, etc.)
   - Status is updated to `COMPLETED` or `FAILED`

3. **Access**
   - Documents can be listed, retrieved, or downloaded
   - Download streams file directly from MinIO

4. **Deletion**
   - Removes file from MinIO
   - Deletes database record (cascade deletes related data)

## Document Statuses

- `PENDING` - Document uploaded, awaiting processing
- `PROCESSING` - Document is being processed
- `COMPLETED` - Processing completed successfully
- `FAILED` - Processing failed

## Storage

### MinIO Configuration

Documents are stored in MinIO with the following structure:

```
bucket: legalease
path: cases/{case_id}/{uuid}_{filename}
```

**Environment Variables:**
- `MINIO_ENDPOINT` - MinIO server endpoint (default: localhost:9000)
- `MINIO_ACCESS_KEY` - Access key (default: minioadmin)
- `MINIO_SECRET_KEY` - Secret key (default: minioadmin)
- `MINIO_BUCKET` - Bucket name (default: legalease)
- `MINIO_SECURE` - Use HTTPS (default: false)

### Database Schema

Documents are stored in the `documents` table with relationships to:
- `cases` - Parent case (CASCADE on delete)
- `chunks` - Text chunks for embedding (CASCADE on delete)
- `entities` - Extracted entities
- `transcription` - Audio transcription (if applicable)

## Testing the API

### Using cURL

**Upload a document:**
```bash
curl -X POST "http://localhost:8000/api/v1/cases/1/documents" \
  -F "files=@/path/to/document.pdf" \
  -F "files=@/path/to/contract.docx"
```

**List documents:**
```bash
curl "http://localhost:8000/api/v1/cases/1/documents"
```

**Get document:**
```bash
curl "http://localhost:8000/api/v1/documents/1"
```

**Download document:**
```bash
curl "http://localhost:8000/api/v1/documents/1/download" -o downloaded.pdf
```

**Delete document:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/1"
```

### Using Python Requests

```python
import requests

# Upload documents
files = [
    ('files', open('contract.pdf', 'rb')),
    ('files', open('agreement.docx', 'rb'))
]
response = requests.post('http://localhost:8000/api/v1/cases/1/documents', files=files)
documents = response.json()

# List documents
response = requests.get('http://localhost:8000/api/v1/cases/1/documents')
doc_list = response.json()

# Download document
response = requests.get('http://localhost:8000/api/v1/documents/1/download')
with open('downloaded.pdf', 'wb') as f:
    f.write(response.content)
```

### Using the Interactive API Docs

Visit `http://localhost:8000/api/docs` for the interactive Swagger UI where you can test all endpoints directly from your browser.

## Error Handling

All endpoints include comprehensive error handling:

- **Validation Errors** (400) - Invalid request data
- **Not Found** (404) - Resource doesn't exist
- **Server Errors** (500) - Storage or processing errors

Errors are returned in FastAPI's standard format:
```json
{
  "detail": "Error message here"
}
```

## Future Enhancements (Phase 3)

The document processing task currently includes placeholders for:

1. **Text Extraction**
   - PDF parsing
   - DOCX parsing
   - OCR for scanned documents

2. **NLP Processing**
   - Entity extraction (parties, dates, amounts)
   - Text chunking for embeddings
   - Classification and tagging

3. **Vector Search**
   - Generate embeddings using sentence-transformers
   - Store in Qdrant vector database
   - Enable semantic search across documents

4. **Advanced Features**
   - Document comparison
   - Automatic summarization
   - Key clause identification

## Dependencies

- **FastAPI** - Web framework
- **SQLAlchemy** - Database ORM
- **MinIO** - Object storage client
- **Celery** - Task queue
- **Pydantic** - Data validation

## Files Created/Modified

1. `/home/Allie/develop/legalease/backend/app/schemas/document.py` - Created
2. `/home/Allie/develop/legalease/backend/app/core/minio_client.py` - Created
3. `/home/Allie/develop/legalease/backend/app/services/document_service.py` - Created
4. `/home/Allie/develop/legalease/backend/app/api/v1/documents.py` - Updated
5. `/home/Allie/develop/legalease/backend/app/api/v1/router.py` - Updated
6. `/home/Allie/develop/legalease/backend/app/workers/tasks/document_processing.py` - Updated

## Running the Application

1. **Start MinIO:**
   ```bash
   docker run -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ":9001"
   ```

2. **Start Redis (for Celery):**
   ```bash
   docker run -p 6379:6379 redis:alpine
   ```

3. **Start PostgreSQL:**
   ```bash
   docker run -p 5432:5432 -e POSTGRES_DB=legalease -e POSTGRES_USER=legalease -e POSTGRES_PASSWORD=legalease postgres:15
   ```

4. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start Celery worker:**
   ```bash
   celery -A app.workers.celery_app worker --loglevel=info
   ```

6. **Start FastAPI server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access the API:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/api/docs
   - MinIO Console: http://localhost:9001
