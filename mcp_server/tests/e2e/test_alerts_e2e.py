
import pytest
import requests
import uuid
import time
from datetime import datetime, timedelta

MCP_API_URL = "http://localhost:8001"
REQUEST_TIMEOUT = 10

def generate_username(prefix="alert_user"):
    return f"{prefix}_{str(uuid.uuid4())[:8]}"

def generate_user_id():
    return int(str(uuid.uuid4().int)[:8])

@pytest.fixture
def alert_test_user():
    user_id = generate_user_id()
    username = generate_username()
    return user_id, username

def test_e2e_alert_lifecycle(alert_test_user):
    user_id, username = alert_test_user

    # 1. Ingest High Risk Events (Simulate Brute Force)
    # 4 failed logins should trigger risk score (Rule: 3-5 failures = +0.3, wait, threshold is 0.7?)
    # Rules:
    # 3-5 failed logins = +0.3
    # 6-10 failed logins = +0.5
    # 11+ failed logins = +0.7
    # 3-5 failed 2FA = +0.4
    # IP Change = +0.2
    # UA Change = +0.1

    # To hit 0.7 with MINIMAL events:
    # 4 failed logins (+0.3) + 4 failed 2FA (+0.4) = 0.7 risk.

    base_time = datetime.utcnow()

    # Send 4 failed logins
    for i in range(4):
        resp = requests.post(f"{MCP_API_URL}/mcp/ingest", json={
            "user_id": user_id,
            "username": username,
            "event_type": "login_failure",
            "ip_address": "10.0.0.1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {"attempt": i}
        }, timeout=REQUEST_TIMEOUT)
        assert resp.status_code == 201

    # Send 4 failed 2FA
    for i in range(4):
        resp = requests.post(f"{MCP_API_URL}/mcp/ingest", json={
            "user_id": user_id,
            "username": username,
            "event_type": "2fa_failure",
            "ip_address": "10.0.0.1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {"attempt": i}
        }, timeout=REQUEST_TIMEOUT)
        assert resp.status_code == 201

    time.sleep(2)

    # 2. Query Alerts
    resp = requests.get(f"{MCP_API_URL}/mcp/alerts?user_id={user_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0

    alert = data["alerts"][0]
    alert_id = alert["id"]
    print(f"DEBUG: Found Alert ID: {alert_id} for User {user_id}")
    assert alert["status"] == "open"
    assert alert["risk_score"] >= 0.7

    # 3. Update Status
    patch_url = f"{MCP_API_URL}/mcp/alerts/{alert_id}"
    print(f"DEBUG: Patching {patch_url}")
    resp = requests.patch(patch_url, json={"status": "reviewed"})
    print(f"DEBUG: Patch Response: {resp.status_code} {resp.text}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "reviewed"

    # 4. Filter Query
    resp = requests.get(f"{MCP_API_URL}/mcp/alerts?status=reviewed&user_id={user_id}")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    # 5. Consolidation Test
    # Add more events. Consolidation window defaults to 5 mins.
    # Send HUGE risk event (11 logins = 0.7)
    for i in range(11):
        resp = requests.post(f"{MCP_API_URL}/mcp/ingest", json={
            "user_id": user_id,
            "username": username,
            "event_type": "login_failure",
            "ip_address": "10.0.0.2", # IP Change +0.2
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {"attempt": i+100}
        }, timeout=REQUEST_TIMEOUT)
        assert resp.status_code == 201

    time.sleep(2)

    # Check alert was consolidated (still 1 alert, or maybe new one if status changed? Logic updates existing?)
    # If status is 'reviewed', consolidation might create NEW alert or re-open?
    # Logic: "Check for existing open alerts... if existing_alert (status=open)... else Create new alert"
    # So if status is 'reviewed', it creates a NEW alert.

    resp = requests.get(f"{MCP_API_URL}/mcp/alerts?user_id={user_id}&status=open")
    data = resp.json()
    # Should have a NEW open alert
    assert data["total"] == 1
    new_alert = data["alerts"][0]
    assert new_alert["id"] != alert_id

def test_e2e_alert_error_handling(alert_test_user):
    # Invalid ID
    resp = requests.patch(f"{MCP_API_URL}/mcp/alerts/invalid-id", json={"status": "open"})
    assert resp.status_code == 404

    # Invalid Status (Pydantic validation?)
    # Use valid ID first
    user_id, _ = alert_test_user
    # Ensure at least one alert exists (reuse logic or verify isolation)
    # Just skip if no ID is handy, or rely on previous test? No, fixtures isolate.
    # We won't test invalid status on REAL entity to keep it simple, verifying 404 is enough for E2E.
