"""
Event query API endpoint for retrieving stored authentication events
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import Optional
import logging

from schemas import EventListResponse, AuthEventOut, ErrorResponse
from models import MCPAuthEvent
from db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["Event Query"])


@router.get(
    "/events",
    response_model=EventListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "List of authentication events",
            "model": EventListResponse
        },
        400: {
            "description": "Invalid query parameters",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    },
    summary="Query authentication events",
    description="""
    Retrieve stored authentication events with filtering and pagination.

    This endpoint supports:
    - Filtering by user_id, event_type, and timestamp range
    - Pagination with limit and offset parameters
    - Returns total count of matching events for pagination

    All filters are optional and can be combined.
    """
)
async def get_events(
    user_id: Optional[int] = Query(None, gt=0, description="Filter by user ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type (e.g., login_success, login_failure)"),
    start_date: Optional[str] = Query(None, description="Filter events after this timestamp (ISO 8601 format)"),
    end_date: Optional[str] = Query(None, description="Filter events before this timestamp (ISO 8601 format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip for pagination"),
    db: Session = Depends(get_db)
) -> EventListResponse:
    """
    Query authentication events with filtering and pagination.

    Args:
        user_id: Optional filter by user ID
        event_type: Optional filter by event type
        start_date: Optional filter for events after this timestamp
        end_date: Optional filter for events before this timestamp
        limit: Maximum number of events to return (default: 100, max: 1000)
        offset: Number of events to skip (default: 0)
        db: Database session

    Returns:
        EventListResponse with events, total count, limit, and offset

    Raises:
        HTTPException: 400 for invalid parameters, 500 for server errors
    """
    try:
        # Build query filters
        filters = []

        # Filter by user_id
        if user_id is not None:
            filters.append(MCPAuthEvent.user_id == user_id)

        # Filter by event_type
        if event_type is not None:
            filters.append(MCPAuthEvent.event_type == event_type)

        # Filter by start_date
        if start_date is not None:
            try:
                start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                filters.append(MCPAuthEvent.timestamp >= start_datetime)
            except (ValueError, AttributeError) as e:
                logger.error(f"Invalid start_date format: {start_date}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid start_date format. Use ISO 8601 format (e.g., 2024-01-15T10:30:00Z): {str(e)}"
                ) from e

        # Filter by end_date
        if end_date is not None:
            try:
                end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                filters.append(MCPAuthEvent.timestamp <= end_datetime)
            except (ValueError, AttributeError) as e:
                logger.error(f"Invalid end_date format: {end_date}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid end_date format. Use ISO 8601 format (e.g., 2024-01-15T10:30:00Z): {str(e)}"
                ) from e

        # Build base query
        query = db.query(MCPAuthEvent)

        # Apply filters
        if filters:
            query = query.filter(and_(*filters))

        # Get total count before pagination
        total = query.count()

        # Apply pagination and ordering (most recent first)
        events = query.order_by(MCPAuthEvent.timestamp.desc()).limit(limit).offset(offset).all()

        # Convert to response schema
        event_list = []
        for event in events:
            event_out = AuthEventOut(
                id=event.id,
                user_id=event.user_id,
                username=event.username,
                event_type=event.event_type,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                timestamp=event.timestamp.isoformat() + 'Z' if event.timestamp else None,
                metadata=event.event_metadata or {},
                risk_score=event.risk_score,
                fraud_reason=event.fraud_reason,
                analyzed_at=event.analyzed_at.isoformat() + 'Z' if event.analyzed_at else None
            )
            event_list.append(event_out)

        logger.info(
            f"Events query successful: total={total}, returned={len(event_list)}, "
            f"filters=(user_id={user_id}, event_type={event_type}, "
            f"start_date={start_date}, end_date={end_date})"
        )

        return EventListResponse(
            events=event_list,
            total=total,
            limit=limit,
            offset=offset
        )

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise

    except Exception as e:
        # Log unexpected errors and return 500
        logger.error(f"Failed to query events: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query events: {str(e)}"
        ) from e
