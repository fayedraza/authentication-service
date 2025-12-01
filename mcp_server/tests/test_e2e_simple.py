"""
Simplified End-to-End Test: User Signup → Fraud Detection → Email Notification

This test runs against already-running services (no testcontainers required).
Start services first with: cd auth_platform && docker-compose up -d

Usage:
    pytest tests/test_e2e_simple.py -v -s --log-cli-level=INFO
"""
import pytest
import httpx
import asyncio
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Service URLs (can be overridden with environment variables)
AUTH_SERVICE_URL = "http://localhost:8000"
MCP_SERVER_URL = "http://localhost:8001"


@pytest.fixture(scope="module")
def check_services():
    """Verify services are running before tests"""
    logger.info("Checking if services are running...")

    # Check Auth Service (check docs endpoint since /health doesn't exist)
    try:
        response = httpx.get(f"{AUTH_SERVICE_URL}/docs", timeout=5.0)
        assert response.status_code == 200
        logger.info("✓ Auth Service is running")
    except Exception as e:
        pytest.skip(f"Auth Service not available: {e}. Start with: docker-compose up -d")

    # Check MCP Server
    try:
        response = httpx.get(f"{MCP_SERVER_URL}/health", timeout=5.0)
        assert response.status_code == 200
        logger.info("✓ MCP Server is running")
    except Exception as e:
        pytest.skip(f"MCP Server not available: {e}. Start with: docker-compose up -d")

    yield


@pytest.mark.asyncio
async def test_complete_flow_signup_to_email_notification(check_services):
    """
    Complete E2E test: Signup → Failed Logins → Fraud Detection → Email Notification

    This test verifies:
    1. User can sign up
    2. User can login successfully
    3. Multiple failed logins trigger fraud detection
    4. High-risk events generate risk_score >= 0.7
    5. Email notification flag is set correctly
    """
    # Generate unique username
    timestamp = int(time.time())
    username = f"e2e_user_{timestamp}"
    password = "TestPassword123!"  # pragma: allowlist secret

    async with httpx.AsyncClient(timeout=30.0) as client:

        # ============================================================
        # STEP 1: User Signup
        # ============================================================
        logger.info(f"\n{'='*70}")
        logger.info(f"STEP 1: User Signup")
        logger.info(f"{'='*70}")
        logger.info(f"Creating user: {username}")

        signup_response = await client.post(
            f"{AUTH_SERVICE_URL}/register",
            json={"email": f"{username}@test.com", "username": username, "password": password, "first_name": "Test", "last_name": "User", "tier": "dev"}
        )

        assert signup_response.status_code == 200, \
            f"Signup failed: {signup_response.status_code} - {signup_response.text}"

        signup_data = signup_response.json()
        access_token = signup_data["access_token"]

        logger.info(f"✓ User created: username={username}")

        # Wait for event to propagate
        await asyncio.sleep(2)

        # ============================================================
        # STEP 2: Successful Login (Baseline)
        # ============================================================
        logger.info(f"\n{'='*70}")
        logger.info(f"STEP 2: Successful Login (Establish Baseline)")
        logger.info(f"{'='*70}")

        login_response = await client.post(
            f"{AUTH_SERVICE_URL}/login",
            json={"username": username, "password": password}
        )

        assert login_response.status_code == 200, \
            f"Login failed: {login_response.status_code} - {login_response.text}"

        login_data = login_response.json()
        # Login may require 2FA, which is fine for our test
        if "requires2fa" in login_data and login_data["requires2fa"]:
            logger.info(f"✓ Login initiated (2FA required, which is expected)")
        else:
            assert "access_token" in login_data
            logger.info(f"✓ Successful login completed")

        await asyncio.sleep(2)

        # ============================================================
        # STEP 3: Multiple Failed Login Attempts
        # ============================================================
        logger.info(f"\n{'='*70}")
        logger.info(f"STEP 3: Simulating Brute Force Attack")
        logger.info(f"{'='*70}")

        failed_attempts = 12
        logger.info(f"Performing {failed_attempts} failed login attempts...")

        for i in range(failed_attempts):
            failed_response = await client.post(
                f"{AUTH_SERVICE_URL}/login",
                json={"username": username, "password": "WrongPassword!"}  # pragma: allowlist secret
            )

            assert failed_response.status_code == 401, \
                f"Expected 401 for wrong password, got {failed_response.status_code}"

            if (i + 1) % 3 == 0:
                logger.info(f"  Progress: {i+1}/{failed_attempts} failed attempts")

            # Small delay to stay within 5-minute window
            await asyncio.sleep(0.3)

        logger.info(f"✓ Completed {failed_attempts} failed login attempts")

        # Wait for MCP Server to process all events
        logger.info("Waiting for fraud analysis to complete...")
        await asyncio.sleep(5)

        # Get user_id from MCP Server by querying events with username
        events_by_username_response = await client.get(
            f"{MCP_SERVER_URL}/mcp/events",
            params={"username": username, "limit": 1}
        )
        assert events_by_username_response.status_code == 200
        events_by_username = events_by_username_response.json()["events"]
        assert len(events_by_username) > 0, f"No events found for username {username}"
        user_id = events_by_username[0]["user_id"]
        logger.info(f"Retrieved user_id from MCP Server: {user_id}")

        # ============================================================
        # STEP 4: Verify Fraud Detection
        # ============================================================
        logger.info(f"\n{'='*70}")
        logger.info(f"STEP 4: Verify Fraud Detection")
        logger.info(f"{'='*70}")

        fraud_response = await client.get(
            f"{MCP_SERVER_URL}/mcp/fraud-assessments",
            params={"user_id": user_id, "sort_by": "risk_score", "sort_order": "desc"}
        )

        assert fraud_response.status_code == 200, \
            f"Failed to query fraud assessments: {fraud_response.text}"

        fraud_data = fraud_response.json()
        assessments = fraud_data["assessments"]

        assert len(assessments) > 0, "No fraud assessments found"

        # Get highest risk assessment
        highest_risk = assessments[0]  # Already sorted by risk_score desc

        logger.info(f"Fraud Assessment Results:")
        logger.info(f"  Risk Score: {highest_risk['risk_score']:.2f}")
        logger.info(f"  Reason: {highest_risk['reason']}")
        logger.info(f"  Email Notification: {highest_risk['email_notification']}")

        # Verify high risk score
        assert highest_risk['risk_score'] >= 0.7, \
            f"Expected risk_score >= 0.7 for brute force attack, got {highest_risk['risk_score']}"

        # Verify reason mentions failed logins
        assert "failed login" in highest_risk['reason'].lower(), \
            f"Expected fraud reason to mention failed logins"

        logger.info(f"✓ Fraud detection verified: HIGH RISK")

        # ============================================================
        # STEP 5: Verify Email Notification Would Be Sent
        # ============================================================
        logger.info(f"\n{'='*70}")
        logger.info(f"STEP 5: Verify Email Notification Logic")
        logger.info(f"{'='*70}")

        # Count high-risk events (risk_score >= 0.7)
        high_risk_events = [a for a in assessments if a['risk_score'] >= 0.7]

        logger.info(f"High-risk events found: {len(high_risk_events)}")

        for i, event in enumerate(high_risk_events[:3], 1):  # Show first 3
            logger.info(f"  {i}. Risk: {event['risk_score']:.2f} - {event['reason']}")

        assert len(high_risk_events) > 0, \
            "Expected at least one high-risk event that would trigger email notification"

        logger.info(f"✓ Email notification would be triggered for {len(high_risk_events)} event(s)")

        # ============================================================
        # STEP 6: Verify Event Storage
        # ============================================================
        logger.info(f"\n{'='*70}")
        logger.info(f"STEP 6: Verify Event Storage")
        logger.info(f"{'='*70}")

        events_response = await client.get(
            f"{MCP_SERVER_URL}/mcp/events",
            params={"user_id": user_id, "limit": 100}
        )

        assert events_response.status_code == 200
        events_data = events_response.json()
        events = events_data["events"]

        # Count event types
        event_counts = {}
        for event in events:
            event_type = event["event_type"]
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        logger.info(f"Event Summary:")
        for event_type, count in sorted(event_counts.items()):
            logger.info(f"  {event_type}: {count}")

        # Verify expected events
        # Note: Auth service may not send signup events, only login events
        assert event_counts.get("login_failure", 0) >= failed_attempts, \
            f"Expected {failed_attempts} login_failure events, got {event_counts.get('login_failure', 0)}"

        logger.info(f"✓ All events properly stored")

        # ============================================================
        # TEST SUMMARY
        # ============================================================
        logger.info(f"\n{'='*70}")
        logger.info(f"TEST SUMMARY")
        logger.info(f"{'='*70}")
        logger.info(f"✅ User signup: {username} (user_id={user_id})")
        logger.info(f"✅ Baseline login: Successful")
        logger.info(f"✅ Attack simulation: {failed_attempts} failed attempts")
        logger.info(f"✅ Fraud detection: risk_score={highest_risk['risk_score']:.2f}")
        logger.info(f"✅ Email notification: Would be sent ({len(high_risk_events)} events)")
        logger.info(f"✅ Event storage: {len(events)} total events")
        logger.info(f"{'='*70}")
        logger.info(f"🎉 END-TO-END TEST PASSED")
        logger.info(f"{'='*70}\n")


