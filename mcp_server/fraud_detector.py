"""
Fraud detection engine for analyzing authentication events.

Implements rule-based fraud detection with scoring rules for:
- Multiple failed login attempts
- Multiple failed 2FA attempts
- IP address changes
- User agent changes

Also supports AI-powered fraud detection via BAML agent integration.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from models import MCPAuthEvent
from schemas import AuthEventIn
from baml_client import get_baml_client, LoginEvent as BAMLLoginEvent

logger = logging.getLogger(__name__)


class FraudAssessment(BaseModel):
    """
    Result of fraud detection analysis for an authentication event.

    Contains risk score, email notification flag, and explanation of the assessment.
    """
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk score from 0 (no risk) to 1 (high risk)")
    email_notification: bool = Field(..., description="Whether this event should trigger an email notification to the user")
    reason: str = Field(..., description="Explanation of the fraud assessment")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in the assessment")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "risk_score": 0.8,
                    "email_notification": True,
                    "reason": "Multiple failed login attempts (5 in 5 minutes), IP address changed from previous login",
                    "confidence": 1.0
                }
            ]
        }
    }


class FraudDetector:
    """
    Fraud detection engine that analyzes authentication events.

    Implements both rule-based and AI-powered (BAML) detection with
    configurable thresholds and fallback mechanisms.
    """

    def __init__(
        self,
        fraud_threshold: float = 0.7,
        baml_enabled: bool = False,
        baml_timeout_ms: int = 5000
    ):
        """
        Initialize fraud detector.

        Args:
            fraud_threshold: Risk score threshold for triggering email notifications (default: 0.7)
            baml_enabled: Whether to use BAML agent for fraud detection (default: False)
            baml_timeout_ms: Timeout for BAML agent calls in milliseconds (default: 5000)
        """
        self.fraud_threshold = fraud_threshold
        self.baml_enabled = baml_enabled
        self.baml_timeout_ms = baml_timeout_ms

        # Initialize BAML client if enabled
        self.baml_client = None
        if self.baml_enabled:
            self.baml_client = get_baml_client(timeout_ms=baml_timeout_ms)
            if self.baml_client.is_available():
                logger.info(
                    f"FraudDetector initialized with BAML enabled "
                    f"(threshold: {fraud_threshold}, timeout: {baml_timeout_ms}ms)"
                )
            else:
                logger.warning(
                    "FraudDetector: BAML enabled but client not available, "
                    "will use rule-based detection"
                )
        else:
            logger.info(
                f"FraudDetector initialized with rule-based detection "
                f"(threshold: {fraud_threshold})"
            )

    def analyze_event(self, event: AuthEventIn, db: Session) -> FraudAssessment:
        """
        Analyze an authentication event and return fraud assessment.

        Uses BAML agent if enabled and available, otherwise falls back
        to rule-based detection.

        Args:
            event: Authentication event to analyze
            db: Database session for querying historical events

        Returns:
            FraudAssessment with risk score, email_notification flag, and reason
        """
        try:
            # Try BAML analysis if enabled
            if self.baml_enabled and self.baml_client and self.baml_client.is_available():
                logger.debug(f"Attempting BAML analysis for user {event.user_id}")
                assessment = self._baml_analysis(event, db)

                if assessment is not None:
                    logger.info(
                        f"BAML fraud analysis complete for user {event.user_id}: "
                        f"risk_score={assessment.risk_score:.2f}, email_notification={assessment.email_notification}, "
                        f"confidence={assessment.confidence:.2f}"
                    )
                    return assessment

                logger.warning(
                    f"BAML analysis failed for user {event.user_id}, "
                    "falling back to rule-based detection"
                )

            # Fall back to rule-based analysis
            assessment = self._rule_based_analysis(event, db)
            logger.info(
                f"Rule-based fraud analysis complete for user {event.user_id}: "
                f"risk_score={assessment.risk_score:.2f}, email_notification={assessment.email_notification}"
            )
            return assessment

        except Exception as e:
            logger.error(f"Error during fraud analysis: {e}", exc_info=True)
            # Return safe default assessment on error
            return FraudAssessment(
                risk_score=0.0,
                email_notification=False,
                reason="Analysis failed - defaulting to no risk",
                confidence=0.0
            )

    def _baml_analysis(self, event: AuthEventIn, db: Session) -> Optional[FraudAssessment]:
        """
        Perform AI-powered fraud detection using BAML agent.

        Gathers contextual information about recent user activity and
        sends it to the BAML agent for analysis.

        Args:
            event: Authentication event to analyze
            db: Database session

        Returns:
            FraudAssessment if BAML analysis succeeds, None if it fails or times out
        """
        if not self.baml_client or not self.baml_client.is_available():
            logger.debug("BAML client not available")
            return None

        try:
            # Parse event timestamp
            event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
            if event_time.tzinfo is not None:
                event_time = event_time.replace(tzinfo=None)

            # Gather contextual information for BAML agent
            failed_logins = self._count_recent_events(
                db=db,
                user_id=event.user_id,
                event_type="login_failure",
                since=event_time - timedelta(minutes=5),
                before=event_time
            )

            failed_2fa = self._count_recent_events(
                db=db,
                user_id=event.user_id,
                event_type="2fa_failure",
                since=event_time - timedelta(minutes=5),
                before=event_time
            )

            ip_changed = False
            if event.ip_address:
                ip_changed = self._check_ip_change(
                    db=db,
                    user_id=event.user_id,
                    current_ip=event.ip_address,
                    before=event_time
                )

            ua_changed = False
            if event.user_agent:
                ua_changed = self._check_user_agent_change(
                    db=db,
                    user_id=event.user_id,
                    current_ua=event.user_agent,
                    before=event_time
                )

            # Create BAML LoginEvent
            baml_event = BAMLLoginEvent(
                user_id=event.user_id,
                username=event.username,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                timestamp=event.timestamp,
                event_type=event.event_type,
                failed_attempts_5min=failed_logins,
                failed_2fa_attempts_5min=failed_2fa,
                ip_changed=ip_changed,
                user_agent_changed=ua_changed
            )

            # Call BAML agent (synchronous wrapper)
            baml_result = self.baml_client.analyze_fraud_sync(baml_event)

            if baml_result is None:
                logger.warning("BAML analysis returned None")
                return None

            # Convert BAML result to FraudAssessment
            assessment = FraudAssessment(
                risk_score=baml_result.risk_score,
                email_notification=baml_result.alert,  # BAML still uses 'alert' field
                reason=f"[BAML] {baml_result.reason}",
                confidence=baml_result.confidence
            )

            return assessment

        except Exception as e:
            logger.error(f"Error during BAML analysis: {e}", exc_info=True)
            return None

    def _rule_based_analysis(self, event: AuthEventIn, db: Session) -> FraudAssessment:
        """
        Perform rule-based fraud detection analysis.

        Scoring rules:
        - Multiple failed login attempts (3+ in 5 minutes): +0.3
        - Multiple failed 2FA attempts (3+ in 5 minutes): +0.4
        - IP address change from previous login: +0.2
        - User agent change from previous login: +0.1

        Args:
            event: Authentication event to analyze
            db: Database session

        Returns:
            FraudAssessment with calculated risk score and reasoning
        """
        risk_score = 0.0
        reasons = []

        # Parse event timestamp (remove timezone info for comparison with database timestamps)
        event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
        if event_time.tzinfo is not None:
            event_time = event_time.replace(tzinfo=None)

        # Rule 1: Multiple failed login attempts (3+ in 5 minutes)
        # Scales with number of attempts: 3-5 attempts = +0.3, 6-10 = +0.5, 11+ = +0.7
        failed_logins = self._count_recent_events(
            db=db,
            user_id=event.user_id,
            event_type="login_failure",
            since=event_time - timedelta(minutes=5),
            before=event_time
        )
        if failed_logins >= 11:
            risk_score += 0.7
            reasons.append(f"Severe brute force attack detected ({failed_logins} failed logins in 5 minutes)")
        elif failed_logins >= 6:
            risk_score += 0.5
            reasons.append(f"High number of failed login attempts ({failed_logins} in 5 minutes)")
        elif failed_logins >= 3:
            risk_score += 0.3
            reasons.append(f"Multiple failed login attempts ({failed_logins} in 5 minutes)")

        # Rule 2: Multiple failed 2FA attempts (3+ in 5 minutes)
        # Scales with number of attempts: 3-5 attempts = +0.4, 6-10 = +0.6, 11+ = +0.8
        failed_2fa = self._count_recent_events(
            db=db,
            user_id=event.user_id,
            event_type="2fa_failure",
            since=event_time - timedelta(minutes=5),
            before=event_time
        )
        if failed_2fa >= 11:
            risk_score += 0.8
            reasons.append(f"Severe 2FA brute force attack ({failed_2fa} failed attempts in 5 minutes)")
        elif failed_2fa >= 6:
            risk_score += 0.6
            reasons.append(f"High number of failed 2FA attempts ({failed_2fa} in 5 minutes)")
        elif failed_2fa >= 3:
            risk_score += 0.4
            reasons.append(f"Multiple failed 2FA attempts ({failed_2fa} in 5 minutes)")

        # Rule 3: IP address change from previous login
        if event.ip_address:
            ip_changed = self._check_ip_change(
                db=db,
                user_id=event.user_id,
                current_ip=event.ip_address,
                before=event_time
            )
            if ip_changed:
                risk_score += 0.2
                reasons.append("IP address changed from previous login")

        # Rule 4: User agent change from previous login
        if event.user_agent:
            ua_changed = self._check_user_agent_change(
                db=db,
                user_id=event.user_id,
                current_ua=event.user_agent,
                before=event_time
            )
            if ua_changed:
                risk_score += 0.1
                reasons.append("User agent changed from previous login")

        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)

        # Determine if email notification should be sent
        email_notification = risk_score >= self.fraud_threshold

        # Build reason string
        if reasons:
            reason = "; ".join(reasons)
        else:
            reason = "Normal authentication pattern detected"

        return FraudAssessment(
            risk_score=risk_score,
            email_notification=email_notification,
            reason=reason,
            confidence=1.0
        )

    def _count_recent_events(
        self,
        db: Session,
        user_id: int,
        event_type: str,
        since: datetime,
        before: datetime
    ) -> int:
        """
        Count events of a specific type for a user within a time window.

        Args:
            db: Database session
            user_id: User ID to query
            event_type: Type of event to count
            since: Start of time window
            before: End of time window

        Returns:
            Number of matching events
        """
        try:
            count = db.query(MCPAuthEvent).filter(
                MCPAuthEvent.user_id == user_id,
                MCPAuthEvent.event_type == event_type,
                MCPAuthEvent.timestamp >= since,
                MCPAuthEvent.timestamp < before
            ).count()
            return count
        except Exception as e:
            logger.error(f"Error counting recent events: {e}")
            return 0

    def _check_ip_change(
        self,
        db: Session,
        user_id: int,
        current_ip: str,
        before: datetime
    ) -> bool:
        """
        Check if IP address has changed from the most recent successful login.

        Args:
            db: Database session
            user_id: User ID to query
            current_ip: Current IP address
            before: Timestamp to query before

        Returns:
            True if IP has changed, False otherwise
        """
        try:
            # Get most recent successful login before this event
            last_success = db.query(MCPAuthEvent).filter(
                MCPAuthEvent.user_id == user_id,
                MCPAuthEvent.event_type == "login_success",
                MCPAuthEvent.timestamp < before,
                MCPAuthEvent.ip_address.isnot(None)
            ).order_by(MCPAuthEvent.timestamp.desc()).first()

            if last_success and last_success.ip_address:
                return last_success.ip_address != current_ip

            # No previous login found, so no change detected
            return False
        except Exception as e:
            logger.error(f"Error checking IP change: {e}")
            return False

    def _check_user_agent_change(
        self,
        db: Session,
        user_id: int,
        current_ua: str,
        before: datetime
    ) -> bool:
        """
        Check if user agent has changed from the most recent successful login.

        Args:
            db: Database session
            user_id: User ID to query
            current_ua: Current user agent string
            before: Timestamp to query before

        Returns:
            True if user agent has changed, False otherwise
        """
        try:
            # Get most recent successful login before this event
            last_success = db.query(MCPAuthEvent).filter(
                MCPAuthEvent.user_id == user_id,
                MCPAuthEvent.event_type == "login_success",
                MCPAuthEvent.timestamp < before,
                MCPAuthEvent.user_agent.isnot(None)
            ).order_by(MCPAuthEvent.timestamp.desc()).first()

            if last_success and last_success.user_agent:
                return last_success.user_agent != current_ua

            # No previous login found, so no change detected
            return False
        except Exception as e:
            logger.error(f"Error checking user agent change: {e}")
            return False

    def get_recent_events(
        self,
        db: Session,
        user_id: int,
        since: datetime,
        limit: int = 100
    ) -> List[MCPAuthEvent]:
        """
        Get recent events for a user.

        Args:
            db: Database session
            user_id: User ID to query
            since: Start of time window
            limit: Maximum number of events to return

        Returns:
            List of recent authentication events
        """
        try:
            events = db.query(MCPAuthEvent).filter(
                MCPAuthEvent.user_id == user_id,
                MCPAuthEvent.timestamp >= since
            ).order_by(MCPAuthEvent.timestamp.desc()).limit(limit).all()
            return events
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return []
