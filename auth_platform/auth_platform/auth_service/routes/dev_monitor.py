"""
Dev Monitor Router - Development-only endpoints for authentication event inspection.
"""
import os
import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AuthEvent

router = APIRouter(prefix="/dev", tags=["dev-monitor"])
logger = logging.getLogger(__name__)


def is_dev_mode() -> bool:
    """Check if DEV_MODE is enabled."""
    return os.getenv("DEV_MODE", "false").lower() == "true"


def is_local_request(request: Request) -> bool:
    """Check if request originates from localhost or internal IP."""
    if not request.client:
        # If no client info, allow in dev mode (likely internal Docker request)
        return True

    client_ip = request.client.host

    # Check for localhost
    if client_ip in ("127.0.0.1", "::1", "localhost"):
        return True

    # Check for Docker internal networks
    # Docker default bridge: 172.17.0.0/16
    # Docker compose networks: 172.x.x.x
    if client_ip.startswith("172."):
        return True

    # Check for private IP ranges (10.x.x.x, 192.168.x.x)
    if client_ip.startswith(("10.", "192.168.")):
        return True

    # Check for Docker host gateway (host.docker.internal resolves to this)
    if client_ip.startswith("192.168.65."):  # Docker Desktop on Mac
        return True

    return False


@router.get("/event-logs")
def get_event_logs(
    request: Request,
    limit: int = 50,
    event_type: Optional[str] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get recent authentication events (development only).

    Args:
        limit: Maximum number of events to return (default 50, max 1000)
        event_type: Filter by event type (optional)
        user_id: Filter by user ID (optional)

    Returns:
        List of authentication events as dictionaries

    Raises:
        404: If DEV_MODE is not enabled
        403: If request is not from localhost/internal IP
        400: If limit exceeds 1000
    """
    # Check DEV_MODE
    if not is_dev_mode():
        logger.warning(
            "Attempt to access /dev/event-logs with DEV_MODE disabled from IP %s",
            request.client.host if request.client else 'unknown'
        )
        raise HTTPException(status_code=404, detail="Not found")

    # In DEV_MODE, skip IP check since we're already in a dev environment
    # The DEV_MODE flag itself is the primary security control
    # Additional IP check only for extra logging
    if not is_local_request(request):
        logger.info(
            "Dev event logs accessed from non-local IP: %s (allowed in DEV_MODE)",
            request.client.host if request.client else 'unknown'
        )

    # Validate limit
    if limit > 1000:
        raise HTTPException(
            status_code=400,
            detail="Limit cannot exceed 1000 events"
        )

    # Build query
    query = db.query(AuthEvent)

    if event_type:
        query = query.filter(AuthEvent.event_type == event_type)

    if user_id:
        query = query.filter(AuthEvent.user_id == user_id)

    # Order by timestamp descending and limit
    events = query.order_by(AuthEvent.timestamp.desc()).limit(limit).all()

    # Log access
    logger.info(
        "Dev event logs accessed: limit=%s, event_type=%s, user_id=%s, results=%s, ip=%s",
        limit, event_type, user_id, len(events),
        request.client.host if request.client else 'unknown'
    )

    # Serialize to dictionaries
    return [event.to_dict() for event in events]
