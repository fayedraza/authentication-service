"""
Integration tests for MCP Server.

This test suite verifies the complete functionality of the MCP Server including:
- Event ingestion flow: POST event → verify storage → verify fraud analysis
- Alert generation for high-risk events
- Alert consolidation for multiple events
- Query APIs with filtering and pagination
- Health and readiness endpoints

Requirements: All (1.1-7.5)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI

from mcp_server.db import Base, get_db
from mcp_server.config import settings
from mcp_server.models import MCPAuthEvent, MCPAlert

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


# Create test app without lifespan (to avoid init_db on production database)
@asynccontextmanager
async def test_lifespan(app: FastAPI):
    """Test lifespan - tables already created"""
    yield


# Import routes after database setup
from mcp_server.routes import ingest, events, fraud_assessments, alerts, health
from fastapi.middleware.cors import CORSMiddleware

# Create test app
test_app = FastAPI(
    title="MCP Server Test",
    description="Test instance of MCP Server",
    version="1.0.0",
    lifespan=test_lifespan
)

# Configure CORS
test_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
test_app.include_router(ingest.router)
test_app.include_router(events.router)
test_app.include_router(fraud_assessments.router)
test_app.include_router(alerts.router)
test_app.include_router(health.router)

# Override database dependency
test_app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(test_app)


@pytest.fixture
def clean_db():
    """Clean database before each test"""
    db = TestingSessionLocal()
    try:
        db.query(MCPAlert).delete()
        db.query(MCPAuthEvent).delete()
        db.commit()
    except Exception:
        # Tables might not exist yet, that's okay
        db.rollback()
    finally:
        db.close()

    yield

    # Cleanup after test
    db = TestingSessionLocal()
    try:
        db.query(MCPAlert).delete()
        db.query(MCPAuthEvent).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# ============================================================================
# Event Ingestion Flow Tests
# ============================================================================

def test_event_ingestion_flow_complete(clean_db):
    """
    Test complete event ingestion flow: POST event → verify storage → verify fraud analysis
    Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 3.1, 3.4
    """
    # POST event
    event_data = {
        "user_id": 100,
        "username": "test_user",
        "event_type": "login_success",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": {"session_id": "test-session-123"}
    }

    response = client.post("/mcp/ingest", json=event_data)

    # Verify response
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"
    assert "event_id" in data
    event_id = data["event_id"]

    # Verify storage
    db = TestingSessionLocal()
    stored_event = db.query(MCPAuthEvent).filter(MCPAuthEvent.id == event_id).first()

    assert stored_event is not None
    assert stored_event.user_id == 100
    assert stored_event.username == "test_user"
    assert stored_event.event_type == "login_success"
    assert stored_event.ip_address == "192.168.1.100"
    assert stored_event.user_agent == "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    assert stored_event.event_metadata == {"session_id": "test-session-123"}

    # Verify fraud analysis
    assert stored_event.risk_score is not None
    assert 0.0 <= stored_event.risk_score <= 1.0
    assert stored_event.fraud_reason is not None
    assert stored_event.analyzed_at is not None

    db.close()


def test_event_ingestion_validation_error(clean_db):
    """
    Test event ingestion with invalid data
    Requirements: 1.5
    """
    # Invalid event_type
    invalid_event = {
        "user_id": 100,
        "username": "test_user",
        "event_type": "invalid_type",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    response = client.post("/mcp/ingest", json=invalid_event)
    assert response.status_code == 422

    # Missing required field
    incomplete_event = {
        "user_id": 100,
        "event_type": "login_success"
        # Missing username and timestamp
    }

    response = client.post("/mcp/ingest", json=incomplete_event)
    assert response.status_code == 422


def test_event_ingestion_multiple_event_types(clean_db):
    """
    Test ingestion of different event types
    Requirements: 1.3
    """
    event_types = [
        "login_success",
        "login_failure",
        "2fa_success",
        "2fa_failure",
        "password_reset",
        "password_reset_request"
    ]

    for event_type in event_types:
        event_data = {
            "user_id": 101,
            "username": "multi_event_user",
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        response = client.post("/mcp/ingest", json=event_data)
        assert response.status_code == 201


# ============================================================================
# Alert Generation Tests
# ============================================================================

def test_alert_generation_for_high_risk_event(clean_db):
    """
    Test that alerts are generated for high-risk events
    Requirements: 4.1, 4.2, 4.3
    """
    db = TestingSessionLocal()
    user_id = 200
    base_time = datetime.utcnow()

    # Create previous successful login
    prev_event = MCPAuthEvent(
        id="prev-200",
        user_id=user_id,
        username="alert_test_user",
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db.add(prev_event)

    # Create multiple failed login attempts to trigger high risk
    for i in range(4):
        failed_event = MCPAuthEvent(
            id=f"failed-200-{i}",
            user_id=user_id,
            username="alert_test_user",
            event_type="login_failure",
            ip_address="10.0.0.50",
            user_agent="Chrome/91.0",
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db.add(failed_event)

    db.commit()
    db.close()

    # Ingest new high-risk event
    event_data = {
        "user_id": user_id,
        "username": "alert_test_user",
        "event_type": "login_failure",
        "ip_address": "10.0.0.50",
        "user_agent": "Chrome/91.0",
        "timestamp": base_time.isoformat() + "Z",
        "metadata": {}
    }

    response = client.post("/mcp/ingest", json=event_data)
    assert response.status_code == 201
    event_id = response.json()["event_id"]

    # Verify alert was created
    db = TestingSessionLocal()
    alert = db.query(MCPAlert).filter(MCPAlert.user_id == user_id).first()

    assert alert is not None
    assert alert.status == "open"
    assert alert.risk_score >= settings.FRAUD_THRESHOLD
    assert event_id in alert.event_ids
    assert alert.username == "alert_test_user"
    assert len(alert.reason) > 0

    db.close()


def test_no_alert_for_low_risk_event(clean_db):
    """
    Test that no alerts are generated for low-risk events
    Requirements: 4.1
    """
    event_data = {
        "user_id": 201,
        "username": "normal_user",
        "event_type": "login_success",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": {}
    }

    response = client.post("/mcp/ingest", json=event_data)
    assert response.status_code == 201

    # Verify no alert was created
    db = TestingSessionLocal()
    alert = db.query(MCPAlert).filter(MCPAlert.user_id == 201).first()
    assert alert is None
    db.close()


# ============================================================================
# Alert Consolidation Tests
# ============================================================================

def test_alert_consolidation_multiple_events(clean_db):
    """
    Test that multiple high-risk events within consolidation window are consolidated
    Requirements: 4.5
    """
    db = TestingSessionLocal()
    user_id = 300
    base_time = datetime.utcnow()

    # Create historical events to trigger high risk
    for i in range(3):
        failed_event = MCPAuthEvent(
            id=f"setup-300-{i}",
            user_id=user_id,
            username="consolidation_user",
            event_type="login_failure",
            ip_address="10.0.0.50",
            user_agent="Chrome/91.0",
            timestamp=base_time - timedelta(minutes=10+i),
            event_metadata={}
        )
        db.add(failed_event)

    db.commit()
    db.close()

    # Ingest first high-risk event
    event_data_1 = {
        "user_id": user_id,
        "username": "consolidation_user",
        "event_type": "login_failure",
        "ip_address": "10.0.0.50",
        "user_agent": "Chrome/91.0",
        "timestamp": base_time.isoformat() + "Z",
        "metadata": {}
    }

    response1 = client.post("/mcp/ingest", json=event_data_1)
    assert response1.status_code == 201
    event_id_1 = response1.json()["event_id"]

    # Ingest second high-risk event within consolidation window
    event_data_2 = {
        "user_id": user_id,
        "username": "consolidation_user",
        "event_type": "login_failure",
        "ip_address": "10.0.0.51",
        "user_agent": "Chrome/91.0",
        "timestamp": (base_time + timedelta(minutes=2)).isoformat() + "Z",
        "metadata": {}
    }

    response2 = client.post("/mcp/ingest", json=event_data_2)
    assert response2.status_code == 201
    event_id_2 = response2.json()["event_id"]

    # Verify only one alert exists with both events
    db = TestingSessionLocal()
    alerts = db.query(MCPAlert).filter(MCPAlert.user_id == user_id).all()

    assert len(alerts) == 1
    alert = alerts[0]
    assert event_id_1 in alert.event_ids
    assert event_id_2 in alert.event_ids
    assert len(alert.event_ids) >= 2

    db.close()


def test_alert_consolidation_window_expired(clean_db):
    """
    Test that alerts are not consolidated outside the consolidation window
    Requirements: 4.5
    """
    db = TestingSessionLocal()
    user_id = 301
    base_time = datetime.utcnow()

    # Create first alert manually (simulating old alert)
    old_alert = MCPAlert(
        id="old-alert-301",
        user_id=user_id,
        username="window_test_user",
        event_ids=["old-event-301"],
        risk_score=0.8,
        reason="Old high-risk event",
        status="open",
        created_at=base_time - timedelta(minutes=settings.ALERT_CONSOLIDATION_WINDOW_MINUTES + 1),
        updated_at=base_time - timedelta(minutes=settings.ALERT_CONSOLIDATION_WINDOW_MINUTES + 1)
    )
    db.add(old_alert)

    # Create historical events for new alert
    for i in range(3):
        failed_event = MCPAuthEvent(
            id=f"setup-301-{i}",
            user_id=user_id,
            username="window_test_user",
            event_type="login_failure",
            ip_address="10.0.0.50",
            user_agent="Chrome/91.0",
            timestamp=base_time - timedelta(minutes=10+i),
            event_metadata={}
        )
        db.add(failed_event)

    db.commit()
    db.close()

    # Ingest new high-risk event
    event_data = {
        "user_id": user_id,
        "username": "window_test_user",
        "event_type": "login_failure",
        "ip_address": "10.0.0.50",
        "user_agent": "Chrome/91.0",
        "timestamp": base_time.isoformat() + "Z",
        "metadata": {}
    }

    response = client.post("/mcp/ingest", json=event_data)
    assert response.status_code == 201

    # Verify two separate alerts exist
    db = TestingSessionLocal()
    alerts = db.query(MCPAlert).filter(MCPAlert.user_id == user_id).all()

    assert len(alerts) == 2

    db.close()


# ============================================================================
# Query API Tests
# ============================================================================

def test_query_events_with_filtering(clean_db):
    """
    Test event query API with various filters
    Requirements: 2.2, 2.3, 2.4
    """
    db = TestingSessionLocal()
    base_time = datetime.utcnow()

    # Create test events
    events_data = [
        (400, "user_400", "login_success", base_time - timedelta(hours=2)),
        (400, "user_400", "login_failure", base_time - timedelta(hours=1)),
        (401, "user_401", "login_success", base_time - timedelta(minutes=30)),
        (401, "user_401", "2fa_success", base_time - timedelta(minutes=15)),
    ]

    for user_id, username, event_type, timestamp in events_data:
        event = MCPAuthEvent(
            user_id=user_id,
            username=username,
            event_type=event_type,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=timestamp,
            event_metadata={},
            risk_score=0.1,
            fraud_reason="Normal activity",
            analyzed_at=timestamp
        )
        db.add(event)

    db.commit()
    db.close()

    # Test filter by user_id
    response = client.get("/mcp/events?user_id=400")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(event["user_id"] == 400 for event in data["events"])

    # Test filter by event_type
    response = client.get("/mcp/events?event_type=login_success")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(event["event_type"] == "login_success" for event in data["events"])

    # Test combined filters
    response = client.get("/mcp/events?user_id=401&event_type=2fa_success")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["events"][0]["user_id"] == 401
    assert data["events"][0]["event_type"] == "2fa_success"


def test_query_events_with_pagination(clean_db):
    """
    Test event query API pagination
    Requirements: 2.4
    """
    db = TestingSessionLocal()
    base_time = datetime.utcnow()

    # Create 25 test events
    for i in range(25):
        event = MCPAuthEvent(
            user_id=500,
            username="pagination_user",
            event_type="login_success",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=i),
            event_metadata={},
            risk_score=0.1,
            fraud_reason="Normal",
            analyzed_at=base_time
        )
        db.add(event)

    db.commit()
    db.close()

    # Test first page
    response = client.get("/mcp/events?user_id=500&limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert len(data["events"]) == 10

    # Test second page
    response = client.get("/mcp/events?user_id=500&limit=10&offset=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert data["limit"] == 10
    assert data["offset"] == 10
    assert len(data["events"]) == 10

    # Test last page
    response = client.get("/mcp/events?user_id=500&limit=10&offset=20")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert len(data["events"]) == 5


def test_query_alerts_with_filtering(clean_db):
    """
    Test alert query API with filters
    Requirements: 4.2, 4.3
    """
    db = TestingSessionLocal()
    base_time = datetime.utcnow()

    # Create test alerts
    alerts_data = [
        (600, "user_600", 0.8, "open"),
        (601, "user_601", 0.9, "reviewed"),
        (602, "user_602", 0.75, "open"),
        (603, "user_603", 0.65, "resolved"),
    ]

    for user_id, username, risk_score, status in alerts_data:
        alert = MCPAlert(
            user_id=user_id,
            username=username,
            event_ids=[f"event-{user_id}"],
            risk_score=risk_score,
            reason="High-risk activity detected",
            status=status,
            created_at=base_time,
            updated_at=base_time
        )
        db.add(alert)

    db.commit()
    db.close()

    # Test filter by status
    response = client.get("/mcp/alerts?status=open")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(alert["status"] == "open" for alert in data["alerts"])

    # Test filter by min_risk_score
    response = client.get("/mcp/alerts?min_risk_score=0.8")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(alert["risk_score"] >= 0.8 for alert in data["alerts"])

    # Test filter by user_id
    response = client.get("/mcp/alerts?user_id=600")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["alerts"][0]["user_id"] == 600


def test_update_alert_status(clean_db):
    """
    Test updating alert status
    Requirements: 4.4
    """
    db = TestingSessionLocal()

    # Create test alert
    alert = MCPAlert(
        id="test-alert-700",
        user_id=700,
        username="user_700",
        event_ids=["event-700"],
        risk_score=0.85,
        reason="High-risk activity",
        status="open",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(alert)
    db.commit()
    db.close()

    # Update status to reviewed
    response = client.patch(
        "/mcp/alerts/test-alert-700",
        json={"status": "reviewed"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "reviewed"
    assert data["id"] == "test-alert-700"

    # Verify in database
    db = TestingSessionLocal()
    updated_alert = db.query(MCPAlert).filter(MCPAlert.id == "test-alert-700").first()
    assert updated_alert.status == "reviewed"
    db.close()


def test_query_fraud_assessments(clean_db):
    """
    Test fraud assessment query API
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
    """
    db = TestingSessionLocal()
    base_time = datetime.utcnow()

    # Create events with various risk scores
    risk_scores = [0.2, 0.5, 0.8, 0.9, 0.3, 0.6, 0.1]

    for i, risk_score in enumerate(risk_scores):
        event = MCPAuthEvent(
            user_id=800 + i,
            username=f"user_{800+i}",
            event_type="login_success" if risk_score < 0.5 else "login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=i),
            event_metadata={},
            risk_score=risk_score,
            fraud_reason=f"Risk level: {risk_score}",
            analyzed_at=base_time
        )
        db.add(event)

    db.commit()
    db.close()

    # Test basic query
    response = client.get("/mcp/fraud-assessments")
    assert response.status_code == 200
    data = response.json()
    assert "assessments" in data
    assert "statistics" in data
    assert data["total"] == 7

    # Verify statistics
    stats = data["statistics"]
    assert stats["total_events"] == 7
    assert stats["high_risk_events"] == 2  # > 0.7
    assert stats["medium_risk_events"] == 2  # 0.4 < score <= 0.7
    assert stats["low_risk_events"] == 3  # <= 0.4
    assert 0.0 <= stats["average_risk_score"] <= 1.0

    # Test filter by risk score range
    response = client.get("/mcp/fraud-assessments?min_risk_score=0.7")
    assert response.status_code == 200
    data = response.json()
    assert all(assessment["risk_score"] >= 0.7 for assessment in data["assessments"])


# ============================================================================
# Health Check Tests
# ============================================================================

def test_health_endpoint(clean_db):
    """
    Test health check endpoint
    Requirements: 6.5
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_readiness_endpoint(clean_db):
    """
    Test readiness check endpoint
    Requirements: 6.5
    """
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert "baml_agent" in data
    assert "timestamp" in data


# ============================================================================
# Run all tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
