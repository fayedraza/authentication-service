"""
Pydantic schemas for MCP Server API request/response validation
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class AuthEventIn(BaseModel):
    """
    Schema for incoming authentication events from Auth Service.

    Validates event structure before persistence and fraud analysis.
    """
    user_id: int = Field(..., gt=0, description="User ID from Auth Service")
    username: str = Field(..., min_length=1, max_length=255, description="Username")
    event_type: str = Field(
        ...,
        description="Type of authentication event",
        pattern="^(login_success|login_failure|2fa_success|2fa_failure|password_reset|password_reset_request|account_locked|account_unlocked)$"
    )
    ip_address: Optional[str] = Field(None, max_length=45, description="Client IP address (IPv4 or IPv6)")
    user_agent: Optional[str] = Field(None, max_length=500, description="Client user agent string")
    timestamp: str = Field(..., description="Event timestamp in ISO 8601 format")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional event metadata")

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate that timestamp is in valid ISO 8601 format"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except (ValueError, AttributeError) as exc:
            raise ValueError('timestamp must be in ISO 8601 format (e.g., 2024-01-01T12:00:00Z)') from exc

    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Ensure metadata is a dictionary"""
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError('metadata must be a dictionary')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": 123,
                    "username": "john.doe",
                    "event_type": "login_success",
                    "ip_address": "192.168.1.100",
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "metadata": {"session_id": "abc123", "device": "desktop"}
                }
            ]
        }
    }


class AuthEventOut(BaseModel):
    """
    Schema for authentication event responses.

    Includes fraud detection results if analysis has been performed.
    """
    id: str = Field(..., description="Unique event ID")
    user_id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    event_type: str = Field(..., description="Event type")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    timestamp: str = Field(..., description="Event timestamp in ISO 8601 format")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Fraud risk score (0-1)")
    fraud_reason: Optional[str] = Field(None, description="Explanation of fraud assessment")
    analyzed_at: Optional[str] = Field(None, description="Timestamp when fraud analysis was performed")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_id": 123,
                    "username": "john.doe",
                    "event_type": "login_success",
                    "ip_address": "192.168.1.100",
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "metadata": {"session_id": "abc123"},
                    "risk_score": 0.2,
                    "fraud_reason": "Normal login pattern",
                    "analyzed_at": "2024-01-15T10:30:01Z"
                }
            ]
        }
    }


class EventIngestResponse(BaseModel):
    """
    Response schema for successful event ingestion.
    """
    message: str = Field(..., description="Success message")
    event_id: str = Field(..., description="ID of the ingested event")
    status: str = Field(default="accepted", description="Processing status")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Event accepted for processing",
                    "event_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "accepted"
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """
    Schema for error responses.
    """
    detail: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Type of error")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": "Invalid event structure",
                    "error_type": "validation_error"
                }
            ]
        }
    }


class EventListResponse(BaseModel):
    """
    Response schema for event query endpoint with pagination.
    """
    events: List[AuthEventOut] = Field(..., description="List of authentication events")
    total: int = Field(..., ge=0, description="Total number of events matching filters")
    limit: int = Field(..., ge=1, description="Maximum number of events returned")
    offset: int = Field(..., ge=0, description="Number of events skipped")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "events": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "user_id": 123,
                            "username": "john.doe",
                            "event_type": "login_success",
                            "ip_address": "192.168.1.100",
                            "user_agent": "Mozilla/5.0",
                            "timestamp": "2024-01-15T10:30:00Z",
                            "metadata": {},
                            "risk_score": 0.2,
                            "fraud_reason": "Normal login pattern",
                            "analyzed_at": "2024-01-15T10:30:01Z"
                        }
                    ],
                    "total": 150,
                    "limit": 100,
                    "offset": 0
                }
            ]
        }
    }


class FraudStatistics(BaseModel):
    """
    Aggregated statistics for fraud assessments.
    """
    total_events: int = Field(..., ge=0, description="Total number of events analyzed")
    high_risk_events: int = Field(..., ge=0, description="Number of high-risk events (score > 0.7)")
    medium_risk_events: int = Field(..., ge=0, description="Number of medium-risk events (0.4 < score <= 0.7)")
    low_risk_events: int = Field(..., ge=0, description="Number of low-risk events (score <= 0.4)")
    average_risk_score: float = Field(..., ge=0.0, le=1.0, description="Average risk score across all events")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total_events": 1000,
                    "high_risk_events": 15,
                    "medium_risk_events": 85,
                    "low_risk_events": 900,
                    "average_risk_score": 0.18
                }
            ]
        }
    }


