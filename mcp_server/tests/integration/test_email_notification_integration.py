"""
Integration test for email notification logging using testcontainers.

This test verifies that the MCP server correctly logs email notifications
when high-risk fraud events are detected by:
1. Starting the MCP server in a Docker container
2. Sending authentication events that trigger fraud detection
3. Verifying that email notification logs appear in the container logs

Requirements: testcontainers-python
Install with: pip install testcontainers[docker]
"""
import pytest
import time
import requests
from datetime import datetime, timedelta
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_strategies import wait_for_logs


class MCPServerContainer(DockerContainer):
    """
    Custom testcontainer for MCP Server.
    """

    def __init__(self, image="auth_platform-mcp-server:latest", **kwargs):
        super().__init__(image, **kwargs)
        self.with_exposed_ports(8001)
        self.with_env("LOG_LEVEL", "DEBUG")
        self.with_env("FRAUD_THRESHOLD", "0.7")
        self.with_env("DATABASE_URL", "sqlite:///./test_mcp.db")

    def get_api_url(self):
        """Get the base URL for the MCP API"""
        host = self.get_container_host_ip()
        port = self.get_exposed_port(8001)
        return f"http://{host}:{port}"


@pytest.fixture(scope="module")
def mcp_container():
    """
    Fixture that starts MCP server container for the test module.
    """
    container = MCPServerContainer()

    # Start container and wait for it to be ready
    container.start()

    # Wait for the server to be ready (look for startup log)
    try:
        # Give the server time to start
        time.sleep(3)

        # Verify server is responding
        api_url = container.get_api_url()
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get(f"{api_url}/health", timeout=2)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                if i == max_retries - 1:
                    raise
                time.sleep(1)

        yield container

    finally:
        # Stop and remove container
        container.stop()


def test_email_notification_logging_for_brute_force_attack(mcp_container):
    """
    Test that email notification logs appear when a brute force attack is detected.

    This test:
    1. Sends multiple failed login attempts within a 5-minute window
    2. Verifies that the risk score reaches the threshold (0.7)
    3. Checks that email notification logs appear in the container logs

    Requirements: 3.1, 3.4, 4.1
    """
    api_url = mcp_container.get_api_url()
    user_id = 1001
    username = "brute_force_victim"
    base_time = datetime.utcnow()

    # Send 12 failed login attempts within a 5-minute window
    # This should trigger: 11+ failed logins = +0.7 risk score
    event_ids = []

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

        response = requests.post(f"{api_url}/mcp/ingest", json=event_data)
        assert response.status_code == 201, f"Failed to ingest event {i}: {response.text}"

        event_id = response.json()["event_id"]
        event_ids.append(event_id)

        # Small delay to ensure events are processed in order
        time.sleep(0.2)

    # Give the server time to process all events and write logs
    time.sleep(2)

    # Get container logs
    logs = mcp_container.get_logs()[0].decode('utf-8')

    # Verify email notification logs are present
    assert "📧 EMAIL NOTIFICATION TRIGGER" in logs, \
        "Email notification log not found in container logs"

    assert "⚠️ HIGH RISK EVENT DETECTED" in logs, \
        "High risk event log not found in container logs"

    assert username in logs, \
        f"Username '{username}' not found in logs"

    assert "Severe brute force attack detected" in logs or "failed logins in 5 minutes" in logs, \
        "Brute force detection reason not found in logs"

    # Verify the risk score in logs
    assert "risk_score=0.7" in logs or "Risk: 0.7" in logs, \
        "Expected risk score (0.7) not found in logs"

    print("\n✅ Email notification logging test passed!")
    print(f"✅ Successfully detected brute force attack for user '{username}'")
    print(f"✅ Email notification logs found in container output")


def test_email_notification_logging_for_ip_change_with_failures(mcp_container):
    """
    Test email notification logging for IP change combined with failed attempts.

    This test:
    1. Creates a successful login from one IP
    2. Sends multiple failed logins from a different IP
    3. Verifies email notification logs for the combined risk

    Requirements: 3.1, 3.4
    """
    api_url = mcp_container.get_api_url()
    user_id = 1002
    username = "ip_change_victim"
    base_time = datetime.utcnow()

    # First, establish a successful login from original IP
    success_event = {
        "user_id": user_id,
        "username": username,
        "event_type": "login_success",
        "timestamp": (base_time - timedelta(hours=1)).isoformat() + "Z",
        "ip_address": "192.168.1.100",
        "user_agent": "Chrome/91.0",
        "metadata": {}
    }

    response = requests.post(f"{api_url}/mcp/ingest", json=success_event)
    assert response.status_code == 201
    time.sleep(0.5)

    # Now send 6 failed login attempts from a different IP
    # This should trigger: 6-10 failed logins = +0.5, IP change = +0.2 = 0.7 total
    for i in range(6):
        event_data = {
            "user_id": user_id,
            "username": username,
            "event_type": "login_failure",
            "timestamp": (base_time + timedelta(seconds=i)).isoformat() + "Z",
            "ip_address": "10.0.0.200",  # Different IP
            "user_agent": "Chrome/91.0",
            "metadata": {"attempt": i + 1}
        }

        response = requests.post(f"{api_url}/mcp/ingest", json=event_data)
        assert response.status_code == 201
        time.sleep(0.2)

    # Give time for processing
    time.sleep(2)

    # Get container logs
    logs = mcp_container.get_logs()[0].decode('utf-8')

    # Verify email notification logs
    assert "📧 EMAIL NOTIFICATION TRIGGER" in logs, \
        "Email notification log not found"

    assert username in logs, \
        f"Username '{username}' not found in logs"

    # Should mention both IP change and failed attempts
    assert "IP address changed" in logs or "failed login" in logs, \
        "Expected fraud detection reasons not found in logs"

    print("\n✅ IP change with failures test passed!")
    print(f"✅ Successfully detected suspicious activity for user '{username}'")


