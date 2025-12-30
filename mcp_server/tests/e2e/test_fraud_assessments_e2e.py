
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
def assessment_test_data():
    """Setup isolated test data for fraud assessment tests"""
    user_id_1 = generate_user_id()

    # Create Low Risk Events (Normal)
    # 1. Login success
    requests.post(f"{MCP_API_URL}/mcp/ingest", json={
        "user_id": user_id_1,
        "username": f"user_{user_id_1}",
        "event_type": "login_success",
        "ip_address": "192.168.1.100",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": {}
    }, timeout=REQUEST_TIMEOUT)

    # Create Medium Risk Event (Single failure, maybe not enough for >0.4? Rule: Multi failures needed)
    # Actually, let's trigger High Risk to be sure we get a range.
    # High Risk: 10 failures.
    time.sleep(1)

    user_id_2 = generate_user_id()
    for i in range(12):
        r = requests.post(f"{MCP_API_URL}/mcp/ingest", json={
            "user_id": user_id_2,
            "username": f"user_{user_id_2}",
            "event_type": "login_failure",
            "ip_address": "10.0.0.99",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {"attempt": i}
        }, timeout=REQUEST_TIMEOUT)
        assert r.status_code == 201, f"Ingest failed: {r.text}"

    time.sleep(5) # Increase wait time for async processing

    return {
        "low_risk_user": user_id_1,
        "high_risk_user": user_id_2
    }

def test_e2e_get_all_assessments(assessment_test_data):
    # This queries EVERYTHING, so verifying exact counts is hard on shared DB.
    # But we can verify structure and at least our data exists.
    resp = requests.get(f"{MCP_API_URL}/mcp/fraud-assessments?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "assessments" in data
    assert "statistics" in data
    assert data["total"] >= 2

    # Verify Stats structure
    stats = data["statistics"]
    assert stats["total_events"] >= 2
    assert "high_risk_events" in stats
    assert "average_risk_score" in stats

def test_e2e_filter_by_user(assessment_test_data):
    uid = assessment_test_data["high_risk_user"]
    resp = requests.get(f"{MCP_API_URL}/mcp/fraud-assessments?user_id={uid}")
    assert resp.status_code == 200
    data = resp.json()
    # 12 events.
    assert data["total"] == 12
    # Check risk score of the last one (should be high)
    assessments = data["assessments"]
    high_risks = [a for a in assessments if a["risk_score"] >= 0.7]
    assert len(high_risks) > 0
    assert high_risks[0]["alert_generated"] == True

def test_e2e_filter_by_risk_score(assessment_test_data):
    # Filter high risk
    resp = requests.get(f"{MCP_API_URL}/mcp/fraud-assessments?min_risk_score=0.7")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["assessments"]) > 0
    for a in data["assessments"]:
        assert a["risk_score"] >= 0.7

def test_e2e_statistics_integrity(assessment_test_data):
    resp = requests.get(f"{MCP_API_URL}/mcp/fraud-assessments")
    data = resp.json()
    stats = data["statistics"]

    total = stats["high_risk_events"] + stats["medium_risk_events"] + stats["low_risk_events"]
    assert total == stats["total_events"]
    assert 0 <= stats["average_risk_score"] <= 1.0
