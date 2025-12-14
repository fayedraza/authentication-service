"""
Manual test script for event ingestion endpoint
"""
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from mcp_server.main import app
from mcp_server.db import SessionLocal
from mcp_server.models import MCPAuthEvent

# Create test client
client = TestClient(app)


def test_valid_event_ingestion():
    """Test ingesting a valid authentication event"""
    print("\n=== Test 1: Valid Event Ingestion ===")

    event_data = {
        "user_id": 123,
        "username": "john.doe",
        "event_type": "login_success",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "timestamp": "2024-01-15T10:30:00Z",
        "metadata": {"session_id": "abc123", "device": "desktop"}
    }

    response = client.post("/mcp/ingest", json=event_data)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert "event_id" in response.json(), "Response should contain event_id"
    assert response.json()["status"] == "accepted", "Status should be 'accepted'"

    # Verify event was stored in database
    event_id = response.json()["event_id"]
    db = SessionLocal()
    stored_event = db.query(MCPAuthEvent).filter(MCPAuthEvent.id == event_id).first()
    db.close()

    assert stored_event is not None, "Event should be stored in database"
    assert stored_event.user_id == 123, "User ID should match"
    assert stored_event.event_type == "login_success", "Event type should match"

    print("✓ Test passed: Event ingested and stored successfully")


def test_invalid_event_type():
    """Test ingesting an event with invalid event type"""
    print("\n=== Test 2: Invalid Event Type ===")

    event_data = {
        "user_id": 123,
        "username": "john.doe",
        "event_type": "invalid_event",  # Invalid event type
        "timestamp": "2024-01-15T10:30:00Z"
    }

    response = client.post("/mcp/ingest", json=event_data)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    print("✓ Test passed: Invalid event type rejected")


def test_invalid_timestamp():
    """Test ingesting an event with invalid timestamp"""
    print("\n=== Test 3: Invalid Timestamp ===")

    event_data = {
        "user_id": 123,
        "username": "john.doe",
        "event_type": "login_success",
        "timestamp": "not-a-valid-timestamp"
    }

    response = client.post("/mcp/ingest", json=event_data)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    print("✓ Test passed: Invalid timestamp rejected")


def test_missing_required_fields():
    """Test ingesting an event with missing required fields"""
    print("\n=== Test 4: Missing Required Fields ===")

    event_data = {
        "user_id": 123,
        # Missing username, event_type, and timestamp
    }

    response = client.post("/mcp/ingest", json=event_data)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    print("✓ Test passed: Missing required fields rejected")


def test_optional_fields():
    """Test ingesting an event with only required fields"""
    print("\n=== Test 5: Optional Fields ===")

    event_data = {
        "user_id": 456,
        "username": "jane.smith",
        "event_type": "2fa_success",
        "timestamp": "2024-01-15T11:00:00Z"
        # No ip_address, user_agent, or metadata
    }

    response = client.post("/mcp/ingest", json=event_data)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    print("✓ Test passed: Event with only required fields accepted")


if __name__ == "__main__":
    print("Starting MCP Server Event Ingestion Tests")
    print("=" * 50)

    try:
        test_valid_event_ingestion()
        test_invalid_event_type()
        test_invalid_timestamp()
        test_missing_required_fields()
        test_optional_fields()

        print("\n" + "=" * 50)
        print("✓ All tests passed!")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
