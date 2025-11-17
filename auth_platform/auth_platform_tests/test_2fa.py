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
    username = "user1"
    password = "Secret123!"
    ensure_user(username, password)

    resp = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    assert "otpauth://" in data["otpauth_uri"]


def test_verify_accepts_correct_code_and_rejects_wrong(client):
    username = "user2"
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
    username_no2fa = "user_no2fa"
    password = "Secret123!"
    ensure_user(username_no2fa, password)

    no2fa = client.post("/login", json={"username": username_no2fa, "password": password})
    assert no2fa.status_code == 200
    assert "access_token" in no2fa.json()

    # user with 2FA enabled
    username_2fa = "user_with2fa"
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


def test_verify_rate_limiting(client):
    """Test that 5 failed TOTP verification attempts trigger rate limiting."""
    username = "rate_limit_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Enroll in 2FA
    enroll = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert enroll.status_code == 200

    # Make 5 failed attempts with invalid code
    for i in range(5):
        resp = client.post("/2fa/verify", json={"username": username, "code": "000000"})
        assert resp.status_code == 401, f"Attempt {i+1} should fail with 401"

    # 6th attempt should be rate limited
    resp = client.post("/2fa/verify", json={"username": username, "code": "000000"})
    assert resp.status_code == 429
    assert "Too many failed attempts" in resp.json()["detail"]


def test_verify_rate_limit_reset(client):
    """Test that rate limit resets after 15 minutes."""
    from datetime import datetime, timedelta
    from auth_platform.auth_platform.auth_service.models import TOTPAttempt

    username = "rate_limit_reset_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Enroll in 2FA
    enroll = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert enroll.status_code == 200

    # Get user ID
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        user_id = user.id
        secret = user.totp_secret
    finally:
        db.close()

    # Create 5 failed attempts with timestamps 16 minutes ago
    db = SessionLocal()
    try:
        old_time = datetime.utcnow() - timedelta(minutes=16)
        for i in range(5):
            attempt = TOTPAttempt(
                user_id=user_id,
                success=False,
                attempted_at=old_time + timedelta(seconds=i)
            )
            db.add(attempt)
        db.commit()
    finally:
        db.close()

    # Should be able to attempt again since old attempts are outside 15-minute window
    resp = client.post("/2fa/verify", json={"username": username, "code": "000000"})
    assert resp.status_code == 401  # Invalid code, but not rate limited
    assert "Invalid TOTP code" in resp.json()["detail"]


def test_rate_limit_per_user(client):
    """Test that rate limiting is isolated per user."""
    password = "Secret123!"

    # Create and enroll two users
    user1 = "rate_limit_user1"
    user2 = "rate_limit_user2"
    ensure_user(user1, password)
    ensure_user(user2, password)

    client.post("/2fa/enroll", json={"username": user1, "password": password})
    client.post("/2fa/enroll", json={"username": user2, "password": password})

    # Make 5 failed attempts for user1
    for i in range(5):
        resp = client.post("/2fa/verify", json={"username": user1, "code": "000000"})
        assert resp.status_code == 401

    # User1 should be rate limited
    resp = client.post("/2fa/verify", json={"username": user1, "code": "000000"})
    assert resp.status_code == 429

    # User2 should NOT be rate limited
    resp = client.post("/2fa/verify", json={"username": user2, "code": "000000"})
    assert resp.status_code == 401  # Invalid code, but not rate limited
    assert "Invalid TOTP code" in resp.json()["detail"]


def test_successful_attempts_dont_count(client):
    """Test that successful TOTP verifications don't count toward rate limit."""
    username = "success_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Enroll in 2FA
    enroll = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert enroll.status_code == 200

    # Get secret for generating valid codes
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        secret = user.totp_secret
    finally:
        db.close()

    # Make 3 successful attempts
    for i in range(3):
        code = pyotp.TOTP(secret).now()
        resp = client.post("/2fa/verify", json={"username": username, "code": code})
        assert resp.status_code == 200

    # Make 5 failed attempts
    for i in range(5):
        resp = client.post("/2fa/verify", json={"username": username, "code": "000000"})
        assert resp.status_code == 401

    # Should be rate limited now (only failed attempts count)
    resp = client.post("/2fa/verify", json={"username": username, "code": "000000"})
    assert resp.status_code == 429
    assert "Too many failed attempts" in resp.json()["detail"]


