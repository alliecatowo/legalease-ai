"""
Test script for MinIO integration
"""
from io import BytesIO
from app.services.storage_service import storage_service


def test_storage_operations():
    """Test basic storage operations"""
    print("Testing MinIO Storage Integration...")
    print("-" * 50)

    case_id = 123
    test_filename = "test_document.txt"
    test_content = b"This is a test document for LegalEase case management."

    # Test 1: Store a document
    print(f"\n1. Storing document '{test_filename}' for case {case_id}...")
    file_data = BytesIO(test_content)
    success = storage_service.store_document(
        case_id=case_id,
        file=file_data,
        filename=test_filename,
        file_size=len(test_content),
        content_type="text/plain",
    )
    print(f"   Result: {'SUCCESS' if success else 'FAILED'}")

    # Test 2: List case files
    print(f"\n2. Listing files for case {case_id}...")
    files = storage_service.list_case_files(case_id)
    print(f"   Found {len(files)} file(s):")
    for file_info in files:
        print(f"   - {file_info['name']} ({file_info['size']} bytes)")

    # Test 3: Retrieve the document
    print(f"\n3. Retrieving document '{test_filename}'...")
    retrieved_data = storage_service.retrieve_document(case_id, test_filename)
    if retrieved_data:
        content = retrieved_data.read()
        print(f"   Retrieved {len(content)} bytes")
        print(f"   Content matches: {content == test_content}")
    else:
        print("   FAILED to retrieve document")

    # Test 4: Get temporary URL
    print(f"\n4. Generating temporary URL for '{test_filename}'...")
    url = storage_service.get_temporary_url(case_id, test_filename)
    if url:
        print(f"   URL: {url[:80]}...")
    else:
        print("   FAILED to generate URL")

    # Test 5: Get document metadata
    print(f"\n5. Getting metadata for '{test_filename}'...")
    metadata = storage_service.get_document_metadata(case_id, test_filename)
    if metadata:
        print(f"   Name: {metadata['name']}")
        print(f"   Size: {metadata['size']} bytes")
        print(f"   Last Modified: {metadata['last_modified']}")
    else:
        print("   FAILED to get metadata")

    # Test 6: Delete the document
    print(f"\n6. Deleting document '{test_filename}'...")
    success = storage_service.delete_document(case_id, test_filename)
    print(f"   Result: {'SUCCESS' if success else 'FAILED'}")

    # Test 7: Verify deletion
    print(f"\n7. Verifying deletion...")
    files = storage_service.list_case_files(case_id)
    print(f"   Files remaining: {len(files)}")

    # Test 8: Clean up - delete bucket
    print(f"\n8. Cleaning up case storage...")
    success = storage_service.delete_case_storage(case_id)
    print(f"   Result: {'SUCCESS' if success else 'FAILED'}")

    print("\n" + "-" * 50)
    print("Testing complete!")


if __name__ == "__main__":
    try:
        test_storage_operations()
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
