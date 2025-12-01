"""
Event ingestion API endpoint for receiving authentication events from Auth Service
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import uuid

from schemas import AuthEventIn, EventIngestResponse, ErrorResponse
from models import MCPAuthEvent
from db import get_db
from fraud_detector import FraudDetector
from config import settings

logger = logging.getLogger(__name__)

# Initialize fraud detector with configured threshold and BAML settings
fraud_detector = FraudDetector(
    fraud_threshold=settings.FRAUD_THRESHOLD,
    baml_enabled=settings.BAML_ENABLED,
    baml_timeout_ms=settings.BAML_TIMEOUT_MS
)

router = APIRouter(prefix="/mcp", tags=["Event Ingestion"])


@router.post(
    "/ingest",
    response_model=EventIngestResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Event accepted and queued for processing",
            "model": EventIngestResponse
        },
        422: {
            "description": "Invalid event structure",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    },
    summary="Ingest authentication event",
    description="""
    Receive and store authentication events from the Auth Service.

    This endpoint:
    1. Validates the event structure against the defined schema
    2. Persists the event to the MCP database
    3. Returns immediately with event ID (fraud analysis happens asynchronously)

    Supported event types:
    - login_success
    - login_failure
    - 2fa_success
    - 2fa_failure
    - password_reset
    - password_reset_request
    - account_locked
    - account_unlocked
    """
)
async def ingest_event(
    event: AuthEventIn,
    db: Session = Depends(get_db)
) -> EventIngestResponse:
    """
    Ingest an authentication event from the Auth Service.

    Args:
        event: Authentication event data
        db: Database session

    Returns:
        EventIngestResponse with event ID and status

    Raises:
        HTTPException: 422 for validation errors, 500 for server errors
    """
    try:
        # Parse timestamp to datetime object
        try:
            event_timestamp = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid timestamp format: {event.timestamp}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid timestamp format: {str(e)}"
            ) from e

        # Generate unique event ID
        event_id = str(uuid.uuid4())

        # Create MCPAuthEvent instance
        mcp_event = MCPAuthEvent(
            id=event_id,
            user_id=event.user_id,
            username=event.username,
            event_type=event.event_type,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            timestamp=event_timestamp,
            event_metadata=event.metadata,
            # Fraud detection fields will be populated later by fraud detection engine
            risk_score=None,
            fraud_reason=None,
            analyzed_at=None
        )

        # Persist event to database
        db.add(mcp_event)
        db.commit()
        db.refresh(mcp_event)

        logger.info(
            f"Event ingested successfully: id={event_id}, user_id={event.user_id}, "
            f"event_type={event.event_type}"
        )

        # Perform fraud detection analysis
        try:
            assessment = fraud_detector.analyze_event(event, db)

            # Update event with fraud detection results
            mcp_event.risk_score = assessment.risk_score
            mcp_event.fraud_reason = assessment.reason
            mcp_event.analyzed_at = datetime.utcnow()

            db.commit()

            logger.info(
                f"Fraud analysis completed for event {event_id}: "
                f"risk_score={assessment.risk_score:.2f}"
            )

            # Log high-risk events for future AI analysis
            if assessment.risk_score >= settings.FRAUD_THRESHOLD:
                logger.warning(
                    f"⚠️ HIGH RISK EVENT DETECTED: event_id={event_id}, "
                    f"user_id={event.user_id}, username={event.username}, "
                    f"risk_score={assessment.risk_score:.2f}, reason={assessment.reason}"
                )
                logger.warning(
                    f"📧 EMAIL NOTIFICATION TRIGGER: Would send email to user {event.username} "
                    f"about suspicious activity. Risk: {assessment.risk_score:.2f} - {assessment.reason}"
                )

        except Exception as e:
            # Log fraud detection errors but don't fail the ingestion
            logger.error(f"Fraud detection failed for event {event_id}: {e}", exc_info=True)
            # Continue without fraud analysis results

        return EventIngestResponse(
            message="Event accepted for processing",
            event_id=event_id,
            status="accepted"
        )

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise

    except Exception as e:
        # Log unexpected errors and return 500
        logger.error(f"Failed to ingest event: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process event: {str(e)}"
        ) from e