def test_enroll_generates_secret_minimum_length(client):
    """Test that enrollment generates a TOTP secret with minimum length of 16 characters."""
    username = "secret_length_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Enroll in 2FA
    resp = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert resp.status_code == 200

    # Verify secret is stored and has minimum length
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user.totp_secret is not None
        assert len(user.totp_secret) >= 16
    finally:
        db.close()


def test_enroll_enables_2fa_flag(client):
    """Test that enrollment sets the is_2fa_enabled flag to True."""
    username = "2fa_flag_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Verify 2FA is initially disabled
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user.is_2fa_enabled is False
    finally:
        db.close()

    # Enroll in 2FA
    resp = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert resp.status_code == 200

    # Verify 2FA is now enabled
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user.is_2fa_enabled is True
    finally:
        db.close()


def test_reenroll_replaces_existing_secret(client):
    """Test that re-enrollment generates a new secret and invalidates the old one."""
    username = "reenroll_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Initial enrollment
    resp1 = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert resp1.status_code == 200

    # Get first secret
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        first_secret = user.totp_secret
    finally:
        db.close()

    # Re-enroll
    resp2 = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert resp2.status_code == 200

    # Get second secret
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        second_secret = user.totp_secret
    finally:
        db.close()

    # Verify secrets are different
    assert first_secret != second_secret

    # Verify old secret no longer works
    old_code = pyotp.TOTP(first_secret).now()
    resp = client.post("/2fa/verify", json={"username": username, "code": old_code})
    assert resp.status_code == 401

    # Verify new secret works
    new_code = pyotp.TOTP(second_secret).now()
    resp = client.post("/2fa/verify", json={"username": username, "code": new_code})
    assert resp.status_code == 200


def test_enroll_invalid_credentials(client):
    """Test that enrollment fails with invalid credentials."""
    username = "invalid_creds_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Try to enroll with wrong password
    resp = client.post("/2fa/enroll", json={"username": username, "password": "WrongPassword123!"})
    assert resp.status_code == 401
    assert "Invalid credentials" in resp.json()["detail"]

    # Verify 2FA was not enabled
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user.is_2fa_enabled is False
        assert user.totp_secret is None
    finally:
        db.close()


def test_verify_with_valid_window(client):
    """Test that TOTP verification accepts codes within 30-second tolerance window."""
    import time

    username = "valid_window_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Enroll in 2FA
    enroll = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert enroll.status_code == 200

    # Get secret
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        secret = user.totp_secret
    finally:
        db.close()

    totp = pyotp.TOTP(secret)

    # Generate current code
    current_code = totp.now()

    # Verify current code works
    resp = client.post("/2fa/verify", json={"username": username, "code": current_code})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

    # Test with code from adjacent time window
    # valid_window=1 means it accepts codes from current window ±1 (30 seconds before/after)
    # Generate code for the next time window
    import time
    current_timestamp = int(time.time())
    next_window_timestamp = current_timestamp + 30
    next_code = totp.at(next_window_timestamp)

    # Verify next window code is accepted (within valid_window=1)
    resp = client.post("/2fa/verify", json={"username": username, "code": next_code})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_verify_expired_code(client):
    """Test that TOTP verification rejects codes outside the valid time window."""
    from datetime import datetime

    username = "expired_code_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Enroll in 2FA
    enroll = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert enroll.status_code == 200

    # Get secret
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        secret = user.totp_secret
    finally:
        db.close()

    totp = pyotp.TOTP(secret)

    # Generate code for a time window far in the past (5 minutes ago = 10 time windows)
    # valid_window=1 only accepts current window ±1, so this should fail
    old_time = datetime.utcnow().timestamp() - 300  # 5 minutes ago
    old_code = totp.at(int(old_time / 30))

    # Verify old code is rejected
    resp = client.post("/2fa/verify", json={"username": username, "code": old_code})
    assert resp.status_code == 401
    assert "Invalid TOTP code" in resp.json()["detail"]


