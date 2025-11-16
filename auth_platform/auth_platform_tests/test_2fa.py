from fastapi.testclient import TestClient
from auth_platform.auth_platform.auth_service.main import app
import pytest
from auth_platform.auth_platform.auth_service.db import Base, engine
from sqlalchemy.orm import Session
from auth_platform.auth_platform.auth_service.db import SessionLocal
from auth_platform.auth_platform.auth_service.models import User
from auth_platform.auth_platform.auth_service.auth import hash_password
import pyotp


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_database():
    # Drop all tables and recreate them before each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def ensure_user(username: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(username=username, first_name="T", last_name="U", email=f"{username}@example.com", password=hash_password(password), tier="dev")
            db.add(user)
            db.commit()
    finally:
        db.close()


def test_enroll_returns_otpauth_uri(client):
    username = "alice"
    password = "Secret123!"
    ensure_user(username, password)

    resp = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    assert "otpauth://" in data["otpauth_uri"]


def test_verify_accepts_correct_code_and_rejects_wrong(client):
    username = "bob"
    password = "Secret123!"
    ensure_user(username, password)

    # enroll 2FA
    enroll = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert enroll.status_code == 200

    # fetch secret from DB to compute a valid code (test-only)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        secret = user.totp_secret
    finally:
        db.close()

    totp = pyotp.TOTP(secret)
    good_code = totp.now()

    ok = client.post("/2fa/verify", json={"username": username, "code": good_code})
    assert ok.status_code == 200
    assert "access_token" in ok.json()

    bad = client.post("/2fa/verify", json={"username": username, "code": "000000"})
    assert bad.status_code == 401


def test_login_flow_with_and_without_2fa(client):
    # user without 2FA
    username_no2fa = "charlie"
    password = "Secret123!"
    ensure_user(username_no2fa, password)

    no2fa = client.post("/login", json={"username": username_no2fa, "password": password})
    assert no2fa.status_code == 200
    assert "access_token" in no2fa.json()

    # user with 2FA enabled
    username_2fa = "dora"
    ensure_user(username_2fa, password)
    enroll = client.post("/2fa/enroll", json={"username": username_2fa, "password": password})
    assert enroll.status_code == 200

    step1 = client.post("/login", json={"username": username_2fa, "password": password})
    assert step1.status_code == 200
    data = step1.json()
    assert data.get("requires2fa") is True

    # Verify step with valid code
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username_2fa).first()
        secret = user.totp_secret
    finally:
        db.close()

    code = pyotp.TOTP(secret).now()
    step2 = client.post("/2fa/verify", json={"username": username_2fa, "code": code})
    assert step2.status_code == 200
    assert "access_token" in step2.json()
