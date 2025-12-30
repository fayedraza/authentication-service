
import pytest
import time
import requests
import subprocess
import uuid
from datetime import datetime, timedelta
import random

# Configuration
MCP_API_URL = "http://localhost:8001"
CONTAINER_NAME = "authenicationservice-mcp-server-1"
REQUEST_TIMEOUT = 10

def get_container_logs():
    """Retrieve logs from the running MCP server container."""
    try:
        result = subprocess.check_output(
            ["docker", "logs", CONTAINER_NAME],
            stderr=subprocess.STDOUT
        )
        return result.decode("utf-8")
    except subprocess.CalledProcessError as e:
        print(f"Error getting logs: {e.output.decode('utf-8')}")
        raise

def generate_username(prefix="user"):
    """Generate a unique username to avoid log collisions."""
    return f"{prefix}_{str(uuid.uuid4())[:8]}"

def test_e2e_email_notification_brute_force():
    """
    Test that email notification logs appear when a brute force attack is detected.
    Replaces: test_email_notification_logging_for_brute_force_attack
    """
    username = generate_username("brute_force")
    user_id = 9001
    base_time = datetime.utcnow()

    print(f"\n[Test] Brute Force - User: {username}")

    # Send 12 failed login attempts
    for i in range(12):
        event_data = {
            "user_id": user_id,
            "username": username,
            "event_type": "login_failure",
            "timestamp": (base_time + timedelta(seconds=i)).isoformat() + "Z",
            "ip_address": "10.0.0.100",
            "user_agent": "AttackBot/1.0",
            "metadata": {"attempt": i + 1}
        }
        resp = requests.post(f"{MCP_API_URL}/mcp/ingest", json=event_data, timeout=REQUEST_TIMEOUT)
        assert resp.status_code == 201

    # Wait for processing
    time.sleep(3)

    # Verify logs
    logs = get_container_logs()

    # We look for the specific username in the logs associated with the alert
    # Logic: Find lines containing the username AND "EMAIL NOTIFICATION TRIGGER"
    # Note: Logs might be split across lines, but typically the trigger log includes the user info.

    # Simple check: Does the log contain the trigger and duplicate the username?
    # "EMAIL NOTIFICATION TRIGGER: ... username=..."

    # Checking for specific substrings
    assert f"email notification trigger" in logs.lower() or "EMAIL NOTIFICATION TRIGGER" in logs
    # To be more specific and ensure THIS test caused it:
    assert username in logs, f"Username {username} not found in logs"

    # Check for risk reason
    assert "brute force" in logs.lower() or "failed logins" in logs.lower(), \
        "Brute force reason not found in logs"

def test_e2e_email_notification_ip_change():
    """
    Test email notification logging for IP change + failures.
    Replaces: test_email_notification_logging_for_ip_change_with_failures
    """
    username = generate_username("ip_change")
    user_id = 9002
    base_time = datetime.utcnow()

    print(f"\n[Test] IP Change - User: {username}")

    # 1. Success from IP A
    success_event = {
        "user_id": user_id,
        "username": username,
        "event_type": "login_success",
        "timestamp": (base_time - timedelta(hours=1)).isoformat() + "Z",
        "ip_address": "192.168.1.100",
        "user_agent": "Chrome/91.0",
        "metadata": {}
    }
    requests.post(f"{MCP_API_URL}/mcp/ingest", json=success_event, timeout=REQUEST_TIMEOUT)
    time.sleep(0.5)

    # 2. Failures from IP B
    for i in range(6):
        event_data = {
            "user_id": user_id,
            "username": username,
            "event_type": "login_failure",
            "timestamp": (base_time + timedelta(seconds=i)).isoformat() + "Z",
            "ip_address": "10.0.0.200",
            "user_agent": "Chrome/91.0",
            "metadata": {"attempt": i + 1}
        }
        requests.post(f"{MCP_API_URL}/mcp/ingest", json=event_data, timeout=REQUEST_TIMEOUT)

    time.sleep(3)
    logs = get_container_logs()

    assert username in logs
    assert "EMAIL NOTIFICATION TRIGGER" in logs
    assert "IP address changed" in logs or "ip address changed" in logs.lower()

