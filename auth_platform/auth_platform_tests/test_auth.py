from fastapi.testclient import TestClient
from auth_platform.auth_platform.auth_service.main import app
import pytest
from auth_platform.auth_platform.auth_service.db import Base, engine, get_db
from auth_platform.auth_platform.auth_service.models import AuthEvent

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

import sqlalchemy

@pytest.fixture(autouse=True)
def reset_database():
    # Drop all tables and recreate them before each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def test_register_and_login(client):
    # Use a unique username and email for each test run to avoid conflicts
    import uuid
    unique = uuid.uuid4().hex[:8]
    username = f"user_{unique}"
    email = f"user_{unique}@example.com"
    password = "testing12345"
    register_data = {
        "username": username,
        "first_name": "Bob",
        "last_name": "Smith",
        "email": email,
        "password": password,
        "tier": "dev"
    }
    register = client.post("/register", json=register_data)
    assert register.status_code == 200
    # Registration now auto-enables 2FA
    assert "otpauth_uri" in register.json()
    assert register.json()["requires_2fa_setup"] is True

    # Login now requires 2FA
    login = client.post("/login", json={"username": username, "password": password})
    assert login.status_code == 200
    # Should require 2FA verification
    assert "requires2fa" in login.json()
    assert login.json()["requires2fa"] is True


def test_register_missing_fields(client):
    # Missing required fields should return 422
    incomplete_data = {
        "username": "user1",
        "password": "pass"
        # missing first_name, last_name, email, tier
    }
    response = client.post("/register", json=incomplete_data)
    assert response.status_code == 422


def test_login_invalid_password(client):
    import uuid
    unique = uuid.uuid4().hex[:8]
    username = f"testuser_{unique}"
    email = f"testuser_{unique}@example.com"
    password = "goodpassword"
    register_data = {
        "username": username,
        "first_name": "Alice",
        "last_name": "Wonder",
        "email": email,
        "password": password,
        "tier": "pro"
    }
    reg = client.post("/register", json=register_data)
    assert reg.status_code == 200
    # Registration now auto-enables 2FA
    assert "otpauth_uri" in reg.json()

    # Try to login with wrong password
    bad_login = client.post("/login", json={"username": username, "password": "wrongpassword"})
    assert bad_login.status_code == 401


def test_login_success_logs_event(client):
    """Test that successful login without 2FA logs a login_success event"""
    import uuid
    unique = uuid.uuid4().hex[:8]
    username = f"user_{unique}"
    email = f"user_{unique}@example.com"
    password = "testing12345"

    # Register user with dev tier (2FA auto-enabled)
    register_data = {
        "username": username,
        "first_name": "Test",
        "last_name": "User",
        "email": email,
        "password": password,
        "tier": "dev"
    }
    register = client.post("/register", json=register_data)
    assert register.status_code == 200

    # Disable 2FA to test login without 2FA
    disable_response = client.post("/2fa/disable", json={"username": username, "password": password})
    assert disable_response.status_code == 200

    # Login without 2FA
    login = client.post("/login", json={"username": username, "password": password})
    assert login.status_code == 200
    assert "access_token" in login.json()

    # Query auth_events table to verify login_success event
    db = next(get_db())
    events = db.query(AuthEvent).filter(
        AuthEvent.username == username,
        AuthEvent.event_type == "login_success"
    ).all()

    assert len(events) == 1
    event = events[0]
    assert event.username == username
    assert event.event_type == "login_success"
    assert event.ip_address is not None
    assert event.timestamp is not None


def test_login_failure_logs_event(client):
    """Test that failed login attempts log a login_failure event"""
    import uuid
    unique = uuid.uuid4().hex[:8]
    username = f"user_{unique}"
    email = f"user_{unique}@example.com"
    password = "correctpassword"

    # Register user
    register_data = {
        "username": username,
        "first_name": "Test",
        "last_name": "User",
        "email": email,
        "password": password,
        "tier": "dev"
    }
    register = client.post("/register", json=register_data)
    assert register.status_code == 200

    # Attempt login with wrong password
    bad_login = client.post("/login", json={"username": username, "password": "wrongpassword"})
    assert bad_login.status_code == 401

    # Query auth_events table to verify login_failure event
    db = next(get_db())
    events = db.query(AuthEvent).filter(
        AuthEvent.username == username,
        AuthEvent.event_type == "login_failure"
    ).all()

    assert len(events) == 1
    event = events[0]
    assert event.username == username
    assert event.event_type == "login_failure"
    assert event.ip_address is not None
    assert event.timestamp is not None
