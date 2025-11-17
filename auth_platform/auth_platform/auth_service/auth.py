from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from sqlalchemy.orm import Session

SECRET_KEY = "change-this-secret-in-prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Use pbkdf2_sha256 to avoid external bcrypt backend issues in some environments
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(username: str):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def check_rate_limit(user_id: int, db: Session) -> tuple[bool, int]:
    """
    Check if user has exceeded TOTP verification rate limit.

    Args:
        user_id: The user's ID
        db: Database session

    Returns:
        Tuple of (is_rate_limited, minutes_until_reset)
        - is_rate_limited: True if user has exceeded 5 failed attempts in 15 minutes
        - minutes_until_reset: Minutes until rate limit resets (0 if not limited)
    """
    from .models import TOTPAttempt

    # Calculate time window (15 minutes ago)
    time_window = datetime.utcnow() - timedelta(minutes=15)

    # Query failed attempts within the time window
    failed_attempts = db.query(TOTPAttempt).filter(
        TOTPAttempt.user_id == user_id,
        TOTPAttempt.attempted_at > time_window,
        TOTPAttempt.success is False
    ).order_by(TOTPAttempt.attempted_at.asc()).all()

    # Check if rate limit exceeded
    if len(failed_attempts) >= 5:
        # Calculate minutes until reset (from first failed attempt)
        first_attempt_time = failed_attempts[0].attempted_at
        reset_time = first_attempt_time + timedelta(minutes=15)
        minutes_until_reset = max(0, int((reset_time - datetime.utcnow()).total_seconds() / 60) + 1)

        # Log rate limit event
        print(f"[2FA] Rate limit exceeded: user_id={user_id}, failed_attempts={len(failed_attempts)}, minutes_until_reset={minutes_until_reset}, timestamp={datetime.utcnow().isoformat()}")

        return True, minutes_until_reset

    return False, 0

def record_totp_attempt(user_id: int, success: bool, db: Session) -> None:
    """
    Record a TOTP verification attempt in the database.

    Args:
        user_id: The user's ID
        success: Whether the verification was successful
        db: Database session
    """
    from .models import TOTPAttempt

    attempt = TOTPAttempt(
        user_id=user_id,
        success=success,
        attempted_at=datetime.utcnow()
    )
    db.add(attempt)
    db.commit()

    # Log the attempt
    status = "successful" if success else "failed"
    print(f"[2FA] TOTP verification attempt: user_id={user_id}, status={status}, timestamp={datetime.utcnow().isoformat()}")
