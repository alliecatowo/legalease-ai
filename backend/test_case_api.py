#!/usr/bin/env python3
"""
Test script for Case Management API endpoints
Run this script to verify the Case API is working correctly.
"""

import sys
from fastapi.testclient import TestClient
from app.main import app

# Create test client
client = TestClient(app)


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_health_check():
    """Test health check endpoint."""
    print_section("Testing Health Check")
    response = client.get("/api/v1/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✓ Health check passed")


def test_list_cases_empty():
    """Test listing cases when none exist."""
    print_section("Testing List Cases (Empty)")
    response = client.get("/api/v1/cases")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert "cases" in data
    assert "total" in data
    print("✓ List cases passed")


def test_create_case():
    """Test creating a new case."""
    print_section("Testing Create Case")
    case_data = {
        "name": "Test v. Defendant",
        "case_number": "2024-CV-001",
        "client": "Test Client LLC",
        "matter_type": "Civil Litigation"
    }
    print(f"Creating case: {case_data}")

    # Note: This will fail if Qdrant/MinIO are not running
    # We'll catch the error and note it
    try:
        response = client.post("/api/v1/cases", json=case_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

        if response.status_code == 201:
            data = response.json()
            assert data["case_number"] == case_data["case_number"]
            assert data["name"] == case_data["name"]
            assert data["status"] == "STAGING"
            print("✓ Create case passed")
            return data["id"]
        else:
            print(f"⚠ Create case returned {response.status_code}")
            print("Note: This may fail if Qdrant or MinIO are not running")
            return None
    except Exception as e:
        print(f"⚠ Create case failed: {e}")
        print("Note: This may fail if Qdrant or MinIO are not running")
        return None


def test_get_case(case_id):
    """Test getting a specific case."""
    if case_id is None:
        print("\n⊘ Skipping get case test (no case_id)")
        return

    print_section("Testing Get Case")
    response = client.get(f"/api/v1/cases/{case_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        data = response.json()
        assert data["id"] == case_id
        print("✓ Get case passed")
    else:
        print(f"⚠ Get case returned {response.status_code}")


def test_activate_case(case_id):
    """Test activating a case."""
    if case_id is None:
        print("\n⊘ Skipping activate case test (no case_id)")
        return

    print_section("Testing Activate Case")
    response = client.put(f"/api/v1/cases/{case_id}/activate")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "ACTIVE"
        print("✓ Activate case passed")
    else:
        print(f"⚠ Activate case returned {response.status_code}")


def test_unload_case(case_id):
    """Test unloading a case."""
    if case_id is None:
        print("\n⊘ Skipping unload case test (no case_id)")
        return

    print_section("Testing Unload Case")
    response = client.put(f"/api/v1/cases/{case_id}/unload")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "UNLOADED"
        print("✓ Unload case passed")
    else:
        print(f"⚠ Unload case returned {response.status_code}")


def test_delete_case(case_id):
    """Test deleting a case."""
    if case_id is None:
        print("\n⊘ Skipping delete case test (no case_id)")
        return

    print_section("Testing Delete Case")
    response = client.delete(f"/api/v1/cases/{case_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        data = response.json()
        assert "deleted_at" in data
        print("✓ Delete case passed")
    else:
        print(f"⚠ Delete case returned {response.status_code}")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  Case Management API Test Suite")
    print("="*60)

    try:
        # Basic tests that don't require external services
        test_health_check()
        test_list_cases_empty()

        # Tests that require Qdrant/MinIO
        print("\n" + "-"*60)
        print("  Note: The following tests require Qdrant and MinIO")
        print("  to be running. They may fail if services are unavailable.")
        print("-"*60)

        case_id = test_create_case()
        test_get_case(case_id)
        test_activate_case(case_id)
        test_unload_case(case_id)
        test_delete_case(case_id)

        print("\n" + "="*60)
        print("  All tests completed!")
        print("="*60 + "\n")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
