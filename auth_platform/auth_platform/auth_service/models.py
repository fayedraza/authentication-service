from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Enum, Index, JSON
from datetime import datetime
from .db import Base
from sqlalchemy.orm import relationship
import uuid

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    tier = Column(String)
    # Two-Factor Auth (TOTP)
    is_2fa_enabled = Column(Boolean, default=False, nullable=False)
    totp_secret = Column(String, nullable=True)

    # relationships (optional usage)
    tickets = relationship("Ticket", back_populates="owner", cascade="all, delete-orphan")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, default="open", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="tickets")


class TOTPAttempt(Base):
    __tablename__ = "totp_attempts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    attempted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    success = Column(Boolean, nullable=False)


class AuthEvent(Base):
    __tablename__ = "auth_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    username = Column(String, nullable=False)
    event_type = Column(
        Enum("login_success", "login_failure", "2fa_success", "2fa_failure", "password_reset",
             name="auth_event_type"),
        nullable=False
    )
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    event_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index('ix_auth_events_user_id', 'user_id'),
        Index('ix_auth_events_timestamp', 'timestamp'),
        Index('ix_auth_events_event_type', 'event_type'),
        Index('ix_auth_events_user_id_timestamp', 'user_id', 'timestamp'),
    )

    def to_dict(self) -> dict:
        """
        Serialize AuthEvent to dictionary for API responses and MCP consumption.

        Returns:
            Dictionary with all event fields, UUIDs as strings,
            datetimes in ISO 8601 format
        """
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "username": self.username,
            "event_type": self.event_type,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.event_metadata or {}
        }
