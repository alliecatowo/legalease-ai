"""
Simple standalone MinIO test without full app dependencies
"""
import sys
from io import BytesIO

# Test imports
print("Testing imports...")
try:
    from minio import Minio
    print("  - minio: OK")
except ImportError as e:
    print(f"  - minio: FAILED - {e}")
    print("\nPlease run: uv sync")
    sys.exit(1)

# Test MinIO connection
print("\nTesting MinIO connection...")
try:
    client = Minio(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False,
    )

    # List buckets to test connection
    buckets = client.list_buckets()
    print(f"  Connection successful! Found {len(buckets)} bucket(s)")

    # Test bucket creation
    test_bucket = "test-case-999"
    print(f"\nTesting bucket operations with '{test_bucket}'...")

    # Create bucket if it doesn't exist
    if not client.bucket_exists(test_bucket):
        client.make_bucket(test_bucket)
        print("  - Created bucket")
    else:
        print("  - Bucket already exists")

    # Upload a test file
    test_content = b"This is a test document"
    test_filename = "test.txt"
    client.put_object(
        bucket_name=test_bucket,
        object_name=test_filename,
        data=BytesIO(test_content),
        length=len(test_content),
        content_type="text/plain",
    )
    print(f"  - Uploaded '{test_filename}'")

    # Download the file
    response = client.get_object(test_bucket, test_filename)
    downloaded_content = response.read()
    response.close()
    response.release_conn()
    print(f"  - Downloaded '{test_filename}' ({len(downloaded_content)} bytes)")
    print(f"  - Content matches: {downloaded_content == test_content}")

    # Get presigned URL
    from datetime import timedelta
    url = client.presigned_get_object(test_bucket, test_filename, expires=timedelta(hours=1))
    print(f"  - Generated presigned URL: {url[:80]}...")

    # List objects
    objects = list(client.list_objects(test_bucket))
    print(f"  - Listed {len(objects)} object(s) in bucket")

    # Delete the file
    client.remove_object(test_bucket, test_filename)
    print(f"  - Deleted '{test_filename}'")

    # Delete the bucket
    client.remove_bucket(test_bucket)
    print(f"  - Deleted bucket")

    print("\nAll tests passed!")

except Exception as e:
    print(f"  FAILED: {e}")
    print("\nMake sure MinIO is running on localhost:9000")
    print("You can start it with: docker run -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ':9001'")
    import traceback
    traceback.print_exc()
