
import pytest
import requests
import uuid
import time
from datetime import datetime, timedelta

MCP_API_URL = "http://localhost:8001"
REQUEST_TIMEOUT = 10

def generate_user_id():
    return int(str(uuid.uuid4().int)[:8])

@pytest.fixture
def query_test_data():
    """Setup isolated test data for query tests"""
    user_id_1 = generate_user_id()
    user_id_2 = generate_user_id()
    base_time = datetime.utcnow()

    # Ingest events for User 1
    events_u1 = [
        ("login_success", base_time - timedelta(hours=5)),
        ("login_failure", base_time - timedelta(hours=4)),
        ("2fa_success", base_time - timedelta(hours=3)),
    ]
    for et, ts in events_u1:
        requests.post(f"{MCP_API_URL}/mcp/ingest", json={
            "user_id": user_id_1,
            "username": f"user_{user_id_1}",
            "event_type": et,
            "timestamp": ts.isoformat() + "Z",
            "metadata": {"test_set": "query_e2e"}
        }, timeout=REQUEST_TIMEOUT)

    # Ingest events for User 2
    events_u2 = [
        ("login_success", base_time - timedelta(hours=2)),
        ("password_reset", base_time - timedelta(hours=1)),
    ]
    for et, ts in events_u2:
        requests.post(f"{MCP_API_URL}/mcp/ingest", json={
            "user_id": user_id_2,
            "username": f"user_{user_id_2}",
            "event_type": et,
            "timestamp": ts.isoformat() + "Z",
            "metadata": {"test_set": "query_e2e"}
        }, timeout=REQUEST_TIMEOUT)

    # Wait for processing
    time.sleep(1)

    return {
        "user_1": user_id_1,
        "user_2": user_id_2,
        "base_time": base_time
    }

def test_e2e_filter_by_user_id(query_test_data):
    uid = query_test_data["user_1"]
    resp = requests.get(f"{MCP_API_URL}/mcp/events?user_id={uid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for ev in data["events"]:
        assert ev["user_id"] == uid

def test_e2e_filter_by_event_type(query_test_data):
    # This might pick up events from other tests, so we filter by user_id too to be safe,
    # OR we rely on the fact that we just created these.
    # To be robust in a shared env, better to filter by user_id AND event_type,
    # but the API allows single filtering. We verify functionality, not strict total count of whole DB.

    uid = query_test_data["user_1"]
    resp = requests.get(f"{MCP_API_URL}/mcp/events?user_id={uid}&event_type=login_success")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["events"][0]["event_type"] == "login_success"

def test_e2e_filter_by_timestamp(query_test_data):
    base_time = query_test_data["base_time"]
    uid = query_test_data["user_1"]
    # Filter last 3.5 hours (should include 2fa_success (3h ago) but exclude login_failure (4h ago)?)
    # Wait, created: 5h, 4h, 3h.
    # Start date = 3.5h ago. Should math 3h only.
    start_date = (base_time - timedelta(hours=3, minutes=30)).isoformat() + "Z"

    resp = requests.get(f"{MCP_API_URL}/mcp/events?user_id={uid}&start_date={start_date}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["events"][0]["event_type"] == "2fa_success"

def test_e2e_pagination(query_test_data):
    uid = query_test_data["user_1"]
    # Total 3 events. Limit 2.
    resp = requests.get(f"{MCP_API_URL}/mcp/events?user_id={uid}&limit=2&offset=0")
    data1 = resp.json()
    assert len(data1["events"]) == 2

    resp = requests.get(f"{MCP_API_URL}/mcp/events?user_id={uid}&limit=2&offset=2")
    data2 = resp.json()
    assert len(data2["events"]) == 1

    # Ensure no overlap
    ids1 = {e["id"] for e in data1["events"]}
    ids2 = {e["id"] for e in data2["events"]}
    assert ids1.isdisjoint(ids2)

def test_e2e_event_ordering(query_test_data):
    uid = query_test_data["user_1"]
    resp = requests.get(f"{MCP_API_URL}/mcp/events?user_id={uid}")
    events = resp.json()["events"]

    # Check descending timestamp
    dates = [datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) for e in events]
    for i in range(len(dates)-1):
        assert dates[i] >= dates[i+1]
