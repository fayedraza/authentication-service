"""
Fraud assessment query API endpoint for retrieving fraud detection results
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime
from typing import Optional
import logging

from schemas import (
    FraudAssessmentListResponse,
    FraudAssessmentOut,
    FraudStatistics,
    AuthEventOut,
    ErrorResponse
)
from models import MCPAuthEvent
from db import get_db
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["Fraud Assessment"])


@router.get(
    "/fraud-assessments",
    response_model=FraudAssessmentListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "List of fraud assessments with statistics",
            "model": FraudAssessmentListResponse
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
    summary="Query fraud assessments",
    description="""
    Retrieve fraud detection results with filtering, sorting, and statistics.

    This endpoint supports:
    - Filtering by user_id, risk_score range, and timestamp
    - Sorting by risk_score with configurable order (ascending/descending)
    - Pagination with limit and offset parameters
    - Aggregated statistics (total events, risk level counts, average score)

    All filters are optional and can be combined.
    Only returns events that have been analyzed (risk_score is not null).
    """
)
async def get_fraud_assessments(
    user_id: Optional[int] = Query(None, gt=0, description="Filter by user ID"),
    min_risk_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum risk score (inclusive)"),
    max_risk_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum risk score (inclusive)"),
    start_date: Optional[str] = Query(None, description="Filter events after this timestamp (ISO 8601 format)"),
    end_date: Optional[str] = Query(None, description="Filter events before this timestamp (ISO 8601 format)"),
    sort_by: str = Query("risk_score", description="Field to sort by (currently only 'risk_score' supported)"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order: 'asc' or 'desc'"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of assessments to return"),
    offset: int = Query(0, ge=0, description="Number of assessments to skip for pagination"),
    db: Session = Depends(get_db)
) -> FraudAssessmentListResponse:
    """
    Query fraud assessments with filtering, sorting, and statistics.

    Args:
        user_id: Optional filter by user ID
        min_risk_score: Optional minimum risk score filter
        max_risk_score: Optional maximum risk score filter
        start_date: Optional filter for events after this timestamp
        end_date: Optional filter for events before this timestamp
        sort_by: Field to sort by (default: risk_score)
        order: Sort order - 'asc' or 'desc' (default: desc)
        limit: Maximum number of assessments to return (default: 100, max: 1000)
        offset: Number of assessments to skip (default: 0)
        db: Database session

    Returns:
        FraudAssessmentListResponse with assessments, statistics, total count, limit, and offset

    Raises:
        HTTPException: 400 for invalid parameters, 500 for server errors
    """
    try:
        # Validate risk score range
        if min_risk_score is not None and max_risk_score is not None:
            if min_risk_score > max_risk_score:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="min_risk_score cannot be greater than max_risk_score"
                )

        # Build query filters - only include analyzed events
        filters = [MCPAuthEvent.risk_score.isnot(None)]

        # Filter by user_id
        if user_id is not None:
            filters.append(MCPAuthEvent.user_id == user_id)

        # Filter by min_risk_score
        if min_risk_score is not None:
            filters.append(MCPAuthEvent.risk_score >= min_risk_score)

        # Filter by max_risk_score
        if max_risk_score is not None:
            filters.append(MCPAuthEvent.risk_score <= max_risk_score)

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
        query = db.query(MCPAuthEvent).filter(and_(*filters))

        # Calculate statistics before pagination
        statistics = _calculate_statistics(query, db)

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        if sort_by == "risk_score":
            if order == "desc":
                query = query.order_by(MCPAuthEvent.risk_score.desc())
            else:
                query = query.order_by(MCPAuthEvent.risk_score.asc())
        else:
            # Default to risk_score desc if invalid sort_by
            query = query.order_by(MCPAuthEvent.risk_score.desc())

        # Apply pagination
        events = query.limit(limit).offset(offset).all()

        # Convert to response schema
        assessment_list = []
        for event in events:
            # Create AuthEventOut
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

            # Create FraudAssessmentOut
            assessment = FraudAssessmentOut(
                event=event_out,
                risk_score=event.risk_score,
                email_notification=event.risk_score > settings.FRAUD_THRESHOLD if event.risk_score else False,
                reason=event.fraud_reason or "No analysis reason provided",
                analyzed_at=event.analyzed_at.isoformat() + 'Z' if event.analyzed_at else None
            )
            assessment_list.append(assessment)

        logger.info(
            f"Fraud assessments query successful: total={total}, returned={len(assessment_list)}, "
            f"filters=(user_id={user_id}, min_risk={min_risk_score}, max_risk={max_risk_score}, "
            f"start_date={start_date}, end_date={end_date}), sort={sort_by} {order}"
        )

        return FraudAssessmentListResponse(
            assessments=assessment_list,
            statistics=statistics,
            total=total,
            limit=limit,
            offset=offset
        )

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise

    except Exception as e:
        # Log unexpected errors and return 500
        logger.error(f"Failed to query fraud assessments: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query fraud assessments: {str(e)}"
        ) from e


def _calculate_statistics(query, _db: Session) -> FraudStatistics:
    """
    Calculate aggregated fraud statistics for the filtered query.

    Args:
        query: SQLAlchemy query with filters applied
        _db: Database session (unused, kept for future extensibility)

    Returns:
        FraudStatistics with counts and average score
    """
    # Get all risk scores for the filtered events
    risk_scores = [event.risk_score for event in query.all() if event.risk_score is not None]

    if not risk_scores:
        # No events found, return zero statistics
        return FraudStatistics(
            total_events=0,
            high_risk_events=0,
            medium_risk_events=0,
            low_risk_events=0,
            average_risk_score=0.0
        )

    # Calculate counts by risk level
    high_risk_count = sum(1 for score in risk_scores if score > 0.7)
    medium_risk_count = sum(1 for score in risk_scores if 0.4 < score <= 0.7)
    low_risk_count = sum(1 for score in risk_scores if score <= 0.4)

    # Calculate average risk score
    average_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0

    return FraudStatistics(
        total_events=len(risk_scores),
        high_risk_events=high_risk_count,
        medium_risk_events=medium_risk_count,
        low_risk_events=low_risk_count,
        average_risk_score=round(average_score, 4)
    )
