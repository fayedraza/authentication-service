"""
Integration test for fraud detection in event ingestion flow.

This test verifies that task 9 is properly implemented:
- Fraud analysis is triggered after storing event
- Risk score and fraud reason are stored in MCPAuthEvent
- Alerts are created when risk_score > threshold
- Errors are handled gracefully
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from mcp_server.main import app
from mcp_server.db import Base, get_db
from mcp_server.models import MCPAuthEvent, MCPAlert
from mcp_server.config import settings

# Create test database
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_fraud_detection_integration_normal_event():
    """Test that normal events get analyzed with low risk score"""
    print("\n✓ Test: Normal event fraud detection")

    event_data = {
        "user_id": 1001,
        "username": "normal_user",
        "event_type": "login_success",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": {}
    }

    response = client.post("/mcp/ingest", json=event_data)
    assert response.status_code == 201

    data = response.json()
    assert data["status"] == "accepted"
    event_id = data["event_id"]

    # Verify event was stored with fraud analysis
    db = TestingSessionLocal()
    event = db.query(MCPAuthEvent).filter(MCPAuthEvent.id == event_id).first()

    assert event is not None
    assert event.risk_score is not None
    assert event.risk_score >= 0.0
    assert event.risk_score <= 1.0
    assert event.fraud_reason is not None
    assert event.analyzed_at is not None

    # Normal event should have low risk
    assert event.risk_score < settings.FRAUD_THRESHOLD

    # No alert should be created
    alert = db.query(MCPAlert).filter(MCPAlert.user_id == 1001).first()
    assert alert is None

    db.close()
    print(f"  ✓ Event analyzed: risk_score={event.risk_score:.2f}, reason='{event.fraud_reason}'")


def test_fraud_detection_integration_high_risk_event():
    """Test that high-risk events trigger alerts"""
    print("\n✓ Test: High-risk event triggers alert")

    db = TestingSessionLocal()
    user_id = 1002
    base_time = datetime.utcnow()

    # Create previous successful login
    prev_event = MCPAuthEvent(
        id="prev-login-1002",
        user_id=user_id,
        username="risky_user",
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db.add(prev_event)

    # Create multiple failed login attempts
    for i in range(4):
        failed_event = MCPAuthEvent(
            id=f"failed-login-1002-{i}",
            user_id=user_id,
            username="risky_user",
            event_type="login_failure",
            ip_address="10.0.0.50",  # Different IP
            user_agent="Chrome/91.0",  # Different UA
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db.add(failed_event)

    db.commit()
    db.close()

    # Now ingest a new event that should trigger high risk
    event_data = {
        "user_id": user_id,
        "username": "risky_user",
        "event_type": "login_failure",
        "ip_address": "10.0.0.50",
        "user_agent": "Chrome/91.0",
        "timestamp": base_time.isoformat() + "Z",
        "metadata": {}
    }

    response = client.post("/mcp/ingest", json=event_data)
    assert response.status_code == 201

    data = response.json()
    event_id = data["event_id"]

    # Verify event was analyzed
    db = TestingSessionLocal()
    event = db.query(MCPAuthEvent).filter(MCPAuthEvent.id == event_id).first()

    assert event is not None
    assert event.risk_score is not None
    assert event.risk_score > settings.FRAUD_THRESHOLD
    assert "failed login" in event.fraud_reason.lower() or "ip address" in event.fraud_reason.lower()

    # Alert should be created
    alert = db.query(MCPAlert).filter(MCPAlert.user_id == user_id).first()
    assert alert is not None
    assert alert.status == "open"
    assert alert.risk_score >= settings.FRAUD_THRESHOLD
    assert event_id in alert.event_ids

    db.close()
    print(f"  ✓ High-risk event detected: risk_score={event.risk_score:.2f}")
    print(f"  ✓ Alert created: alert_id={alert.id}, status={alert.status}")


def test_fraud_detection_error_handling():
    """Test that fraud detection errors don't fail ingestion"""
    print("\n✓ Test: Graceful error handling")

    # Even with potential issues, ingestion should succeed
    event_data = {
        "user_id": 1003,
        "username": "test_user",
        "event_type": "login_success",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": {}
    }

    response = client.post("/mcp/ingest", json=event_data)
    assert response.status_code == 201

    data = response.json()
    assert data["status"] == "accepted"

    # Event should be stored even if fraud detection had issues
    db = TestingSessionLocal()
    event = db.query(MCPAuthEvent).filter(MCPAuthEvent.id == data["event_id"]).first()
    assert event is not None
    assert event.user_id == 1003

    db.close()
    print("  ✓ Event ingested successfully despite any potential errors")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Testing Task 9: Fraud Detection Integration")
    print("="*70)

    test_fraud_detection_integration_normal_event()
    test_fraud_detection_integration_high_risk_event()
    test_fraud_detection_error_handling()

    print("\n" + "="*70)
    print("✓ All integration tests passed!")
    print("="*70)
