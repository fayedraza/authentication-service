"""
Unit tests for dev monitor endpoint.
"""
import pytest
import os
from unittest.mock import Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from auth_platform.auth_platform.auth_service.routes import dev_monitor
from auth_platform.auth_platform.auth_service.models import AuthEvent, User
from auth_platform.auth_platform.auth_service.db import Base, engine, get_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def reset_database():
    # Drop all tables and recreate them before each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def db_session():
    """Create a database session for testing."""
    session = Session(bind=engine)
    yield session
    session.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        username="testuser",
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password="hashed_password",  # pragma: allowlist secret
        tier="dev"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_events(db_session, test_user):
    """Create test authentication events."""
    events = []
    event_types = ["login_success", "login_failure", "2fa_success", "2fa_failure", "password_reset"]

    for i, event_type in enumerate(event_types):
        event = AuthEvent(
            user_id=test_user.id,
            username=test_user.username,
            event_type=event_type,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 Test Browser",
            timestamp=datetime.utcnow(),
            event_metadata={"test": f"event_{i}"}
        )
        db_session.add(event)
        events.append(event)

    db_session.commit()
    return events


@pytest.fixture
def test_app(db_session):
    """Create a test FastAPI app with dev_monitor router."""
    app = FastAPI()

    # Override get_db dependency to use test session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.include_router(dev_monitor.router)
    return app


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


def test_endpoint_returns_events_when_dev_mode_enabled_and_local_ip(client, test_events):
    """Test endpoint returns events when DEV_MODE=true and local IP."""
    with patch.dict(os.environ, {"DEV_MODE": "true"}):
        with patch("auth_platform.auth_platform.auth_service.routes.dev_monitor.is_local_request", return_value=True):
            response = client.get("/dev/event-logs")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 5

            # Verify structure of first event
            assert "id" in data[0]
            assert "user_id" in data[0]
            assert "username" in data[0]
            assert "event_type" in data[0]
            assert "timestamp" in data[0]


def test_endpoint_returns_404_when_dev_mode_disabled(client, test_events):
    """Test endpoint returns 404 when DEV_MODE=false."""
    with patch.dict(os.environ, {"DEV_MODE": "false"}):
        response = client.get("/dev/event-logs")

        assert response.status_code == 404
        # FastAPI returns "Not Found" by default
        assert "not found" in response.json()["detail"].lower()


def test_endpoint_returns_403_when_request_from_external_ip(client, test_events):
    """Test endpoint returns 403 when request from external IP."""
    with patch.dict(os.environ, {"DEV_MODE": "true"}):
        # Mock the request to have an external IP
        with patch("auth_platform.auth_platform.auth_service.routes.dev_monitor.is_local_request", return_value=False):
            response = client.get("/dev/event-logs")

            assert response.status_code == 403
            assert response.json()["detail"] == "Forbidden"


def test_endpoint_returns_400_when_limit_exceeds_1000(client, test_events):
    """Test endpoint returns 400 when limit exceeds 1000."""
    with patch.dict(os.environ, {"DEV_MODE": "true"}):
        with patch("auth_platform.auth_platform.auth_service.routes.dev_monitor.is_local_request", return_value=True):
            response = client.get("/dev/event-logs?limit=2000")

            assert response.status_code == 400
            assert "cannot exceed 1000" in response.json()["detail"]


def test_filtering_by_event_type_works_correctly(client, db_session, test_user):
    """Test filtering by event_type works correctly."""
    # Create events with different types
    for _ in range(3):
        event = AuthEvent(
            user_id=test_user.id,
            username=test_user.username,
            event_type="login_success",
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )
        db_session.add(event)

    for _ in range(2):
        event = AuthEvent(
            user_id=test_user.id,
            username=test_user.username,
            event_type="login_failure",
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )
        db_session.add(event)

    db_session.commit()

    with patch.dict(os.environ, {"DEV_MODE": "true"}):
        with patch("auth_platform.auth_platform.auth_service.routes.dev_monitor.is_local_request", return_value=True):
            response = client.get("/dev/event-logs?event_type=login_success")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert all(event["event_type"] == "login_success" for event in data)


