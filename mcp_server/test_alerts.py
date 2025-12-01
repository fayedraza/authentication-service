"""
Manual test script for alert generation and management functionality
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001"


def test_alert_creation_and_query():
    """Test alert creation through event ingestion and alert querying"""

    print("=" * 60)
    print("Testing Alert Generation and Management")
    print("=" * 60)

    # Test 1: Ingest high-risk events to trigger alert creation
    print("\n1. Ingesting high-risk events (multiple failed logins)...")

    user_id = 999
    username = "test_user_alerts"

    # Create multiple failed login events to trigger high risk score
    event_ids = []
    for i in range(4):
        event = {
            "user_id": user_id,
            "username": username,
            "event_type": "login_failure",
            "ip_address": f"192.168.1.{100 + i}",
            "user_agent": "Mozilla/5.0 Test Browser",
            "timestamp": (datetime.utcnow() - timedelta(minutes=i)).isoformat() + "Z",
            "metadata": {"attempt": i + 1}
        }

        response = requests.post(f"{BASE_URL}/mcp/ingest", json=event)
        if response.status_code == 201:
            result = response.json()
            event_ids.append(result["event_id"])
            print(f"   ✓ Event {i+1} ingested: {result['event_id']}")
        else:
            print(f"   ✗ Failed to ingest event {i+1}: {response.status_code}")
            print(f"     Response: {response.text}")

    # Wait a moment for fraud analysis to complete
    import time
    time.sleep(1)

    # Test 2: Query alerts for this user
    print(f"\n2. Querying alerts for user {user_id}...")
    response = requests.get(f"{BASE_URL}/mcp/alerts", params={"user_id": user_id})

    if response.status_code == 200:
        alerts_data = response.json()
        print(f"   ✓ Found {alerts_data['total']} alert(s)")

        if alerts_data['alerts']:
            for alert in alerts_data['alerts']:
                print(f"\n   Alert Details:")
                print(f"   - ID: {alert['id']}")
                print(f"   - User: {alert['username']} (ID: {alert['user_id']})")
                print(f"   - Risk Score: {alert['risk_score']:.2f}")
                print(f"   - Status: {alert['status']}")
                print(f"   - Event IDs: {len(alert['event_ids'])} events")
                print(f"   - Reason: {alert['reason']}")
                print(f"   - Created: {alert['created_at']}")

                alert_id = alert['id']
    else:
        print(f"   ✗ Failed to query alerts: {response.status_code}")
        print(f"     Response: {response.text}")
        return

    # Test 3: Query alerts with filters
    print("\n3. Querying open alerts with min risk score 0.7...")
    response = requests.get(
        f"{BASE_URL}/mcp/alerts",
        params={"status": "open", "min_risk_score": 0.7}
    )

    if response.status_code == 200:
        alerts_data = response.json()
        print(f"   ✓ Found {alerts_data['total']} high-risk open alert(s)")
    else:
        print(f"   ✗ Failed to query filtered alerts: {response.status_code}")

    # Test 4: Update alert status
    if alerts_data['alerts']:
        alert_id = alerts_data['alerts'][0]['id']
        print(f"\n4. Updating alert {alert_id} status to 'reviewed'...")

        response = requests.patch(
            f"{BASE_URL}/mcp/alerts/{alert_id}",
            json={"status": "reviewed"}
        )

        if response.status_code == 200:
            updated_alert = response.json()
            print(f"   ✓ Alert status updated to: {updated_alert['status']}")
            print(f"   - Updated at: {updated_alert['updated_at']}")
        else:
            print(f"   ✗ Failed to update alert: {response.status_code}")
            print(f"     Response: {response.text}")

        # Test 5: Update to resolved
        print(f"\n5. Updating alert {alert_id} status to 'resolved'...")

        response = requests.patch(
            f"{BASE_URL}/mcp/alerts/{alert_id}",
            json={"status": "resolved"}
        )

        if response.status_code == 200:
            updated_alert = response.json()
            print(f"   ✓ Alert status updated to: {updated_alert['status']}")
        else:
            print(f"   ✗ Failed to update alert: {response.status_code}")

    # Test 6: Test alert consolidation
    print(f"\n6. Testing alert consolidation (ingesting more high-risk events)...")

    # Ingest more failed login events within consolidation window
    for i in range(2):
        event = {
            "user_id": user_id,
            "username": username,
            "event_type": "2fa_failure",
            "ip_address": f"192.168.1.{200 + i}",
            "user_agent": "Mozilla/5.0 Test Browser",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {"consolidation_test": True}
        }

        response = requests.post(f"{BASE_URL}/mcp/ingest", json=event)
        if response.status_code == 201:
            print(f"   ✓ Additional event {i+1} ingested")

    time.sleep(1)

    # Query alerts again to see if they were consolidated
    print(f"\n7. Checking for alert consolidation...")
    response = requests.get(
        f"{BASE_URL}/mcp/alerts",
        params={"user_id": user_id, "status": "open"}
    )

    if response.status_code == 200:
        alerts_data = response.json()
        print(f"   ✓ Found {alerts_data['total']} open alert(s)")

        if alerts_data['alerts']:
            for alert in alerts_data['alerts']:
                print(f"\n   Consolidated Alert:")
                print(f"   - Event count: {len(alert['event_ids'])} events")
                print(f"   - Risk Score: {alert['risk_score']:.2f}")
                print(f"   - Reason: {alert['reason']}")

    # Test 8: Test invalid alert ID
    print("\n8. Testing error handling (invalid alert ID)...")
    response = requests.patch(
        f"{BASE_URL}/mcp/alerts/invalid-alert-id",
        json={"status": "reviewed"}
    )

    if response.status_code == 404:
        print(f"   ✓ Correctly returned 404 for invalid alert ID")
    else:
        print(f"   ✗ Unexpected status code: {response.status_code}")

    # Test 9: Test invalid status value
    print("\n9. Testing error handling (invalid status value)...")
    if alerts_data['alerts']:
        alert_id = alerts_data['alerts'][0]['id']
        response = requests.patch(
            f"{BASE_URL}/mcp/alerts/{alert_id}",
            json={"status": "invalid_status"}
        )

        if response.status_code == 422:
            print(f"   ✓ Correctly returned 422 for invalid status value")
        else:
            print(f"   ✗ Unexpected status code: {response.status_code}")

    print("\n" + "=" * 60)
    print("Alert Testing Complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_alert_creation_and_query()
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to MCP Server")
        print("  Make sure the server is running on http://localhost:8001")
        print("  Start it with: uvicorn mcp_server.main:app --port 8001")
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