def test_e2e_no_notification_low_risk():
    """
    Test NO email notification for low risk.
    Replaces: test_no_email_notification_for_low_risk_events
    """
    username = generate_username("normal_user")
    user_id = 9003
    base_time = datetime.utcnow()

    print(f"\n[Test] Low Risk - User: {username}")

    for i in range(3):
        event_data = {
            "user_id": user_id,
            "username": username,
            "event_type": "login_success",
            "timestamp": (base_time + timedelta(minutes=i)).isoformat() + "Z",
            "ip_address": "192.168.1.100",
            "user_agent": "Chrome/91.0",
            "metadata": {}
        }
        requests.post(f"{MCP_API_URL}/mcp/ingest", json=event_data, timeout=REQUEST_TIMEOUT)

    time.sleep(2)
    logs = get_container_logs()

    # Filter logs for this username
    user_logs = [line for line in logs.split('\n') if username in line]

    for line in user_logs:
        assert "EMAIL NOTIFICATION TRIGGER" not in line, \
            f"Found unexpected trigger for low risk user: {line}"

def test_e2e_email_notification_2fa_failure():
    """
    Test email notification for 2FA failures.
    Replaces: test_email_notification_logging_for_2fa_failures
    """
    username = generate_username("2fa_victim")
    user_id = 9004
    base_time = datetime.utcnow()

    print(f"\n[Test] 2FA Failure - User: {username}")

    for i in range(11):
        event_data = {
            "user_id": user_id,
            "username": username,
            "event_type": "2fa_failure",
            "timestamp": (base_time + timedelta(seconds=i)).isoformat() + "Z",
            "ip_address": "10.0.0.150",
            "user_agent": "2FABot/1.0",
            "metadata": {"attempt": i + 1}
        }
        requests.post(f"{MCP_API_URL}/mcp/ingest", json=event_data, timeout=REQUEST_TIMEOUT)

    time.sleep(3)
    logs = get_container_logs()

    assert username in logs
    assert "EMAIL NOTIFICATION TRIGGER" in logs
    assert "2FA" in logs or "2fa" in logs.lower()

def test_e2e_verify_fraud_assessment_api():
    """
    Test API return after trigger.
    Replaces: test_verify_fraud_assessment_api_after_email_trigger
    """
    username = generate_username("api_check")
    user_id = random.randint(10000, 99999)
    base_time = datetime.utcnow()

    print(f"\n[Test] API Check - User: {username}")

    for i in range(12):
        event_data = {
            "user_id": user_id,
            "username": username,
            "event_type": "login_failure",
            "timestamp": (base_time + timedelta(seconds=i)).isoformat() + "Z",
            "ip_address": "10.0.0.250",
            "user_agent": "TestBot/1.0",
            "metadata": {}
        }
        requests.post(f"{MCP_API_URL}/mcp/ingest", json=event_data, timeout=REQUEST_TIMEOUT)

    time.sleep(3)

    # Query API
    resp = requests.get(f"{MCP_API_URL}/mcp/fraud-assessments?user_id={user_id}", timeout=REQUEST_TIMEOUT)
    assert resp.status_code == 200
    data = resp.json()

    assessments = data["assessments"]
    high_risk = [a for a in assessments if a["risk_score"] >= 0.7]
    assert len(high_risk) > 0, "No high risk assessment found in API"

    assessment = high_risk[0]
    # The API returns 'FraudAssessmentOut' which contains 'event' object
    # checks logic: assessment["event"]["username"] should match
    assert assessment["event"]["username"] == username
    assert len(assessment["reason"]) > 0

if __name__ == "__main__":
    # Allow running directly script
    test_e2e_email_notification_brute_force()
    test_e2e_email_notification_ip_change()
    test_e2e_no_notification_low_risk()
    test_e2e_email_notification_2fa_failure()
    test_e2e_verify_fraud_assessment_api()
    print("\nALL tests passed!")
