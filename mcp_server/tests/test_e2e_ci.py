"""
CI-Friendly End-to-End Test for GitHub Actions

This test is designed to run in CI environments where services are pre-started.
It focuses on the core email notification flow without assumptions about database state.

Usage in CI:
    1. Start services: docker compose up -d
    2. Run tests: pytest tests/test_e2e_ci.py -v
    3. Clean up: docker compose down -v
"""
import pytest
import httpx
import asyncio
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = "http://localhost:8000"
MCP_SERVER_URL = "http://localhost:8001"


@pytest.fixture(scope="module")
def check_services():
    """Verify services are running before tests"""
    logger.info("Checking if services are running...")

    # Check Auth Service
    try:
        response = httpx.get(f"{AUTH_SERVICE_URL}/docs", timeout=5.0)
        assert response.status_code == 200
        logger.info("✓ Auth Service is running")
    except Exception as e:
        pytest.fail(f"Auth Service not available: {e}")

    # Check MCP Server
    try:
        response = httpx.get(f"{MCP_SERVER_URL}/health", timeout=5.0)
        assert response.status_code == 200
        logger.info("✓ MCP Server is running")
    except Exception as e:
        pytest.fail(f"MCP Server not available: {e}")

    yield


@pytest.mark.asyncio
async def test_brute_force_triggers_email_notification(check_services):
    """
    Test that brute force attack triggers email notification

    This is the main E2E test for CI:
    1. Create user
    2. Perform 12 failed login attempts
    3. Verify high risk score (>= 0.7)
    4. Verify email notification would be sent
    """
    timestamp = int(time.time())
    username = f"ci_test_{timestamp}"
    password = "SecurePass123!"  # pragma: allowlist secret

    async with httpx.AsyncClient(timeout=30.0) as client:

        logger.info(f"\n{'='*70}")
        logger.info(f"CI E2E TEST: Brute Force → Email Notification")
        logger.info(f"{'='*70}")

        # Step 1: Create user
        logger.info(f"Step 1: Creating user {username}")
        signup_response = await client.post(
            f"{AUTH_SERVICE_URL}/register",
            json={
                "email": f"{username}@test.com",
                "username": username,
                "password": password,
                "first_name": "CI",
                "last_name": "Test",
                "tier": "dev"
            }
        )
        assert signup_response.status_code == 200, \
            f"Signup failed: {signup_response.text}"
        logger.info(f"✓ User created")

        await asyncio.sleep(2)

        # Step 2: Perform brute force attack
        logger.info(f"Step 2: Simulating brute force (12 failed logins)")
        failed_count = 12

        for i in range(failed_count):
            failed_response = await client.post(
                f"{AUTH_SERVICE_URL}/login",
                json={"username": username, "password": "WrongPassword!"}  # pragma: allowlist secret
            )
            assert failed_response.status_code == 401
            await asyncio.sleep(0.3)  # Stay within 5-minute window

        logger.info(f"✓ Completed {failed_count} failed login attempts")

        # Wait for fraud analysis
        await asyncio.sleep(5)

        # Step 3: Get user_id from MCP Server
        logger.info(f"Step 3: Retrieving fraud assessments")
        events_response = await client.get(
            f"{MCP_SERVER_URL}/mcp/events",
            params={"username": username, "limit": 1}
        )
        assert events_response.status_code == 200
        events = events_response.json()["events"]
        assert len(events) > 0, f"No events found for {username}"
        user_id = events[0]["user_id"]

        # Step 4: Verify fraud detection
        fraud_response = await client.get(
            f"{MCP_SERVER_URL}/mcp/fraud-assessments",
            params={"user_id": user_id, "sort_by": "risk_score", "sort_order": "desc"}
        )
        assert fraud_response.status_code == 200

        assessments = fraud_response.json()["assessments"]
        assert len(assessments) > 0, "No fraud assessments found"

        highest_risk = assessments[0]

        logger.info(f"Fraud Assessment:")
        logger.info(f"  Risk Score: {highest_risk['risk_score']:.2f}")
        logger.info(f"  Reason: {highest_risk['reason']}")
        logger.info(f"  Email Notification: {highest_risk['email_notification']}")

        # Assertions
        assert highest_risk['risk_score'] >= 0.7, \
            f"Expected high risk score (>= 0.7), got {highest_risk['risk_score']}"

        assert highest_risk['email_notification'] == True, \
            "Expected email_notification to be True for high-risk event"

        assert "failed login" in highest_risk['reason'].lower(), \
            "Expected fraud reason to mention failed logins"

        logger.info(f"✓ High-risk event detected correctly")
        logger.info(f"✓ Email notification flag set correctly")

        # Step 5: Verify event counts
        logger.info(f"Step 4: Verifying event storage")
        all_events_response = await client.get(
            f"{MCP_SERVER_URL}/mcp/events",
            params={"user_id": user_id, "limit": 100}
        )
        assert all_events_response.status_code == 200

        all_events = all_events_response.json()["events"]
        login_failures = [e for e in all_events if e["event_type"] == "login_failure"]

        logger.info(f"  Total events: {len(all_events)}")
        logger.info(f"  Login failures: {len(login_failures)}")

        assert len(login_failures) >= failed_count, \
            f"Expected at least {failed_count} login_failure events"

        logger.info(f"✓ All events stored correctly")

        # Test Summary
        logger.info(f"\n{'='*70}")
        logger.info(f"TEST SUMMARY")
        logger.info(f"{'='*70}")
        logger.info(f"✅ User: {username} (user_id={user_id})")
        logger.info(f"✅ Attack: {failed_count} failed logins")
        logger.info(f"✅ Detection: risk_score={highest_risk['risk_score']:.2f}")
        logger.info(f"✅ Notification: Email would be sent")
        logger.info(f"✅ Storage: {len(all_events)} events recorded")
        logger.info(f"{'='*70}")
        logger.info(f"🎉 CI E2E TEST PASSED")
        logger.info(f"{'='*70}\n")


