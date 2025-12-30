"""
Component test for AI Rate Limiting.
Verifies that bursts of requests trigger the rate limiter (60 RPM).
"""
import pytest
import requests
import time
import subprocess
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8001"
# We need to send > 60 requests quickly.
# Token bucket capacity = 60. Refill = 1/sec.
NUM_REQUESTS = 120

def test_ai_rate_limit_enforcement():
    """
    Test that the AI rate limiter triggers after ~60 requests.
    Since we don't have a real BAML key, normal requests fail with "BAML Error".
    But "Rate Exceeded" requests will fail with "BAML rate limit exceeded" in logs.
    """
    print(f"\n[Component Test] Sending {NUM_REQUESTS} requests to trigger rate limit...")

    # We use a unique user_id to ensure we don't hit the *per-user* rate limit (5 mins)
    # The per-user limit skips BAML if recent analysis exists.
    # To hit the GLOBAL TokenBucket, we need valid calls that *enter* analyze_fraud.
    # So we need DIFFERENT users for each call to bypass per-user check?
    # Yes, create_unique_users

    start_time = time.time()

    for i in range(NUM_REQUESTS):
        uid = int(uuid.uuid4().int % 10000000)
        requests.post(f"{BASE_URL}/mcp/ingest", json={
            "user_id": uid,
            "username": f"load_test_{i}",
            "event_type": "login_success",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "ip_address": "1.2.3.4",
            "user_agent": "LoadBot/1.0",
            "metadata": {}
        })
        time.sleep(0.01)

    duration = time.time() - start_time
    print(f"  -> Sent {NUM_REQUESTS} requests in {duration:.2f} seconds")

    # Allow logs to flush
    time.sleep(2)

    # Check docker logs
    # We use subprocess to get logs from the mcp-server container
    print("  -> Checking docker logs for rate limit warning...")
    result = subprocess.run(
        ["docker", "logs", "--since", "30s", "authenicationservice-mcp-server-1"],
        capture_output=True,
        text=True
    )

    logs = result.stdout + result.stderr

    # Assert
    assert "BAML rate limit exceeded" in logs, "Rate limit warning not found in logs!"
    assert "Falling back to rule-based detection" in logs, "Fallback message not found!"

    # Count occurrences (optional)
    count = logs.count("BAML rate limit exceeded")
    print(f"  -> Found {count} rate limit exceeded messages.")
    assert count > 0, "Should have at least some rate limited requests"

    print("✅ Component Test Passed: AI Rate Limit enforced (verified via logs).")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