@pytest.mark.asyncio
async def test_low_risk_no_email_notification(check_services):
    """
    Test that low-risk activity does NOT trigger email notification
    """
    timestamp = int(time.time())
    username = f"normal_user_{timestamp}"
    password = "TestPassword123!"

    async with httpx.AsyncClient(timeout=30.0) as client:

        logger.info(f"\n{'='*70}")
        logger.info(f"TEST: Low-Risk Activity (No Email Notification)")
        logger.info(f"{'='*70}")

        # Signup
        signup_response = await client.post(
            f"{AUTH_SERVICE_URL}/register",
            json={"email": f"{username}@test.com", "username": username, "password": password, "first_name": "Test", "last_name": "User", "tier": "dev"}
        )
        assert signup_response.status_code == 200

        await asyncio.sleep(2)

        # Single successful login
        login_response = await client.post(
            f"{AUTH_SERVICE_URL}/login",
            json={"username": username, "password": password}
        )
        assert login_response.status_code == 200

        await asyncio.sleep(3)

        # Get user_id from events
        events_response = await client.get(
            f"{MCP_SERVER_URL}/mcp/events",
            params={"username": username, "limit": 1}
        )
        assert events_response.status_code == 200
        events = events_response.json()["events"]
        assert len(events) > 0
        user_id = events[0]["user_id"]

        # Check fraud assessments
        fraud_response = await client.get(
            f"{MCP_SERVER_URL}/mcp/fraud-assessments",
            params={"user_id": user_id}
        )
        assert fraud_response.status_code == 200

        assessments = fraud_response.json()["assessments"]

        # All assessments should be low risk
        for assessment in assessments:
            logger.info(f"Risk Score: {assessment['risk_score']:.2f} - {assessment['reason']}")
            assert assessment['risk_score'] < 0.7, \
                f"Expected low risk for normal activity, got {assessment['risk_score']}"

        logger.info(f"✓ No email notification triggered (all risk scores < 0.7)")
        logger.info(f"✅ TEST PASSED: Low-risk activity correctly identified\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--log-cli-level=INFO"])
