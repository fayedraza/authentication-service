
import pytest
from fastapi.testclient import TestClient
from auth_platform.auth_service.main import app
from auth_platform.auth_service.db import Base, engine, get_db, SessionLocal
from auth_platform.auth_service.models import User
from auth_platform.auth_service.routes.api_keys import get_current_user

# Define standard fixtures
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)

@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides = {} # Clear overrides

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

# Mock data
MOCK_USER_DEV = {
    "username": "unittest_dev",
    "password": "password",
    "email": "dev@unit.test",
    "first_name": "Dev",
    "last_name": "Test",
    "tier": "dev"
}

MOCK_USER_PRO = {
    "username": "unittest_pro",
    "password": "password",
    "email": "pro@unit.test",
    "first_name": "Pro",
    "last_name": "Test",
    "tier": "pro"
}

def setup_user(db, user_data):
    """Create user in DB and return the object."""
    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def test_create_api_key_dev_limit(client, db):
    """Test Dev tier limit of 1 key."""
    user = setup_user(db, MOCK_USER_DEV)
    app.dependency_overrides[get_current_user] = lambda: user

    # 1. Create First Key (Should Succeed)
    resp = client.post("/api-keys", json={"label": "Key 1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] == "Key 1"
    assert "key" in data

    # 2. Create Second Key (Should Fail)
    resp = client.post("/api-keys", json={"label": "Key 2"})
    assert resp.status_code == 403
    assert "Dev tier is limited" in resp.json()["detail"]

def test_create_api_key_pro_unlimited(client, db):
    """Test Pro tier can create multiple keys."""
    user = setup_user(db, MOCK_USER_PRO)
    app.dependency_overrides[get_current_user] = lambda: user

    for i in range(3):
        resp = client.post("/api-keys", json={"label": f"Pro Key {i}"})
        assert resp.status_code == 200

def test_list_api_keys(client, db):
    """Test listing keys."""
    user = setup_user(db, MOCK_USER_PRO)
    app.dependency_overrides[get_current_user] = lambda: user

    # Create one manually verify list
    client.post("/api-keys", json={"label": "List Me"})

    resp = client.get("/api-keys")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["label"] == "List Me"

def test_rotate_api_key(client, db):
    """Test rotating a key."""
    user = setup_user(db, MOCK_USER_PRO)
    app.dependency_overrides[get_current_user] = lambda: user

    # Create key
    resp = client.post("/api-keys", json={"label": "To Rotate"})
    original_key = resp.json()
    key_id = original_key["id"]

    # Rotate
    resp = client.post(f"/api-keys/{key_id}/rotate")
    assert resp.status_code == 200
    new_key = resp.json()

    assert new_key["id"] != key_id
    assert new_key["label"] == "To Rotate"
    assert new_key["key"] != original_key["key"]

def test_revoke_api_key(client, db):
    """Test revoking a key."""
    user = setup_user(db, MOCK_USER_PRO)
    app.dependency_overrides[get_current_user] = lambda: user

    # Create key
    resp = client.post("/api-keys", json={"label": "To Revoke"})
    key_id = resp.json()["id"]

    # Revoke
    resp = client.delete(f"/api-keys/{key_id}")
    assert resp.status_code == 200

    # Verify it's gone from active list
    resp = client.get("/api-keys")
    active_ids = [k["id"] for k in resp.json()]
    assert key_id not in active_ids