class FraudAssessmentOut(BaseModel):
    """
    Schema for fraud assessment response including event and analysis results.
    """
    event: AuthEventOut = Field(..., description="The authentication event that was analyzed")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Fraud risk score (0-1)")
    email_notification: bool = Field(..., description="Whether an email notification should be sent to the user")
    reason: str = Field(..., description="Explanation of the fraud assessment")
    analyzed_at: str = Field(..., description="Timestamp when fraud analysis was performed")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "event": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "user_id": 123,
                        "username": "john.doe",
                        "event_type": "login_failure",
                        "ip_address": "192.168.1.100",
                        "user_agent": "Mozilla/5.0",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "metadata": {},
                        "risk_score": 0.8,
                        "fraud_reason": "Multiple failed login attempts detected",
                        "analyzed_at": "2024-01-15T10:30:01Z"
                    },
                    "risk_score": 0.8,
                    "email_notification": True,
                    "reason": "Multiple failed login attempts detected",
                    "analyzed_at": "2024-01-15T10:30:01Z"
                }
            ]
        }
    }


class FraudAssessmentListResponse(BaseModel):
    """
    Response schema for fraud assessment query endpoint with statistics and pagination.
    """
    assessments: List[FraudAssessmentOut] = Field(..., description="List of fraud assessments")
    statistics: FraudStatistics = Field(..., description="Aggregated fraud statistics")
    total: int = Field(..., ge=0, description="Total number of assessments matching filters")
    limit: int = Field(..., ge=1, description="Maximum number of assessments returned")
    offset: int = Field(..., ge=0, description="Number of assessments skipped")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "assessments": [
                        {
                            "event": {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "user_id": 123,
                                "username": "john.doe",
                                "event_type": "login_failure",
                                "ip_address": "192.168.1.100",
                                "user_agent": "Mozilla/5.0",
                                "timestamp": "2024-01-15T10:30:00Z",
                                "metadata": {},
                                "risk_score": 0.8,
                                "fraud_reason": "Multiple failed login attempts",
                                "analyzed_at": "2024-01-15T10:30:01Z"
                            },
                            "risk_score": 0.8,
                            "email_notification": True,
                            "reason": "Multiple failed login attempts",
                            "analyzed_at": "2024-01-15T10:30:01Z"
                        }
                    ],
                    "statistics": {
                        "total_events": 1000,
                        "high_risk_events": 15,
                        "medium_risk_events": 85,
                        "low_risk_events": 900,
                        "average_risk_score": 0.18
                    },
                    "total": 1000,
                    "limit": 100,
                    "offset": 0
                }
            ]
        }
    }


class AlertOut(BaseModel):
    """
    Schema for alert responses.

    Represents a security alert generated for high-risk authentication events.
    """
    id: str = Field(..., description="Unique alert ID")
    user_id: int = Field(..., description="User ID associated with the alert")
    username: str = Field(..., description="Username associated with the alert")
    event_ids: List[str] = Field(..., description="List of related event IDs")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Maximum risk score from related events")
    reason: str = Field(..., description="Explanation of why the alert was generated")
    status: str = Field(..., description="Alert status: open, reviewed, or resolved")
    created_at: str = Field(..., description="Timestamp when alert was created")
    updated_at: str = Field(..., description="Timestamp when alert was last updated")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "alert-550e8400-e29b-41d4-a716-446655440000",
                    "user_id": 123,
                    "username": "john.doe",
                    "event_ids": ["550e8400-e29b-41d4-a716-446655440000", "660e8400-e29b-41d4-a716-446655440001"],
                    "risk_score": 0.85,
                    "reason": "Multiple failed login attempts detected from different IP addresses",
                    "status": "open",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                }
            ]
        }
    }


class AlertListResponse(BaseModel):
    """
    Response schema for alert query endpoint with pagination.
    """
    alerts: List[AlertOut] = Field(..., description="List of alerts")
    total: int = Field(..., ge=0, description="Total number of alerts matching filters")
    limit: int = Field(..., ge=1, description="Maximum number of alerts returned")
    offset: int = Field(..., ge=0, description="Number of alerts skipped")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "alerts": [
                        {
                            "id": "alert-550e8400-e29b-41d4-a716-446655440000",
                            "user_id": 123,
                            "username": "john.doe",
                            "event_ids": ["550e8400-e29b-41d4-a716-446655440000"],
                            "risk_score": 0.85,
                            "reason": "Multiple failed login attempts",
                            "status": "open",
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z"
                        }
                    ],
                    "total": 25,
                    "limit": 100,
                    "offset": 0
                }
            ]
        }
    }


class AlertStatusUpdate(BaseModel):
    """
    Schema for updating alert status.
    """
    status: str = Field(
        ...,
        description="New alert status",
        pattern="^(open|reviewed|resolved)$"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "reviewed"
                }
            ]
        }
    }


class AlertCreateResponse(BaseModel):
    """
    Response schema for alert creation.
    """
    message: str = Field(..., description="Success message")
    alert_id: str = Field(..., description="ID of the created alert")
    consolidated: bool = Field(..., description="Whether this alert was consolidated with an existing one")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Alert created successfully",
                    "alert_id": "alert-550e8400-e29b-41d4-a716-446655440000",
                    "consolidated": False
                }
            ]
        }
    }
