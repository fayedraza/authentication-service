"""
Event logger utility for authentication events.
"""
from datetime import datetime
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import sys
import logging
import os

from ..models import AuthEvent, User

# Configure file and stdout logging
log_dir = os.getenv("LOG_DIR", "/app/logs")

# Create handlers list
handlers = [logging.StreamHandler(sys.stdout)]

# Try to add file handler, but continue without it if directory creation fails
try:
    os.makedirs(log_dir, exist_ok=True)
    handlers.append(logging.FileHandler(f"{log_dir}/auth_events.log"))
except (OSError, PermissionError) as e:
    # Log to stderr if file logging setup fails
    print(f"WARNING: Could not set up file logging: {e}", file=sys.stderr)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(message)s",
    handlers=handlers
)

logger = logging.getLogger(__name__)


ALLOWED_EVENT_TYPES = {
    "login_success",
    "login_failure",
    "2fa_success",
    "2fa_failure",
    "password_reset"
}


def log_auth_event(
    event_type: str,
    user: User,
    request: Request,
    db: Session,
    metadata: dict = None
) -> None:
    """
    Log an authentication event to the database.

    Args:
        event_type: One of: login_success, login_failure, 2fa_success,
                    2fa_failure, password_reset
        user: User object from database
        request: FastAPI Request object
        db: Database session
        metadata: Optional dictionary of additional context

    Raises:
        ValueError: If event_type is invalid
    """
    # Validate event type
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(
            f"Invalid event_type '{event_type}'. Must be one of: {', '.join(ALLOWED_EVENT_TYPES)}"
        )

    # Extract IP address with X-Forwarded-For fallback
    ip_address = None
    if request.client:
        ip_address = request.client.host

    # Check for X-Forwarded-For header (proxy/load balancer scenarios)
    if not ip_address and request.headers.get("x-forwarded-for"):
        # X-Forwarded-For can contain multiple IPs, take the first one
        ip_address = request.headers.get("x-forwarded-for").split(",")[0].strip()

    # Extract user agent
    user_agent = request.headers.get("user-agent")

    # Create AuthEvent instance
    try:
        auth_event = AuthEvent(
            user_id=user.id,
            username=user.username,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
            event_metadata=metadata or {}
        )

        db.add(auth_event)
        db.commit()

        # Log to file and stdout
        logger.info(
            "AUTH %s user_id=%s username=%s ip=%s timestamp=%s",
            event_type, user.id, user.username, ip_address, datetime.utcnow().isoformat()
        )

    except SQLAlchemyError as e:
        # Log error but don't raise - logging failure should not break auth flow
        print(
            f"WARNING: Failed to log auth event - "
            f"user_id={user.id}, event_type={event_type}, error={str(e)}",
            file=sys.stderr
        )
        db.rollback()