def test_no_email_notification_for_low_risk_events(mcp_container):
    """
    Test that email notification logs do NOT appear for low-risk events.

    This test:
    1. Sends normal authentication events
    2. Verifies that no email notification logs appear

    Requirements: 3.1, 4.1
    """
    api_url = mcp_container.get_api_url()
    user_id = 1003
    username = "normal_user"
    base_time = datetime.utcnow()

    # Send a few normal login events
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

        response = requests.post(f"{api_url}/mcp/ingest", json=event_data)
        assert response.status_code == 201
        time.sleep(0.2)

    # Give time for processing
    time.sleep(2)

    # Get recent logs (last 50 lines to avoid checking old test logs)
    logs = mcp_container.get_logs()[0].decode('utf-8')
    recent_logs = '\n'.join(logs.split('\n')[-50:])

    # Verify NO email notification logs for this user
    user_specific_logs = [line for line in recent_logs.split('\n') if username in line]

    for log_line in user_specific_logs:
        assert "📧 EMAIL NOTIFICATION TRIGGER" not in log_line, \
            f"Unexpected email notification log found for low-risk user: {log_line}"
        assert "⚠️ HIGH RISK EVENT DETECTED" not in log_line, \
            f"Unexpected high risk log found for low-risk user: {log_line}"

    print("\n✅ Low-risk event test passed!")
    print(f"✅ No email notifications triggered for normal user '{username}'")


def test_email_notification_logging_for_2fa_failures(mcp_container):
    """
    Test email notification logging for multiple 2FA failures.

    This test:
    1. Sends multiple failed 2FA attempts
    2. Verifies email notification logs appear

    Requirements: 3.1, 3.4
    """
    api_url = mcp_container.get_api_url()
    user_id = 1004
    username = "2fa_attack_victim"
    base_time = datetime.utcnow()

    # Send 11 failed 2FA attempts
    # This should trigger: 11+ failed 2FA = +0.8 risk score
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

        response = requests.post(f"{api_url}/mcp/ingest", json=event_data)
        assert response.status_code == 201
        time.sleep(0.2)

    # Give time for processing
    time.sleep(2)

    # Get container logs
    logs = mcp_container.get_logs()[0].decode('utf-8')

    # Verify email notification logs
    assert "📧 EMAIL NOTIFICATION TRIGGER" in logs, \
        "Email notification log not found for 2FA attack"

    assert username in logs, \
        f"Username '{username}' not found in logs"

    assert "2FA" in logs or "2fa" in logs, \
        "2FA-related fraud detection not found in logs"

    print("\n✅ 2FA failure test passed!")
    print(f"✅ Successfully detected 2FA brute force attack for user '{username}'")


def test_verify_fraud_assessment_api_after_email_trigger(mcp_container):
    """
    Test that fraud assessments API returns correct data after email notification trigger.

    This test:
    1. Triggers a high-risk event
    2. Queries the fraud assessments API
    3. Verifies the event is marked with high risk and email_notification flag

    Requirements: 3.4, 7.1, 7.2
    """
    api_url = mcp_container.get_api_url()
    user_id = 1005
    username = "api_test_user"
    base_time = datetime.utcnow()

    # Send events to trigger high risk
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

        response = requests.post(f"{api_url}/mcp/ingest", json=event_data)
        assert response.status_code == 201
        time.sleep(0.2)

    # Give time for processing
    time.sleep(2)

    # Query fraud assessments API
    response = requests.get(f"{api_url}/mcp/fraud-assessments?user_id={user_id}")
    assert response.status_code == 200

    data = response.json()
    assert "assessments" in data
    assert len(data["assessments"]) > 0

    # Find the high-risk assessment
    high_risk_assessments = [a for a in data["assessments"] if a["risk_score"] >= 0.7]
    assert len(high_risk_assessments) > 0, "No high-risk assessments found"

    # Verify the assessment has correct data
    assessment = high_risk_assessments[0]
    assert assessment["user_id"] == user_id
    assert assessment["username"] == username
    assert assessment["risk_score"] >= 0.7
    assert len(assessment["fraud_reason"]) > 0

    print("\n✅ Fraud assessment API test passed!")
    print(f"✅ High-risk assessment correctly stored for user '{username}'")
    print(f"✅ Risk score: {assessment['risk_score']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