def test_verify_without_enrollment(client):
    """Test that TOTP verification returns 400 error when user hasn't enrolled in 2FA."""
    username = "no_enrollment_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Try to verify without enrolling first
    resp = client.post("/2fa/verify", json={"username": username, "code": "123456"})
    assert resp.status_code == 400
    assert "2FA not enabled for user" in resp.json()["detail"]


def test_verify_with_empty_code(client):
    """Test that TOTP verification validates code format and rejects empty codes."""
    username = "empty_code_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Enroll in 2FA
    enroll = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert enroll.status_code == 200

    # Try to verify with empty code
    resp = client.post("/2fa/verify", json={"username": username, "code": ""})
    assert resp.status_code == 400
    assert "TOTP code must be 6 digits" in resp.json()["detail"]


def test_verify_with_non_numeric_code(client):
    """Test that TOTP verification validates code format and rejects non-numeric codes."""
    username = "non_numeric_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Enroll in 2FA
    enroll = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert enroll.status_code == 200

    # Try to verify with non-numeric code
    resp = client.post("/2fa/verify", json={"username": username, "code": "abc123"})
    assert resp.status_code == 400
    assert "TOTP code must be 6 digits" in resp.json()["detail"]

    # Try to verify with code that's not 6 digits
    resp = client.post("/2fa/verify", json={"username": username, "code": "12345"})
    assert resp.status_code == 400
    assert "TOTP code must be 6 digits" in resp.json()["detail"]

    # Try to verify with code that's too long
    resp = client.post("/2fa/verify", json={"username": username, "code": "1234567"})
    assert resp.status_code == 400
    assert "TOTP code must be 6 digits" in resp.json()["detail"]


def test_disable_2fa_clears_secret(client):
    """Test that disabling 2FA clears the TOTP secret and sets is_2fa_enabled to False."""
    username = "disable_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Enroll in 2FA
    enroll = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert enroll.status_code == 200

    # Verify 2FA is enabled and secret is stored
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user.is_2fa_enabled is True
        assert user.totp_secret is not None
    finally:
        db.close()

    # Disable 2FA
    resp = client.post("/2fa/disable", json={"username": username, "password": password})
    assert resp.status_code == 200
    assert "2FA has been disabled successfully" in resp.json()["message"]

    # Verify 2FA is disabled and secret is cleared
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user.is_2fa_enabled is False
        assert user.totp_secret is None
    finally:
        db.close()


def test_disable_2fa_requires_password(client):
    """Test that disabling 2FA requires valid password authentication."""
    username = "disable_password_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Enroll in 2FA
    enroll = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert enroll.status_code == 200

    # Try to disable with wrong password
    resp = client.post("/2fa/disable", json={"username": username, "password": "WrongPassword123!"})
    assert resp.status_code == 401
    assert "Invalid credentials" in resp.json()["detail"]

    # Verify 2FA is still enabled
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user.is_2fa_enabled is True
        assert user.totp_secret is not None
    finally:
        db.close()

    # Disable with correct password
    resp = client.post("/2fa/disable", json={"username": username, "password": password})
    assert resp.status_code == 200

    # Verify 2FA is now disabled
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user.is_2fa_enabled is False
    finally:
        db.close()


def test_login_after_disable(client):
    """Test that login works normally after disabling 2FA (no TOTP required)."""
    username = "login_after_disable_user"
    password = "Secret123!"
    ensure_user(username, password)

    # Enroll in 2FA
    enroll = client.post("/2fa/enroll", json={"username": username, "password": password})
    assert enroll.status_code == 200

    # Login should require 2FA
    resp = client.post("/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("requires2fa") is True
    assert "access_token" not in data

    # Disable 2FA
    resp = client.post("/2fa/disable", json={"username": username, "password": password})
    assert resp.status_code == 200

    # Login should now work without 2FA and return JWT directly
    resp = client.post("/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data.get("requires2fa") is None or data.get("requires2fa") is False
