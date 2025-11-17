from fastapi.testclient import TestClient
from auth_platform.auth_platform.auth_service.main import app
from auth_platform.auth_platform.auth_service.db import Base, engine, SessionLocal
from auth_platform.auth_platform.auth_service.models import User, PasswordResetToken
from auth_platform.auth_platform.auth_service.auth import hash_password
import time
from datetime import datetime, timedelta

client = TestClient(app)


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def ensure_user(email="user@example.com", username="user", password="Secret123!", tier="dev"):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        if not u:
            u = User(username=username, first_name="A", last_name="B", email=email, password=hash_password(password), tier=tier)
            db.add(u)
            db.commit()
        # return stable scalar values to avoid DetachedInstance
        return {"username": username, "email": email}
    finally:
        db.close()


def test_password_reset_request_creates_token():
    reset_db()
    user_info = ensure_user()

    resp = client.post("/password-reset/request", json={"email": user_info["email"]})
    assert resp.status_code == 200

    # Check token exists in DB and has ~15 min expiry
    db = SessionLocal()
    try:
        # look up user id from email
        u = db.query(User).filter(User.email == user_info["email"]).first()
        prt = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == u.id).first()
        assert prt is not None
        assert not prt.used
        now = datetime.utcnow()
        assert now + timedelta(minutes=14) <= prt.expires_at <= now + timedelta(minutes=16)
    finally:
        db.close()


def test_password_reset_confirm_updates_password():
    reset_db()
    user_info = ensure_user(password="OldPass1!")

    # Request a token
    resp = client.post("/password-reset/request", json={"email": user_info["email"]})
    assert resp.status_code == 200

    # Load token directly from DB (simulating email)
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == user_info["email"]).first()
        prt = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == u.id).first()
        token = prt.token
    finally:
        db.close()

    # Confirm with new password
    confirm = client.post("/password-reset/confirm", json={"token": token, "new_password": "NewPass2!"})
    assert confirm.status_code == 200

    # Token should be marked used; password changed (try login)
    login = client.post("/login", json={"username": user_info["username"], "password": "NewPass2!"})
    assert login.status_code == 200

    # Reuse should fail
    reuse = client.post("/password-reset/confirm", json={"token": token, "new_password": "Another!3"})
    assert reuse.status_code == 400


def test_password_reset_confirm_rejects_invalid_token():
    reset_db()
    ensure_user()
    bad = client.post("/password-reset/confirm", json={"token": "not-a-token", "new_password": "x"})
    assert bad.status_code == 400