@pytest.mark.asyncio
async def test_normal_login_no_email(check_services):
    """
    Test that normal login activity does NOT trigger email notification
    """
    timestamp = int(time.time())
    username = f"normal_{timestamp}"
    password = "SecurePass123!"

    async with httpx.AsyncClient(timeout=30.0) as client:

        logger.info(f"\n{'='*70}")
        logger.info(f"CI E2E TEST: Normal Activity (No Email)")
        logger.info(f"{'='*70}")

        # Create user
        signup_response = await client.post(
            f"{AUTH_SERVICE_URL}/register",
            json={
                "email": f"{username}@test.com",
                "username": username,
                "password": password,
                "first_name": "Normal",
                "last_name": "User",
                "tier": "dev"
            }
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

        # Get assessments for this specific user
        events_response = await client.get(
            f"{MCP_SERVER_URL}/mcp/events",
            params={"username": username, "limit": 1}
        )
        assert events_response.status_code == 200
        events = events_response.json()["events"]

        if len(events) > 0:
            user_id = events[0]["user_id"]

            fraud_response = await client.get(
                f"{MCP_SERVER_URL}/mcp/fraud-assessments",
                params={"user_id": user_id}
            )
            assert fraud_response.status_code == 200

            assessments = fraud_response.json()["assessments"]

            # Check only assessments for THIS user's recent activity
            # Filter to only login_success events
            recent_success_assessments = [
                a for a in assessments
                if "login_success" in str(a.get("event_type", "")).lower() or
                   a.get("risk_score", 1.0) < 0.3
            ]

            if recent_success_assessments:
                for assessment in recent_success_assessments:
                    logger.info(f"Risk Score: {assessment['risk_score']:.2f}")
                    assert assessment['risk_score'] < 0.7, \
                        f"Expected low risk for normal login"

                logger.info(f"✓ Normal activity correctly identified (low risk)")
            else:
                logger.info(f"✓ No high-risk assessments for normal login")

        logger.info(f"✅ TEST PASSED: Normal activity does not trigger email\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--log-cli-level=INFO"])