def test_filtering_by_user_id_works_correctly(client, db_session):
    """Test filtering by user_id works correctly."""
    # Create two users
    user1 = User(username="user1", email="user1@example.com", password="pass", tier="dev")
    user2 = User(username="user2", email="user2@example.com", password="pass", tier="dev")
    db_session.add(user1)
    db_session.add(user2)
    db_session.commit()

    # Create events for both users
    for _ in range(3):
        event = AuthEvent(
            user_id=user1.id,
            username=user1.username,
            event_type="login_success",
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )
        db_session.add(event)

    for _ in range(2):
        event = AuthEvent(
            user_id=user2.id,
            username=user2.username,
            event_type="login_success",
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )
        db_session.add(event)

    db_session.commit()

    with patch.dict(os.environ, {"DEV_MODE": "true"}):
        with patch("auth_platform.auth_platform.auth_service.routes.dev_monitor.is_local_request", return_value=True):
            response = client.get(f"/dev/event-logs?user_id={user1.id}")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert all(event["user_id"] == user1.id for event in data)


def test_combining_event_type_and_user_id_filters(client, db_session):
    """Test combining event_type and user_id filters."""
    # Create two users
    user1 = User(username="user1", email="user1@example.com", password="pass", tier="dev")
    user2 = User(username="user2", email="user2@example.com", password="pass", tier="dev")
    db_session.add(user1)
    db_session.add(user2)
    db_session.commit()

    # Create various events
    # User1: 2 login_success, 1 login_failure
    for _ in range(2):
        event = AuthEvent(
            user_id=user1.id,
            username=user1.username,
            event_type="login_success",
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )
        db_session.add(event)

    event = AuthEvent(
        user_id=user1.id,
        username=user1.username,
        event_type="login_failure",
        ip_address="192.168.1.1",
        user_agent="Test Browser"
    )
    db_session.add(event)

    # User2: 1 login_success
    event = AuthEvent(
        user_id=user2.id,
        username=user2.username,
        event_type="login_success",
        ip_address="192.168.1.1",
        user_agent="Test Browser"
    )
    db_session.add(event)

    db_session.commit()

    with patch.dict(os.environ, {"DEV_MODE": "true"}):
        with patch("auth_platform.auth_platform.auth_service.routes.dev_monitor.is_local_request", return_value=True):
            response = client.get(f"/dev/event-logs?user_id={user1.id}&event_type=login_success")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert all(event["user_id"] == user1.id for event in data)
            assert all(event["event_type"] == "login_success" for event in data)


def test_events_are_ordered_by_timestamp_descending(client, db_session, test_user):
    """Test events are ordered by timestamp descending."""
    import time

    # Create events with slight time differences
    events = []
    for i in range(5):
        event = AuthEvent(
            user_id=test_user.id,
            username=test_user.username,
            event_type="login_success",
            ip_address="192.168.1.1",
            user_agent="Test Browser",
            timestamp=datetime.utcnow()
        )
        db_session.add(event)
        db_session.commit()
        events.append(event)
        time.sleep(0.01)  # Small delay to ensure different timestamps

    with patch.dict(os.environ, {"DEV_MODE": "true"}):
        with patch("auth_platform.auth_platform.auth_service.routes.dev_monitor.is_local_request", return_value=True):
            response = client.get("/dev/event-logs")

            assert response.status_code == 200
            data = response.json()

            # Verify events are in descending order (most recent first)
            timestamps = [event["timestamp"] for event in data]
            assert timestamps == sorted(timestamps, reverse=True)


def test_endpoint_respects_limit_parameter(client, db_session, test_user):
    """Test endpoint respects limit parameter."""
    # Create 10 events
    for i in range(10):
        event = AuthEvent(
            user_id=test_user.id,
            username=test_user.username,
            event_type="login_success",
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )
        db_session.add(event)

    db_session.commit()

    with patch.dict(os.environ, {"DEV_MODE": "true"}):
        with patch("auth_platform.auth_platform.auth_service.routes.dev_monitor.is_local_request", return_value=True):
            response = client.get("/dev/event-logs?limit=5")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 5


def test_endpoint_uses_default_limit_of_50(client, db_session, test_user):
    """Test endpoint uses default limit of 50."""
    # Create 60 events
    for i in range(60):
        event = AuthEvent(
            user_id=test_user.id,
            username=test_user.username,
            event_type="login_success",
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )
        db_session.add(event)

    db_session.commit()

    with patch.dict(os.environ, {"DEV_MODE": "true"}):
        with patch("auth_platform.auth_platform.auth_service.routes.dev_monitor.is_local_request", return_value=True):
            response = client.get("/dev/event-logs")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 50
