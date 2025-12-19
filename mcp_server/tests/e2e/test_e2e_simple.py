"""
Simple E2E test to verify basic MCP server functionality
"""
import pytest
import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8001"
REQUEST_TIMEOUT = 30


def test_mcp_server_health():
    """Test that MCP server is healthy and responding"""
    response = requests.get(f"{BASE_URL}/health", timeout=REQUEST_TIMEOUT)
    assert response.status_code == 200

    health_data = response.json()
    assert health_data["status"] == "healthy"


def test_basic_event_ingestion():
    """Test basic event ingestion functionality"""
    # Test event data
    event_data = {
        "user_id": 12345,
        "username": "test_user_e2e",
        "event_type": "login_success",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 Test Browser",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": {"test": "e2e_simple"}
    }

    # Ingest the event
    response = requests.post(f"{BASE_URL}/mcp/ingest", json=event_data, timeout=REQUEST_TIMEOUT)
    assert response.status_code == 201

    result = response.json()
    assert "event_id" in result
    assert result["status"] == "processed"


def test_fraud_assessment_query():
    """Test fraud assessment query functionality"""
    user_id = 12345

    # Query fraud assessments
    response = requests.get(
        f"{BASE_URL}/mcp/fraud-assessments",
        params={"user_id": user_id},
        timeout=REQUEST_TIMEOUT
    )
    assert response.status_code == 200

    data = response.json()
    assert "assessments" in data
    assert isinstance(data["assessments"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
