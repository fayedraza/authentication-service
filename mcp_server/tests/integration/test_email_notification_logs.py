#!/usr/bin/env python3
"""
Test script to verify email notification logging.

This script simulates suspicious activity and checks if the system
would trigger email notifications (shown in logs).
"""
import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8001"

def test_email_notification_trigger():
    """
    Test that high-risk events trigger email notification logs.

    Simulates 3 failed login attempts which should trigger:
    1. High risk detection (risk_score > 0.7)
    2. Email notification log message
    """
    print("=" * 80)
    print("Testing Email Notification Trigger via Logs")
    print("=" * 80)

    # Test user
    user_id = 999
    username = "test.suspicious.user"

    print(f"\n📝 Simulating suspicious activity for user: {username} (ID: {user_id})")
    print("-" * 80)

    # Send 3 failed login attempts
    for i in range(1, 4):
        print(f"\n{i}. Sending failed login attempt from IP 10.0.0.{i}...")

        event_data = {
            "user_id": user_id,
            "username": username,
            "event_type": "login_failure",
            "ip_address": f"10.0.0.{i}",
            "user_agent": "curl/7.68.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {}
        }

        try:
            response = requests.post(
                f"{BASE_URL}/mcp/ingest",
                json=event_data,
                timeout=5
            )

            if response.status_code == 201:
                result = response.json()
                print(f"   ✅ Event ingested: {result['event_id']}")
            else:
                print(f"   ❌ Failed: {response.status_code} - {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error: {e}")
            print("\n⚠️  Make sure MCP Server is running: docker compose up -d mcp-server")
            return

        # Small delay between attempts
        if i < 3:
            time.sleep(1)

    print("\n" + "=" * 80)
    print("✅ Test Complete!")
    print("=" * 80)

    print("\n📋 What to check in the logs:")
    print("-" * 80)
    print("1. Run: docker compose logs mcp-server | grep 'HIGH RISK'")
    print("2. Look for: ⚠️ HIGH RISK EVENT DETECTED")
    print("3. Look for: 📧 EMAIL NOTIFICATION TRIGGER")
    print()
    print("If you see the 📧 EMAIL NOTIFICATION TRIGGER message,")
    print("it means the system would send an email to the user!")
    print()

    # Query fraud assessments
    print("\n🔍 Checking fraud assessments...")
    print("-" * 80)

    try:
        response = requests.get(
            f"{BASE_URL}/mcp/fraud-assessments?user_id={user_id}",
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            assessments = data.get("assessments", [])
            stats = data.get("statistics", {})

            print(f"\n📊 Statistics:")
            print(f"   Total events: {stats.get('total_events', 0)}")
            print(f"   High risk events: {stats.get('high_risk_events', 0)}")
            print(f"   Average risk score: {stats.get('average_risk_score', 0):.2f}")

            if assessments:
                print(f"\n🎯 Latest Assessment:")
                latest = assessments[0]
                print(f"   Risk Score: {latest['risk_score']:.2f}")
                print(f"   Reason: {latest['reason']}")
                print(f"   Email would be sent: {'YES ✅' if latest['risk_score'] > 0.7 else 'NO ❌'}")
        else:
            print(f"   ❌ Failed to get assessments: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 80)
    print("📝 To see the actual log messages:")
    print("=" * 80)
    print("docker compose logs mcp-server --tail=50 | grep -E '(HIGH RISK|EMAIL)'")
    print()


if __name__ == "__main__":
    test_email_notification_trigger()
