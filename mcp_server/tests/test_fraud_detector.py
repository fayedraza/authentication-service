"""
Unit tests for fraud detection engine.

Tests each rule-based detection rule independently, risk score calculation,
alert threshold logic, and BAML fallback behavior.

Requirements: 3.1, 3.2, 3.3, 3.5, 5.5
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch

from db import Base
from models import MCPAuthEvent
from fraud_detector import FraudDetector, FraudAssessment
from schemas import AuthEventIn
from baml_client import BAMLClient, BAMLFraudAssessment, LoginEvent

# Create test database
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database session for each test"""
    db = TestingSessionLocal()
    try:
        # Clean database
        db.query(MCPAuthEvent).delete()
        db.commit()
        yield db
    finally:
        db.close()


@pytest.fixture
def fraud_detector():
    """Create a fraud detector instance with default settings"""
    return FraudDetector(fraud_threshold=0.7, baml_enabled=False)


@pytest.fixture
def base_event():
    """Create a base authentication event for testing"""
    return AuthEventIn(
        user_id=1000,
        username="test_user",
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        timestamp=datetime.utcnow().isoformat() + "Z",
        metadata={}
    )


# ============================================================================
# Rule 1: Multiple Failed Login Attempts Tests
# ============================================================================

def test_rule_multiple_failed_logins_triggers(db_session, fraud_detector, base_event):
    """
    Test that 3+ failed login attempts in 5 minutes adds 0.3 to risk score.
    Requirements: 3.2
    """
    base_time = datetime.utcnow()

    # Create 3 failed login attempts in the last 5 minutes
    for i in range(3):
        failed_event = MCPAuthEvent(
            id=f"failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db_session.add(failed_event)
    db_session.commit()

    # Analyze new event
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    assert assessment.risk_score >= 0.3
    assert "Multiple failed login attempts" in assessment.reason
    assert "(3 in 5 minutes)" in assessment.reason


def test_rule_multiple_failed_logins_no_trigger(db_session, fraud_detector, base_event):
    """
    Test that fewer than 3 failed login attempts does not trigger the rule.
    Requirements: 3.2
    """
    base_time = datetime.utcnow()

    # Create only 2 failed login attempts
    for i in range(2):
        failed_event = MCPAuthEvent(
            id=f"failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=3-i),
            event_metadata={}
        )
        db_session.add(failed_event)
    db_session.commit()

    # Analyze new event
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    assert "Multiple failed login attempts" not in assessment.reason


def test_rule_multiple_failed_logins_outside_window(db_session, fraud_detector, base_event):
    """
    Test that failed logins outside the 5-minute window don't trigger the rule.
    Requirements: 3.2
    """
    base_time = datetime.utcnow()

    # Create 3 failed login attempts but outside the 5-minute window
    for i in range(3):
        failed_event = MCPAuthEvent(
            id=f"failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=10+i),
            event_metadata={}
        )
        db_session.add(failed_event)
    db_session.commit()

    # Analyze new event
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    assert "Multiple failed login attempts" not in assessment.reason


# ============================================================================
# Rule 2: Multiple Failed 2FA Attempts Tests
# ============================================================================

def test_rule_multiple_failed_2fa_triggers(db_session, fraud_detector, base_event):
    """
    Test that 3+ failed 2FA attempts in 5 minutes adds 0.4 to risk score.
    Requirements: 3.2
    """
    base_time = datetime.utcnow()

    # Create 3 failed 2FA attempts in the last 5 minutes
    for i in range(3):
        failed_2fa = MCPAuthEvent(
            id=f"2fa-failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="2fa_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db_session.add(failed_2fa)
    db_session.commit()

    # Analyze new event
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    assert assessment.risk_score >= 0.4
    assert "Multiple failed 2FA attempts" in assessment.reason
    assert "(3 in 5 minutes)" in assessment.reason


def test_rule_multiple_failed_2fa_no_trigger(db_session, fraud_detector, base_event):
    """
    Test that fewer than 3 failed 2FA attempts does not trigger the rule.
    Requirements: 3.2
    """
    base_time = datetime.utcnow()

    # Create only 2 failed 2FA attempts
    for i in range(2):
        failed_2fa = MCPAuthEvent(
            id=f"2fa-failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="2fa_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=3-i),
            event_metadata={}
        )
        db_session.add(failed_2fa)
    db_session.commit()

    # Analyze new event
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    assert "Multiple failed 2FA attempts" not in assessment.reason


# ============================================================================
# Rule 3: IP Address Change Tests
# ============================================================================

def test_rule_ip_change_triggers(db_session, fraud_detector, base_event):
    """
    Test that IP address change from previous login adds 0.2 to risk score.
    Requirements: 3.2
    """
    base_time = datetime.utcnow()

    # Create previous successful login with different IP
    prev_login = MCPAuthEvent(
        id="prev-login",
        user_id=base_event.user_id,
        username=base_event.username,
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db_session.add(prev_login)
    db_session.commit()

    # Analyze new event with different IP
    base_event.ip_address = "10.0.0.50"
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    assert assessment.risk_score >= 0.2
    assert "IP address changed from previous login" in assessment.reason


def test_rule_ip_change_no_trigger_same_ip(db_session, fraud_detector, base_event):
    """
    Test that same IP address does not trigger the rule.
    Requirements: 3.2
    """
    base_time = datetime.utcnow()

    # Create previous successful login with same IP
    prev_login = MCPAuthEvent(
        id="prev-login",
        user_id=base_event.user_id,
        username=base_event.username,
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db_session.add(prev_login)
    db_session.commit()

    # Analyze new event with same IP
    base_event.ip_address = "192.168.1.100"
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    assert "IP address changed" not in assessment.reason


def test_rule_ip_change_no_trigger_no_previous_login(db_session, fraud_detector, base_event):
    """
    Test that no IP change is detected when there's no previous login.
    Requirements: 3.2
    """
    base_time = datetime.utcnow()

    # No previous login events
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    assert "IP address changed" not in assessment.reason


# ============================================================================
# Rule 4: User Agent Change Tests
# ============================================================================

def test_rule_user_agent_change_triggers(db_session, fraud_detector, base_event):
    """
    Test that user agent change from previous login adds 0.1 to risk score.
    Requirements: 3.2
    """
    base_time = datetime.utcnow()

    # Create previous successful login with different user agent
    prev_login = MCPAuthEvent(
        id="prev-login",
        user_id=base_event.user_id,
        username=base_event.username,
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db_session.add(prev_login)
    db_session.commit()

    # Analyze new event with different user agent
    base_event.user_agent = "Chrome/91.0.4472.124"
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    assert assessment.risk_score >= 0.1
    assert "User agent changed from previous login" in assessment.reason


def test_rule_user_agent_change_no_trigger_same_ua(db_session, fraud_detector, base_event):
    """
    Test that same user agent does not trigger the rule.
    Requirements: 3.2
    """
    base_time = datetime.utcnow()

    # Create previous successful login with same user agent
    prev_login = MCPAuthEvent(
        id="prev-login",
        user_id=base_event.user_id,
        username=base_event.username,
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db_session.add(prev_login)
    db_session.commit()

    # Analyze new event with same user agent
    base_event.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    assert "User agent changed" not in assessment.reason


# ============================================================================
# Risk Score Calculation Tests
# ============================================================================

def test_risk_score_multiple_rules_combined(db_session, fraud_detector, base_event):
    """
    Test that multiple rules combine their risk scores correctly.
    Requirements: 3.1, 3.3
    """
    base_time = datetime.utcnow()

    # Create previous successful login with different IP and user agent
    prev_login = MCPAuthEvent(
        id="prev-login",
        user_id=base_event.user_id,
        username=base_event.username,
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db_session.add(prev_login)

    # Create 3 failed login attempts
    for i in range(3):
        failed_event = MCPAuthEvent(
            id=f"failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="login_failure",
            ip_address="10.0.0.50",
            user_agent="Chrome/91.0",
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db_session.add(failed_event)

    # Create 3 failed 2FA attempts
    for i in range(3):
        failed_2fa = MCPAuthEvent(
            id=f"2fa-failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="2fa_failure",
            ip_address="10.0.0.50",
            user_agent="Chrome/91.0",
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db_session.add(failed_2fa)

    db_session.commit()

    # Analyze new event with different IP and user agent
    base_event.ip_address = "10.0.0.50"
    base_event.user_agent = "Chrome/91.0"
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    # Expected: 0.3 (failed logins) + 0.4 (failed 2FA) + 0.2 (IP change) + 0.1 (UA change) = 1.0
    assert assessment.risk_score >= 0.99  # Allow for floating point precision
    assert assessment.risk_score <= 1.0
    assert "Multiple failed login attempts" in assessment.reason
    assert "Multiple failed 2FA attempts" in assessment.reason
    assert "IP address changed" in assessment.reason
    assert "User agent changed" in assessment.reason


def test_risk_score_capped_at_one(db_session, fraud_detector, base_event):
    """
    Test that risk score is capped at 1.0 even if rules would exceed it.
    Requirements: 3.1
    """
    base_time = datetime.utcnow()

    # Create conditions that would exceed 1.0
    # (This test verifies the cap is working)
    prev_login = MCPAuthEvent(
        id="prev-login",
        user_id=base_event.user_id,
        username=base_event.username,
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db_session.add(prev_login)

    for i in range(5):
        failed_event = MCPAuthEvent(
            id=f"failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="login_failure",
            ip_address="10.0.0.50",
            user_agent="Chrome/91.0",
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db_session.add(failed_event)

    for i in range(5):
        failed_2fa = MCPAuthEvent(
            id=f"2fa-failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="2fa_failure",
            ip_address="10.0.0.50",
            user_agent="Chrome/91.0",
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db_session.add(failed_2fa)

    db_session.commit()

    base_event.ip_address = "10.0.0.50"
    base_event.user_agent = "Chrome/91.0"
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    assert assessment.risk_score <= 1.0


def test_risk_score_zero_for_normal_activity(db_session, fraud_detector, base_event):
    """
    Test that normal activity results in zero risk score.
    Requirements: 3.1
    """
    base_time = datetime.utcnow()

    # Create previous successful login with same IP and user agent
    prev_login = MCPAuthEvent(
        id="prev-login",
        user_id=base_event.user_id,
        username=base_event.username,
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db_session.add(prev_login)
    db_session.commit()

    # Analyze new event with same IP and user agent, no failed attempts
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    assert assessment.risk_score == 0.0
    assert "Normal authentication pattern" in assessment.reason


# ============================================================================
# Alert Threshold Tests
# ============================================================================

def test_alert_threshold_triggers_above_threshold(db_session, fraud_detector, base_event):
    """
    Test that alert flag is True when risk score exceeds threshold.
    Requirements: 3.3
    """
    base_time = datetime.utcnow()

    # Create conditions for high risk score (> 0.7)
    for i in range(3):
        failed_event = MCPAuthEvent(
            id=f"failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db_session.add(failed_event)

    for i in range(3):
        failed_2fa = MCPAuthEvent(
            id=f"2fa-failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="2fa_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db_session.add(failed_2fa)

    db_session.commit()

    # Risk score should be 0.3 + 0.4 = 0.7
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    assert assessment.risk_score >= 0.7
    assert assessment.alert is True


def test_alert_threshold_no_trigger_below_threshold(db_session, fraud_detector, base_event):
    """
    Test that alert flag is False when risk score is below threshold.
    Requirements: 3.3
    """
    base_time = datetime.utcnow()

    # Create conditions for low risk score (< 0.7)
    for i in range(2):
        failed_event = MCPAuthEvent(
            id=f"failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db_session.add(failed_event)

    db_session.commit()

    # Risk score should be 0.0 (only 2 failed attempts, need 3)
    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = fraud_detector.analyze_event(base_event, db_session)

    assert assessment.risk_score < 0.7
    assert assessment.alert is False


def test_alert_threshold_custom_threshold(db_session, base_event):
    """
    Test that custom threshold values work correctly.
    Requirements: 3.3
    """
    # Create detector with custom threshold
    custom_detector = FraudDetector(fraud_threshold=0.5, baml_enabled=False)
    base_time = datetime.utcnow()

    # Create conditions for risk score of 0.4
    for i in range(3):
        failed_2fa = MCPAuthEvent(
            id=f"2fa-failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="2fa_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db_session.add(failed_2fa)

    db_session.commit()

    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = custom_detector.analyze_event(base_event, db_session)

    # Risk score is 0.4, which is below default 0.7 but below custom 0.5
    assert assessment.risk_score == 0.4
    assert assessment.alert is False


# ============================================================================
# BAML Fallback Behavior Tests
# ============================================================================

def test_baml_fallback_when_disabled(db_session, base_event):
    """
    Test that rule-based detection is used when BAML is disabled.
    Requirements: 5.5
    """
    detector = FraudDetector(fraud_threshold=0.7, baml_enabled=False)
    base_time = datetime.utcnow()

    # Create conditions for rule-based detection
    for i in range(3):
        failed_event = MCPAuthEvent(
            id=f"failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db_session.add(failed_event)

    db_session.commit()

    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = detector.analyze_event(base_event, db_session)

    # Should use rule-based detection
    assert assessment.risk_score == 0.3
    assert assessment.confidence == 1.0
    assert "[BAML]" not in assessment.reason


@patch('mcp_server.fraud_detector.get_baml_client')
def test_baml_fallback_when_unavailable(mock_get_baml_client, db_session, base_event):
    """
    Test that rule-based detection is used when BAML client is unavailable.
    Requirements: 5.5
    """
    # Mock BAML client as unavailable
    mock_client = Mock(spec=BAMLClient)
    mock_client.is_available.return_value = False
    mock_get_baml_client.return_value = mock_client

    detector = FraudDetector(fraud_threshold=0.7, baml_enabled=True)
    base_time = datetime.utcnow()

    # Create conditions for rule-based detection
    for i in range(3):
        failed_event = MCPAuthEvent(
            id=f"failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db_session.add(failed_event)

    db_session.commit()

    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = detector.analyze_event(base_event, db_session)

    # Should fall back to rule-based detection
    assert assessment.risk_score == 0.3
    assert assessment.confidence == 1.0
    assert "[BAML]" not in assessment.reason


@patch('mcp_server.fraud_detector.get_baml_client')
def test_baml_analysis_success(mock_get_baml_client, db_session, base_event):
    """
    Test that BAML analysis is used when available and returns results.
    Requirements: 5.5
    """
    # Mock BAML client with successful response
    mock_client = Mock(spec=BAMLClient)
    mock_client.is_available.return_value = True

    baml_result = BAMLFraudAssessment(
        risk_score=0.85,
        alert=True,
        reason="AI detected suspicious pattern",
        confidence=0.95
    )
    mock_client.analyze_fraud_sync.return_value = baml_result
    mock_get_baml_client.return_value = mock_client

    detector = FraudDetector(fraud_threshold=0.7, baml_enabled=True)
    base_time = datetime.utcnow()

    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = detector.analyze_event(base_event, db_session)

    # Should use BAML result
    assert assessment.risk_score == 0.85
    assert assessment.alert is True
    assert assessment.confidence == 0.95
    assert "[BAML]" in assessment.reason
    assert "AI detected suspicious pattern" in assessment.reason


@patch('mcp_server.fraud_detector.get_baml_client')
def test_baml_fallback_on_error(mock_get_baml_client, db_session, base_event):
    """
    Test that rule-based detection is used when BAML analysis fails.
    Requirements: 5.5
    """
    # Mock BAML client that returns None (error case)
    mock_client = Mock(spec=BAMLClient)
    mock_client.is_available.return_value = True
    mock_client.analyze_fraud_sync.return_value = None
    mock_get_baml_client.return_value = mock_client

    detector = FraudDetector(fraud_threshold=0.7, baml_enabled=True)
    base_time = datetime.utcnow()

    # Create conditions for rule-based detection
    for i in range(3):
        failed_event = MCPAuthEvent(
            id=f"failed-{i}",
            user_id=base_event.user_id,
            username=base_event.username,
            event_type="login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=4-i),
            event_metadata={}
        )
        db_session.add(failed_event)

    db_session.commit()

    base_event.timestamp = base_time.isoformat() + "Z"
    assessment = detector.analyze_event(base_event, db_session)

    # Should fall back to rule-based detection
    assert assessment.risk_score == 0.3
    assert assessment.confidence == 1.0
    assert "[BAML]" not in assessment.reason


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_error_handling_returns_safe_default(db_session, base_event):
    """
    Test that errors during analysis are handled gracefully.
    Requirements: 3.5
    """
    # Create a detector and force an error by passing invalid database session
    detector = FraudDetector(fraud_threshold=0.7, baml_enabled=False)

    # Pass None as database session to trigger error in helper methods
    # The helper methods catch errors and return 0/False, so analysis continues
    assessment = detector.analyze_event(base_event, None)

    # Should handle errors gracefully and return a result
    # Since all helper methods return safe defaults (0, False), we get normal pattern
    assert assessment.risk_score == 0.0
    assert assessment.alert is False
    assert assessment.confidence == 1.0
    # The reason will be "Normal authentication pattern" since no rules triggered


# ============================================================================
# Helper Method Tests
# ============================================================================

def test_count_recent_events(db_session, fraud_detector):
    """
    Test the _count_recent_events helper method.
    Requirements: 3.2
    """
    base_time = datetime.utcnow()
    user_id = 2000

    # Create events within window
    for i in range(3):
        event = MCPAuthEvent(
            id=f"event-{i}",
            user_id=user_id,
            username="test_user",
            event_type="login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=i),
            event_metadata={}
        )
        db_session.add(event)

    # Create events outside window
    for i in range(2):
        event = MCPAuthEvent(
            id=f"old-event-{i}",
            user_id=user_id,
            username="test_user",
            event_type="login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=10+i),
            event_metadata={}
        )
        db_session.add(event)

    db_session.commit()

    # Count events in 5-minute window
    count = fraud_detector._count_recent_events(
        db=db_session,
        user_id=user_id,
        event_type="login_failure",
        since=base_time - timedelta(minutes=5),
        before=base_time + timedelta(seconds=1)
    )

    assert count == 3


def test_check_ip_change(db_session, fraud_detector):
    """
    Test the _check_ip_change helper method.
    Requirements: 3.2
    """
    base_time = datetime.utcnow()
    user_id = 2001

    # Create previous successful login
    prev_login = MCPAuthEvent(
        id="prev-login",
        user_id=user_id,
        username="test_user",
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db_session.add(prev_login)
    db_session.commit()

    # Check with different IP
    ip_changed = fraud_detector._check_ip_change(
        db=db_session,
        user_id=user_id,
        current_ip="10.0.0.50",
        before=base_time
    )
    assert ip_changed is True

    # Check with same IP
    ip_not_changed = fraud_detector._check_ip_change(
        db=db_session,
        user_id=user_id,
        current_ip="192.168.1.100",
        before=base_time
    )
    assert ip_not_changed is False


def test_check_user_agent_change(db_session, fraud_detector):
    """
    Test the _check_user_agent_change helper method.
    Requirements: 3.2
    """
    base_time = datetime.utcnow()
    user_id = 2002

    # Create previous successful login
    prev_login = MCPAuthEvent(
        id="prev-login",
        user_id=user_id,
        username="test_user",
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db_session.add(prev_login)
    db_session.commit()

    # Check with different user agent
    ua_changed = fraud_detector._check_user_agent_change(
        db=db_session,
        user_id=user_id,
        current_ua="Chrome/91.0.4472.124",
        before=base_time
    )
    assert ua_changed is True

    # Check with same user agent
    ua_not_changed = fraud_detector._check_user_agent_change(
        db=db_session,
        user_id=user_id,
        current_ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        before=base_time
    )
    assert ua_not_changed is False


# ============================================================================
# Run all tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
