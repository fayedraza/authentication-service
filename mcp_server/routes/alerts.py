"""
Alert management endpoints for MCP Server.

Provides endpoints for creating, querying, and updating security alerts
generated from high-risk authentication events.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

from db import get_db
from models import MCPAlert, MCPAuthEvent
from schemas import (
    AlertOut,
    AlertListResponse,
    AlertStatusUpdate,
    AlertCreateResponse
)
from config import settings


router = APIRouter(prefix="/mcp/alerts", tags=["alerts"])


def create_alert_for_event(
    event_id: str,
    user_id: int,
    username: str,
    risk_score: float,
    reason: str,
    db: Session
) -> AlertCreateResponse:
    """
    Helper function to create an alert for a high-risk event.

    This is called by the event ingestion endpoint when fraud detection
    identifies a high-risk event. It wraps the create_alert function
    and returns an AlertCreateResponse.

    Args:
        event_id: ID of the high-risk event
        user_id: User ID associated with the event
        username: Username associated with the event
        risk_score: Risk score of the event
        reason: Explanation of why the alert was generated
        db: Database session

    Returns:
        AlertCreateResponse with alert_id and consolidation status
    """
    alert_id, consolidated = create_alert(
        db=db,
        user_id=user_id,
        username=username,
        event_id=event_id,
        risk_score=risk_score,
        reason=reason
    )

    return AlertCreateResponse(
        message="Alert created successfully" if not consolidated else "Alert consolidated with existing alert",
        alert_id=alert_id,
        consolidated=consolidated
    )


def create_alert(
    db: Session,
    user_id: int,
    username: str,
    event_id: str,
    risk_score: float,
    reason: str
) -> tuple[str, bool]:
    """
    Create a new alert or consolidate with existing alert.

    Implements alert consolidation: if an open alert exists for the same user
    within the consolidation window (5 minutes), add the event to that alert
    instead of creating a new one.

    Args:
        db: Database session
        user_id: User ID associated with the alert
        username: Username associated with the alert
        event_id: ID of the high-risk event
        risk_score: Risk score of the event
        reason: Explanation of why the alert was generated

    Returns:
        Tuple of (alert_id, consolidated) where consolidated is True if
        the event was added to an existing alert
    """
    # Check for existing open alerts for this user within consolidation window
    consolidation_window = datetime.utcnow() - timedelta(
        minutes=settings.ALERT_CONSOLIDATION_WINDOW_MINUTES
    )

    existing_alert = db.query(MCPAlert).filter(
        and_(
            MCPAlert.user_id == user_id,
            MCPAlert.status == "open",
            MCPAlert.created_at >= consolidation_window
        )
    ).first()

    if existing_alert:
        # Consolidate: add event to existing alert
        event_ids = existing_alert.event_ids
        if not isinstance(event_ids, list):
            event_ids = []

        # Only add if not already in the list and under max limit
        if event_id not in event_ids and len(event_ids) < settings.MAX_EVENTS_PER_ALERT:
            event_ids.append(event_id)
            existing_alert.event_ids = event_ids

            # Update risk score to maximum
            existing_alert.risk_score = max(existing_alert.risk_score, risk_score)

            # Append reason if different
            if reason not in existing_alert.reason:
                existing_alert.reason = f"{existing_alert.reason}; {reason}"

            existing_alert.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_alert)

            return existing_alert.id, True

    # Create new alert
    new_alert = MCPAlert(
        id=str(uuid.uuid4()),
        user_id=user_id,
        username=username,
        event_ids=[event_id],
        risk_score=risk_score,
        reason=reason,
        status="open",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)

    return new_alert.id, False


@router.post("", response_model=AlertCreateResponse, status_code=201)
async def create_alert_endpoint(
    user_id: int = Query(..., gt=0, description="User ID"),
    username: str = Query(..., min_length=1, description="Username"),
    event_id: str = Query(..., description="Event ID that triggered the alert"),
    risk_score: float = Query(..., ge=0.0, le=1.0, description="Risk score"),
    reason: str = Query(..., min_length=1, description="Reason for alert"),
    db: Session = Depends(get_db)
):
    """
    Create a new alert for a high-risk event.

    This endpoint is typically called internally by the fraud detection engine
    when an event exceeds the risk threshold. It implements alert consolidation
    to prevent alert fatigue.

    **Requirements**: 4.1, 4.2, 4.5
    """
    try:
        alert_id, consolidated = create_alert(
            db=db,
            user_id=user_id,
            username=username,
            event_id=event_id,
            risk_score=risk_score,
            reason=reason
        )

        return AlertCreateResponse(
            message="Alert created successfully" if not consolidated else "Alert consolidated with existing alert",
            alert_id=alert_id,
            consolidated=consolidated
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}") from e


@router.get("", response_model=AlertListResponse)
async def get_alerts(
    status: Optional[str] = Query(
        None,
        pattern="^(open|reviewed|resolved)$",
        description="Filter by alert status"
    ),
    min_risk_score: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Filter by minimum risk score"
    ),
    user_id: Optional[int] = Query(
        None,
        gt=0,
        description="Filter by user ID"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of alerts to return"),
    offset: int = Query(0, ge=0, description="Number of alerts to skip"),
    db: Session = Depends(get_db)
):
    """
    Retrieve alerts with optional filtering.

    Returns a paginated list of alerts matching the specified filters.
    Alerts are sorted by creation date in descending order (newest first).

    **Requirements**: 4.2, 4.3
    """
    try:
        # Build query with filters
        query = db.query(MCPAlert)

        if status:
            query = query.filter(MCPAlert.status == status)

        if min_risk_score is not None:
            query = query.filter(MCPAlert.risk_score >= min_risk_score)

        if user_id:
            query = query.filter(MCPAlert.user_id == user_id)

        # Get total count
        total = query.count()

        # Apply sorting and pagination
        alerts = query.order_by(desc(MCPAlert.created_at)).limit(limit).offset(offset).all()

        # Convert to response schema
        alert_outs = []
        for alert in alerts:
            alert_outs.append(AlertOut(
                id=alert.id,
                user_id=alert.user_id,
                username=alert.username,
                event_ids=alert.event_ids if isinstance(alert.event_ids, list) else [],
                risk_score=alert.risk_score,
                reason=alert.reason,
                status=alert.status,
                created_at=alert.created_at.isoformat() + "Z",
                updated_at=alert.updated_at.isoformat() + "Z"
            ))

        return AlertListResponse(
            alerts=alert_outs,
            total=total,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}") from e


@router.patch("/{alert_id}", response_model=AlertOut)
async def update_alert_status(
    alert_id: str,
    status_update: AlertStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Update the status of an alert.

    Allows security administrators to mark alerts as reviewed or resolved.
    The updated_at timestamp is automatically updated.

    **Requirements**: 4.4
    """
    try:
        # Find the alert
        alert = db.query(MCPAlert).filter(MCPAlert.id == alert_id).first()

        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found")

        # Update status
        alert.status = status_update.status
        alert.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(alert)

        return AlertOut(
            id=alert.id,
            user_id=alert.user_id,
            username=alert.username,
            event_ids=alert.event_ids if isinstance(alert.event_ids, list) else [],
            risk_score=alert.risk_score,
            reason=alert.reason,
            status=alert.status,
            created_at=alert.created_at.isoformat() + "Z",
            updated_at=alert.updated_at.isoformat() + "Z"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update alert: {str(e)}") from e


@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert_by_id(
    alert_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific alert by ID.

    Returns detailed information about a single alert.
    """
    try:
        alert = db.query(MCPAlert).filter(MCPAlert.id == alert_id).first()

        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found")

        return AlertOut(
            id=alert.id,
            user_id=alert.user_id,
            username=alert.username,
            event_ids=alert.event_ids if isinstance(alert.event_ids, list) else [],
            risk_score=alert.risk_score,
            reason=alert.reason,
            status=alert.status,
            created_at=alert.created_at.isoformat() + "Z",
            updated_at=alert.updated_at.isoformat() + "Z"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alert: {str(e)}") from e
