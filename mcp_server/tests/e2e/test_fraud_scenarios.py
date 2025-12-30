"""
Component/E2E tests for Fraud Detection scenarios.
Targeting the running MCP Server at localhost:8001.
"""
import pytest
import requests
import time
import uuid
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001"
REQUEST_TIMEOUT = 30

def generate_user_data():
    """Generate unique user data for testing"""
    uid = str(uuid.uuid4())[:8]
    return {
        "user_id": int(uuid.uuid4().int % 1000000),  # Random integer ID
        "username": f"test_comp_{uid}"
    }

def test_brute_force_detection_component():
    """
    Verify that the system detects a brute force attack pattern.

    Scenario:
    1. Sends multiple failed login attempts (simulating brute force).
    2. Sends a login attempt from a new IP.
    3. Verifies that the fraud assessment returns high risk.
    """
    user_data = generate_user_data()
    user_id = user_data["user_id"]
    username = user_data["username"]

    print(f"\n[Component Test] Testing brute force detection for user: {username} ({user_id})")

    # 1. Send normal baseline event (optional, but realistic)
    requests.post(f"{BASE_URL}/mcp/ingest", json={
        "user_id": user_id,
        "username": username,
        "event_type": "login_success",
        "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0",
        "metadata": {}
    }, timeout=REQUEST_TIMEOUT)
    time.sleep(0.5)

    # 2. Attack Phase: Multiple failed logins
    print("  -> Sending failed login attempts...")
    for i in range(6):
        resp = requests.post(f"{BASE_URL}/mcp/ingest", json={
            "user_id": user_id,
            "username": username,
            "event_type": "login_failure",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "ip_address": "203.0.113.55",  # Attacker IP
            "user_agent": "Bot/1.0",
            "metadata": {"attempt": i+1}
        }, timeout=REQUEST_TIMEOUT)
        assert resp.status_code == 201

    # Allow async processing
    time.sleep(2)

    # 3. Verify Assessment
    print("  -> Verifying fraud assessment...")
    resp = requests.get(f"{BASE_URL}/mcp/fraud-assessments", params={"user_id": user_id}, timeout=REQUEST_TIMEOUT)
    assert resp.status_code == 200

    data = resp.json()
    assessments = data.get("assessments", [])
    assert len(assessments) > 0, "No fraud assessments found for test user"

    latest_assessment = assessments[0]
    risk_score = latest_assessment["risk_score"]
    reason = latest_assessment["reason"]

    print(f"     Risk Score: {risk_score}")
    print(f"     Reason:     {reason}")

    # Assertions
    # 6 failures triggers rule (+0.3 or similar high score) + IP change (+0.2)
    # Expecting at least 0.5, likely higher (0.7 threshold for alert)
    assert risk_score >= 0.5, f"Risk score {risk_score} is too low for brute force attack"

    # Verify reason contains key terms
    reason_lower = reason.lower()
    assert "failed" in reason_lower, "Reason should mention failed attempts"
    assert "login" in reason_lower, "Reason should mention login"

    print("✅ Component Test Passed: Brute force detected successfully.")

def test_normal_login_flow():
    """Verify that a normal login does NOT trigger high risk."""
    user_data = generate_user_data()
    user_id = user_data["user_id"]
    username = user_data["username"]

    requests.post(f"{BASE_URL}/mcp/ingest", json={
        "user_id": user_id,
        "username": username,
        "event_type": "login_success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "ip_address": "10.0.0.1",
        "user_agent": "SafeBrowser/1.0",
        "metadata": {}
    }, timeout=REQUEST_TIMEOUT)

    time.sleep(1)

    resp = requests.get(f"{BASE_URL}/mcp/fraud-assessments", params={"user_id": user_id}, timeout=REQUEST_TIMEOUT)
    assessments = resp.json().get("assessments", [])

    # Assessment might exist but score should be low
    if assessments:
        score = assessments[0]["risk_score"]
        assert score < 0.3, f"Normal login should have low risk, got {score}"
        print(f"\n[Component Test] Normal login check passed (Risk: {score})")
    else:
        print("\n[Component Test] Normal login check passed (No risk assessment created)")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
