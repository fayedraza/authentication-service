from fastapi.testclient import TestClient
from auth_platform.auth_platform.auth_service.main import app
import pytest
from auth_platform.auth_platform.auth_service.db import Base, engine

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
    username = f"bob_{unique}"
    email = f"bob_{unique}@example.com"
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

    login = client.post("/login", json={"username": username, "password": password})
    assert login.status_code == 200
    assert "access_token" in login.json()


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
    username = f"alice_{unique}"
    email = f"alice_{unique}@example.com"
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

    # Try to login with wrong password
    bad_login = client.post("/login", json={"username": username, "password": "wrongpassword"})
    assert bad_login.status_code == 401
