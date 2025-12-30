
import pytest
import requests
import uuid
import time
from datetime import datetime

MCP_API_URL = "http://localhost:8001"
REQUEST_TIMEOUT = 10

def test_e2e_validation_error():
    # 1. Missing Username
    resp = requests.post(f"{MCP_API_URL}/mcp/ingest", json={
        "user_id": 999,
        # "username": "missing",
        "event_type": "login_success",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })
    assert resp.status_code == 422

    # 2. Invalid Event Type
    resp = requests.post(f"{MCP_API_URL}/mcp/ingest", json={
        "user_id": 999,
        "username": "test",
        "event_type": "INVALID_TYPE",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })
    assert resp.status_code == 422

def test_e2e_multiple_event_types():
    event_types = [
        "login_success", "login_failure", "2fa_success",
        "2fa_failure", "password_reset", "password_reset_request"
    ]
    uid = int(str(uuid.uuid4().int)[:8])

    for et in event_types:
        resp = requests.post(f"{MCP_API_URL}/mcp/ingest", json={
            "user_id": uid,
            "username": f"user_{uid}",
            "event_type": et,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        assert resp.status_code == 201

def test_e2e_readiness_probe():
    resp = requests.get(f"{MCP_API_URL}/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert "database" in data
    assert "baml_agent" in data
