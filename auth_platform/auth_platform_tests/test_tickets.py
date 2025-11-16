from fastapi.testclient import TestClient
from auth_platform.auth_platform.auth_service.main import app
from auth_platform.auth_platform.auth_service.db import Base, engine, SessionLocal
from auth_platform.auth_platform.auth_service.models import User
from auth_platform.auth_platform.auth_service.auth import hash_password, create_access_token

client = TestClient(app)


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def ensure_user(username="owner", email="owner@example.com", password="Secret123!", tier="dev"):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        if not u:
            u = User(username=username, first_name="O", last_name="W", email=email, password=hash_password(password), tier=tier)
            db.add(u)
            db.commit()
        return {"username": username, "email": email}
    finally:
        db.close()


def auth_header_for(username: str):
    token = create_access_token(username)
    return {"Authorization": f"Bearer {token}"}


def test_create_ticket_requires_auth():
    reset_db()
    ensure_user()
    # Missing auth
    r = client.post("/support/ticket", json={"title": "Help", "description": "I need assistance"})
    assert r.status_code == 401


def test_create_and_list_tickets():
    reset_db()
    user_info = ensure_user()

    # Create
    h = auth_header_for(user_info["username"])
    create = client.post("/support/ticket", headers=h, json={"title": "Help", "description": "I need assistance"})
    assert create.status_code == 200
    data = create.json()
    assert data["id"] > 0
    assert data["status"] == "open"

    # List
    lst = client.get("/support/tickets", headers=h)
    assert lst.status_code == 200
    items = lst.json()
    assert isinstance(items, list)
    assert len(items) == 1
    assert items[0]["title"] == "Help"
