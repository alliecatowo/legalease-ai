# MinIO Object Storage Integration

This document describes the MinIO object storage integration for the LegalEase backend.

## Overview

The MinIO integration provides secure, scalable object storage for case documents. Files are organized in case-specific buckets with the naming convention `case-{case_id}`.

## Architecture

### Components

1. **MinioClient** (`app/core/minio.py`) - Low-level MinIO client singleton
2. **StorageService** (`app/services/storage_service.py`) - High-level storage service

## Configuration

MinIO settings are configured in `.env`:

```env
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=False
```

## Usage Examples

### Basic Storage Operations

```python
from app.services.storage_service import storage_service
from io import BytesIO

# Store a document
with open("contract.pdf", "rb") as f:
    content = f.read()
    file_data = BytesIO(content)

    success = storage_service.store_document(
        case_id=123,
        file=file_data,
        filename="contract.pdf",
        file_size=len(content),
        content_type="application/pdf"
    )

# Retrieve a document
file_data = storage_service.retrieve_document(
    case_id=123,
    filename="contract.pdf"
)
if file_data:
    # Process the file
    content = file_data.read()

# List case files
files = storage_service.list_case_files(case_id=123)
for file_info in files:
    print(f"{file_info['name']}: {file_info['size']} bytes")

# Delete a document
success = storage_service.delete_document(
    case_id=123,
    filename="contract.pdf"
)
```

### Progress Tracking

```python
def progress_callback(bytes_uploaded):
    print(f"Uploaded {bytes_uploaded} bytes")

storage_service.store_document(
    case_id=123,
    file=file_data,
    filename="large_file.pdf",
    file_size=file_size,
    progress_callback=progress_callback
)
```

### Temporary Access URLs

```python
from datetime import timedelta

# Generate a presigned URL valid for 2 hours
url = storage_service.get_temporary_url(
    case_id=123,
    filename="contract.pdf",
    expiry=timedelta(hours=2)
)

# Share this URL with clients for temporary access
print(f"Download URL: {url}")
```

### Document Metadata

```python
metadata = storage_service.get_document_metadata(
    case_id=123,
    filename="contract.pdf"
)

if metadata:
    print(f"Name: {metadata['name']}")
    print(f"Size: {metadata['size']} bytes")
    print(f"Last Modified: {metadata['last_modified']}")
    print(f"ETag: {metadata['etag']}")
```

### Cleanup

```python
# Delete all documents and the bucket for a case
success = storage_service.delete_case_storage(case_id=123)
```

## Low-Level MinIO Client

For advanced use cases, you can use the MinioClient directly:

```python
from app.core.minio import minio_client

# Create a custom bucket
minio_client.create_bucket("custom-bucket")

# Upload with custom parameters
minio_client.upload_file(
    bucket_name="custom-bucket",
    object_name="document.pdf",
    file_data=file_data,
    file_size=file_size,
    content_type="application/pdf"
)

# List objects with prefix
objects = minio_client.list_objects(
    bucket_name="case-123",
    prefix="contracts/"
)
```

## FastAPI Integration Example

```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.storage_service import storage_service

router = APIRouter()

@router.post("/cases/{case_id}/documents")
async def upload_document(
    case_id: int,
    file: UploadFile = File(...)
):
    """Upload a document to a case"""
    try:
        # Read file content
        content = await file.read()
        file_data = BytesIO(content)

        # Store the document
        success = storage_service.store_document(
            case_id=case_id,
            file=file_data,
            filename=file.filename,
            file_size=len(content),
            content_type=file.content_type or "application/octet-stream"
        )

        if success:
            return {"message": "Document uploaded successfully"}
        else:
            raise HTTPException(status_code=500, detail="Upload failed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cases/{case_id}/documents/{filename}")
async def download_document(case_id: int, filename: str):
    """Download a document from a case"""
    from fastapi.responses import StreamingResponse

    file_data = storage_service.retrieve_document(case_id, filename)
    if not file_data:
        raise HTTPException(status_code=404, detail="Document not found")

    return StreamingResponse(
        file_data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/cases/{case_id}/documents")
async def list_documents(case_id: int):
    """List all documents for a case"""
    files = storage_service.list_case_files(case_id)
    return {"files": files}

@router.delete("/cases/{case_id}/documents/{filename}")
async def delete_document(case_id: int, filename: str):
    """Delete a document from a case"""
    success = storage_service.delete_document(case_id, filename)
    if success:
        return {"message": "Document deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Deletion failed")

@router.get("/cases/{case_id}/documents/{filename}/url")
async def get_document_url(case_id: int, filename: str):
    """Get a temporary download URL for a document"""
    url = storage_service.get_temporary_url(case_id, filename)
    if url:
        return {"url": url}
    else:
        raise HTTPException(status_code=404, detail="Document not found")
```

## Testing

### Start MinIO

Using Docker:
```bash
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ':9001'
```

### Run Tests

```bash
# Simple test (requires MinIO to be running)
python test_minio_simple.py

# Full integration test (requires all dependencies)
python test_minio_integration.py
```

## Bucket Naming Convention

- Format: `case-{case_id}`
- Example: `case-123`, `case-456`
- Each case has its own isolated bucket
- Buckets are created automatically when storing the first document

## Best Practices

1. **Always check return values** - All methods return boolean success indicators
2. **Handle file cleanup** - Delete documents when cases are closed
3. **Use temporary URLs** - For sharing documents with external clients
4. **Set appropriate content types** - Helps with browser handling
5. **Monitor storage usage** - Track bucket sizes for billing/capacity planning
6. **Implement access control** - Validate case access before serving documents

## Error Handling

All operations log errors and return `None` or `False` on failure:

```python
file_data = storage_service.retrieve_document(case_id, filename)
if file_data is None:
    # Handle error - document not found or storage error
    logger.error(f"Failed to retrieve document {filename}")
    return {"error": "Document not available"}
```

## Security Considerations

1. **Access Control** - Implement case-level access control in your API
2. **Presigned URLs** - Set appropriate expiry times (default: 1 hour)
3. **File Validation** - Validate file types and sizes before upload
4. **Secure Connection** - Use `MINIO_SECURE=True` in production with HTTPS
5. **Credentials** - Store credentials securely, never commit to version control

## Performance Tips

1. **Connection Pooling** - MinioClient is a singleton, reuse the instance
2. **Async Operations** - Consider using async wrappers for large file operations
3. **Chunked Uploads** - For very large files, implement chunked upload
4. **Caching** - Cache file metadata to reduce MinIO API calls
5. **CDN Integration** - Use presigned URLs with CDN for frequently accessed files
