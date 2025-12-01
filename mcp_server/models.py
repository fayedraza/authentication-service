"""
Database models for MCP Server
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, Index
from datetime import datetime
import uuid

from db import Base


class MCPAuthEvent(Base):
    """
    Stored authentication event in MCP database.

    Represents an authentication event received from the Auth Service,
    including fraud detection analysis results.
    """
    __tablename__ = "mcp_auth_events"

    # Event identification
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String, nullable=False)

    # Event details
    event_type = Column(String, nullable=False, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    event_metadata = Column(JSON, nullable=True, default=dict)

    # Fraud detection results
    risk_score = Column(Float, nullable=True)
    fraud_reason = Column(Text, nullable=True)
    analyzed_at = Column(DateTime, nullable=True)

    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_user_timestamp', 'user_id', 'timestamp'),
        Index('ix_risk_score', 'risk_score'),
        Index('ix_event_type_timestamp', 'event_type', 'timestamp'),
    )

    def __repr__(self):
        return f"<MCPAuthEvent(id={self.id}, user_id={self.user_id}, event_type={self.event_type}, risk_score={self.risk_score})>"


class MCPAlert(Base):
    """
    Security alert for high-risk authentication events.

    Generated when authentication events exceed the fraud detection threshold.
    Multiple related events can be consolidated into a single alert.
    """
    __tablename__ = "mcp_alerts"

    # Alert identification
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String, nullable=False)

    # Alert details
    event_ids = Column(JSON, nullable=False)  # List of related event IDs
    risk_score = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)

    # Alert status and timestamps
    status = Column(String, default="open", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_status_created', 'status', 'created_at'),
        Index('ix_user_status', 'user_id', 'status'),
        Index('ix_risk_score_alert', 'risk_score'),
    )

    def __repr__(self):
        return f"<MCPAlert(id={self.id}, user_id={self.user_id}, status={self.status}, risk_score={self.risk_score})>"
