"""
Manual test script for event query endpoint
"""
import sys
import json
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from mcp_server.main import app
from mcp_server.db import SessionLocal
from mcp_server.models import MCPAuthEvent

# Create test client
client = TestClient(app)


def setup_test_data():
    """Create test events in the database"""
    print("\n=== Setting up test data ===")

    db = SessionLocal()

    # Clear existing test data
    db.query(MCPAuthEvent).delete()
    db.commit()

    # Create test events
    base_time = datetime.utcnow()

    test_events = [
        # User 123 events
        MCPAuthEvent(
            user_id=123,
            username="john.doe",
            event_type="login_success",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(hours=5),
            event_metadata={"device": "desktop"}
        ),
        MCPAuthEvent(
            user_id=123,
            username="john.doe",
            event_type="login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(hours=4),
            event_metadata={"reason": "wrong_password"}
        ),
        MCPAuthEvent(
            user_id=123,
            username="john.doe",
            event_type="2fa_success",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(hours=3),
            event_metadata={}
        ),
        # User 456 events
        MCPAuthEvent(
            user_id=456,
            username="jane.smith",
            event_type="login_success",
            ip_address="10.0.0.50",
            user_agent="Chrome/91.0",
            timestamp=base_time - timedelta(hours=2),
            event_metadata={"device": "mobile"}
        ),
        MCPAuthEvent(
            user_id=456,
            username="jane.smith",
            event_type="password_reset",
            ip_address="10.0.0.50",
            user_agent="Chrome/91.0",
            timestamp=base_time - timedelta(hours=1),
            event_metadata={}
        ),
    ]

    for event in test_events:
        db.add(event)

    db.commit()
    db.close()

    print(f"✓ Created {len(test_events)} test events")
    return base_time


def test_get_all_events():
    """Test retrieving all events without filters"""
    print("\n=== Test 1: Get All Events ===")

    response = client.get("/mcp/events")

    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Total events: {data['total']}")
    print(f"Returned events: {len(data['events'])}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data['total'] >= 5, f"Expected at least 5 events, got {data['total']}"
    assert len(data['events']) >= 5, f"Expected at least 5 events returned"
    assert 'limit' in data, "Response should contain limit"
    assert 'offset' in data, "Response should contain offset"

    print("✓ Test passed: Retrieved all events successfully")


def test_filter_by_user_id():
    """Test filtering events by user_id"""
    print("\n=== Test 2: Filter by User ID ===")

    response = client.get("/mcp/events?user_id=123")

    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Total events for user 123: {data['total']}")
    print(f"Returned events: {len(data['events'])}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data['total'] == 3, f"Expected 3 events for user 123, got {data['total']}"

    # Verify all returned events are for user 123
    for event in data['events']:
        assert event['user_id'] == 123, f"Expected user_id 123, got {event['user_id']}"

    print("✓ Test passed: Filtered by user_id successfully")


def test_filter_by_event_type():
    """Test filtering events by event_type"""
    print("\n=== Test 3: Filter by Event Type ===")

    response = client.get("/mcp/events?event_type=login_success")

    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Total login_success events: {data['total']}")
    print(f"Returned events: {len(data['events'])}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data['total'] == 2, f"Expected 2 login_success events, got {data['total']}"

    # Verify all returned events are login_success
    for event in data['events']:
        assert event['event_type'] == "login_success", f"Expected login_success, got {event['event_type']}"

    print("✓ Test passed: Filtered by event_type successfully")


def test_filter_by_timestamp_range(base_time):
    """Test filtering events by timestamp range"""
    print("\n=== Test 4: Filter by Timestamp Range ===")

    # Get events from last 3 hours
    start_date = (base_time - timedelta(hours=3)).isoformat() + 'Z'

    response = client.get(f"/mcp/events?start_date={start_date}")

    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Total events in range: {data['total']}")
    print(f"Returned events: {len(data['events'])}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data['total'] == 3, f"Expected 3 events in range, got {data['total']}"

    print("✓ Test passed: Filtered by timestamp range successfully")


def test_pagination():
    """Test pagination with limit and offset"""
    print("\n=== Test 5: Pagination ===")

    # Get first 2 events
    response1 = client.get("/mcp/events?limit=2&offset=0")
    data1 = response1.json()

    print(f"Page 1 - Status Code: {response1.status_code}")
    print(f"Page 1 - Returned events: {len(data1['events'])}")
    print(f"Page 1 - Total: {data1['total']}")

    assert response1.status_code == 200, f"Expected 200, got {response1.status_code}"
    assert len(data1['events']) == 2, f"Expected 2 events, got {len(data1['events'])}"
    assert data1['limit'] == 2, f"Expected limit 2, got {data1['limit']}"
    assert data1['offset'] == 0, f"Expected offset 0, got {data1['offset']}"

    # Get next 2 events
    response2 = client.get("/mcp/events?limit=2&offset=2")
    data2 = response2.json()

    print(f"Page 2 - Status Code: {response2.status_code}")
    print(f"Page 2 - Returned events: {len(data2['events'])}")

    assert response2.status_code == 200, f"Expected 200, got {response2.status_code}"
    assert len(data2['events']) == 2, f"Expected 2 events, got {len(data2['events'])}"
    assert data2['offset'] == 2, f"Expected offset 2, got {data2['offset']}"

    # Verify different events returned
    page1_ids = {e['id'] for e in data1['events']}
    page2_ids = {e['id'] for e in data2['events']}
    assert page1_ids.isdisjoint(page2_ids), "Pages should return different events"

    print("✓ Test passed: Pagination works correctly")


def test_combined_filters():
    """Test combining multiple filters"""
    print("\n=== Test 6: Combined Filters ===")

    response = client.get("/mcp/events?user_id=123&event_type=login_failure")

    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Total events: {data['total']}")
    print(f"Returned events: {len(data['events'])}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data['total'] == 1, f"Expected 1 event, got {data['total']}"

    # Verify the event matches both filters
    event = data['events'][0]
    assert event['user_id'] == 123, f"Expected user_id 123, got {event['user_id']}"
    assert event['event_type'] == "login_failure", f"Expected login_failure, got {event['event_type']}"

    print("✓ Test passed: Combined filters work correctly")


def test_invalid_timestamp_format():
    """Test with invalid timestamp format"""
    print("\n=== Test 7: Invalid Timestamp Format ===")

    response = client.get("/mcp/events?start_date=invalid-timestamp")

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    print("✓ Test passed: Invalid timestamp rejected")


def test_event_ordering():
    """Test that events are ordered by timestamp descending"""
    print("\n=== Test 8: Event Ordering ===")

    response = client.get("/mcp/events")

    print(f"Status Code: {response.status_code}")
    data = response.json()

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(data['events']) >= 2, "Need at least 2 events to test ordering"

    # Verify events are in descending order by timestamp
    timestamps = [datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) for e in data['events']]
    for i in range(len(timestamps) - 1):
        assert timestamps[i] >= timestamps[i + 1], "Events should be ordered by timestamp descending"

    print("✓ Test passed: Events are correctly ordered")


if __name__ == "__main__":
    print("Starting MCP Server Event Query Tests")
    print("=" * 50)

    try:
        base_time = setup_test_data()

        test_get_all_events()
        test_filter_by_user_id()
        test_filter_by_event_type()
        test_filter_by_timestamp_range(base_time)
        test_pagination()
        test_combined_filters()
        test_invalid_timestamp_format()
        test_event_ordering()

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
