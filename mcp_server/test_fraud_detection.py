"""
Test script for fraud detection engine (Task 5)
"""
import sys
from datetime import datetime, timedelta
import uuid

sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from mcp_server.main import app
from mcp_server.db import SessionLocal
from mcp_server.models import MCPAuthEvent
from mcp_server.fraud_detector import FraudDetector, FraudAssessment
from mcp_server.schemas import AuthEventIn

client = TestClient(app)


def generate_unique_id(prefix: str) -> str:
    """Generate unique ID for test events"""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def setup_test_events(db, user_id: int, base_time: datetime):
    """Helper to create test events in database"""
    events = []

    # Create some historical successful logins
    for i in range(3):
        event = MCPAuthEvent(
            id=f"test-success-{user_id}-{i}",
            user_id=user_id,
            username=f"test_user_{user_id}",
            event_type="login_success",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0)",
            timestamp=base_time - timedelta(hours=i+1),
            event_metadata={}
        )
        db.add(event)
        events.append(event)

    db.commit()
    return events


def test_fraud_assessment_model():
    """Test FraudAssessment model creation"""
    print("\n✓ Test FraudAssessment Model")

    assessment = FraudAssessment(
        risk_score=0.8,
        alert=True,
        reason="Test reason",
        confidence=1.0
    )

    assert assessment.risk_score == 0.8
    assert assessment.alert is True
    assert assessment.reason == "Test reason"
    assert assessment.confidence == 1.0

    print("  Verified: FraudAssessment model works correctly")


def test_fraud_detector_initialization():
    """Test FraudDetector initialization"""
    print("\n✓ Test FraudDetector Initialization")

    detector = FraudDetector(fraud_threshold=0.7)
    assert detector.fraud_threshold == 0.7

    detector2 = FraudDetector(fraud_threshold=0.5)
    assert detector2.fraud_threshold == 0.5

    print("  Verified: FraudDetector initializes with custom threshold")


def test_rule_multiple_failed_logins():
    """Test Rule: Multiple failed login attempts (3+ in 5 minutes): +0.3"""
    print("\n✓ Test Rule: Multiple Failed Login Attempts")

    db = SessionLocal()
    detector = FraudDetector(fraud_threshold=0.7)

    user_id = 5001
    base_time = datetime.utcnow()

    # Create 4 failed login attempts in the last 5 minutes
    for i in range(4):
        event = MCPAuthEvent(
            id=generate_unique_id(f"failed-login-{user_id}"),
            user_id=user_id,
            username=f"test_user_{user_id}",
            event_type="login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=i),
            event_metadata={}
        )
        db.add(event)
    db.commit()

    # Analyze a new event
    new_event = AuthEventIn(
        user_id=user_id,
        username=f"test_user_{user_id}",
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
        timestamp=base_time.isoformat() + "Z",
        metadata={}
    )

    assessment = detector.analyze_event(new_event, db)

    assert assessment.risk_score >= 0.3, f"Risk score should be at least 0.3, got {assessment.risk_score}"
    assert "failed login attempts" in assessment.reason.lower()

    db.close()
    print(f"  Verified: Risk score = {assessment.risk_score:.2f}, Reason: {assessment.reason}")


def test_rule_multiple_failed_2fa():
    """Test Rule: Multiple failed 2FA attempts (3+ in 5 minutes): +0.4"""
    print("\n✓ Test Rule: Multiple Failed 2FA Attempts")

    db = SessionLocal()
    detector = FraudDetector(fraud_threshold=0.7)

    user_id = 5002
    base_time = datetime.utcnow()

    # Create 3 failed 2FA attempts in the last 5 minutes
    for i in range(3):
        event = MCPAuthEvent(
            id=generate_unique_id(f"failed-2fa-{user_id}"),
            user_id=user_id,
            username=f"test_user_{user_id}",
            event_type="2fa_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(minutes=i),
            event_metadata={}
        )
        db.add(event)
    db.commit()

    # Analyze a new event
    new_event = AuthEventIn(
        user_id=user_id,
        username=f"test_user_{user_id}",
        event_type="2fa_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
        timestamp=base_time.isoformat() + "Z",
        metadata={}
    )

    assessment = detector.analyze_event(new_event, db)

    assert assessment.risk_score >= 0.4, f"Risk score should be at least 0.4, got {assessment.risk_score}"
    assert "2fa" in assessment.reason.lower()

    db.close()
    print(f"  Verified: Risk score = {assessment.risk_score:.2f}, Reason: {assessment.reason}")


def test_rule_ip_address_change():
    """Test Rule: IP address change from previous login: +0.2"""
    print("\n✓ Test Rule: IP Address Change")

    db = SessionLocal()
    detector = FraudDetector(fraud_threshold=0.7)

    user_id = 5003
    base_time = datetime.utcnow()

    # Create a previous successful login with different IP
    prev_event = MCPAuthEvent(
        id=generate_unique_id(f"prev-login-{user_id}"),
        user_id=user_id,
        username=f"test_user_{user_id}",
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db.add(prev_event)
    db.commit()

    # Analyze a new event with different IP
    new_event = AuthEventIn(
        user_id=user_id,
        username=f"test_user_{user_id}",
        event_type="login_success",
        ip_address="10.0.0.50",  # Different IP
        user_agent="Mozilla/5.0",
        timestamp=base_time.isoformat() + "Z",
        metadata={}
    )

    assessment = detector.analyze_event(new_event, db)

    assert assessment.risk_score >= 0.2, f"Risk score should be at least 0.2, got {assessment.risk_score}"
    assert "ip address changed" in assessment.reason.lower()

    db.close()
    print(f"  Verified: Risk score = {assessment.risk_score:.2f}, Reason: {assessment.reason}")


def test_rule_user_agent_change():
    """Test Rule: User agent change from previous login: +0.1"""
    print("\n✓ Test Rule: User Agent Change")

    db = SessionLocal()
    detector = FraudDetector(fraud_threshold=0.7)

    user_id = 5004
    base_time = datetime.utcnow()

    # Create a previous successful login with different user agent
    prev_event = MCPAuthEvent(
        id=generate_unique_id(f"prev-login-{user_id}"),
        user_id=user_id,
        username=f"test_user_{user_id}",
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0)",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db.add(prev_event)
    db.commit()

    # Analyze a new event with different user agent
    new_event = AuthEventIn(
        user_id=user_id,
        username=f"test_user_{user_id}",
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Chrome/91.0 (Macintosh)",  # Different user agent
        timestamp=base_time.isoformat() + "Z",
        metadata={}
    )

    assessment = detector.analyze_event(new_event, db)

    assert assessment.risk_score >= 0.1, f"Risk score should be at least 0.1, got {assessment.risk_score}"
    assert "user agent changed" in assessment.reason.lower()

    db.close()
    print(f"  Verified: Risk score = {assessment.risk_score:.2f}, Reason: {assessment.reason}")


def test_combined_rules():
    """Test multiple rules triggering together"""
    print("\n✓ Test Combined Rules")

    db = SessionLocal()
    detector = FraudDetector(fraud_threshold=0.7)

    user_id = 5005
    base_time = datetime.utcnow()

    # Create previous successful login
    prev_event = MCPAuthEvent(
        id=generate_unique_id(f"prev-login-{user_id}"),
        user_id=user_id,
        username=f"test_user_{user_id}",
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0)",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db.add(prev_event)

    # Create multiple failed login attempts
    for i in range(4):
        event = MCPAuthEvent(
            id=generate_unique_id(f"failed-login-{user_id}"),
            user_id=user_id,
            username=f"test_user_{user_id}",
            event_type="login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0)",
            timestamp=base_time - timedelta(minutes=i),
            event_metadata={}
        )
        db.add(event)

    db.commit()

    # Analyze new event with IP and UA change
    new_event = AuthEventIn(
        user_id=user_id,
        username=f"test_user_{user_id}",
        event_type="login_success",
        ip_address="10.0.0.50",  # Different IP
        user_agent="Chrome/91.0",  # Different UA
        timestamp=base_time.isoformat() + "Z",
        metadata={}
    )

    assessment = detector.analyze_event(new_event, db)

    # Should have: 0.3 (failed logins) + 0.2 (IP change) + 0.1 (UA change) = 0.6
    assert assessment.risk_score >= 0.6, f"Risk score should be at least 0.6, got {assessment.risk_score}"
    assert "failed login" in assessment.reason.lower()
    assert "ip address" in assessment.reason.lower()
    assert "user agent" in assessment.reason.lower()

    db.close()
    print(f"  Verified: Risk score = {assessment.risk_score:.2f}, Reason: {assessment.reason}")


def test_alert_threshold():
    """Test that alert flag is set when risk_score >= threshold"""
    print("\n✓ Test Alert Threshold")

    db = SessionLocal()
    detector = FraudDetector(fraud_threshold=0.7)

    user_id = 5006
    base_time = datetime.utcnow()

    # Create scenario that triggers high risk score
    # Previous successful login with original IP/UA
    prev_event = MCPAuthEvent(
        id=generate_unique_id(f"prev-login-{user_id}"),
        user_id=user_id,
        username=f"test_user_{user_id}",
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db.add(prev_event)

    # Multiple failed logins with new IP/UA
    for i in range(4):
        event = MCPAuthEvent(
            id=generate_unique_id(f"failed-login-{user_id}"),
            user_id=user_id,
            username=f"test_user_{user_id}",
            event_type="login_failure",
            ip_address="10.0.0.50",
            user_agent="Chrome/91.0",
            timestamp=base_time - timedelta(minutes=i),
            event_metadata={}
        )
        db.add(event)

    # Multiple failed 2FA with new IP/UA
    for i in range(3):
        event = MCPAuthEvent(
            id=generate_unique_id(f"failed-2fa-{user_id}"),
            user_id=user_id,
            username=f"test_user_{user_id}",
            event_type="2fa_failure",
            ip_address="10.0.0.50",
            user_agent="Chrome/91.0",
            timestamp=base_time - timedelta(minutes=i),
            event_metadata={}
        )
        db.add(event)

    db.commit()

    # Analyze new event with the new IP/UA (different from previous successful login)
    new_event = AuthEventIn(
        user_id=user_id,
        username=f"test_user_{user_id}",
        event_type="login_success",
        ip_address="10.0.0.50",  # Different from previous successful login
        user_agent="Chrome/91.0",  # Different from previous successful login
        timestamp=base_time.isoformat() + "Z",
        metadata={}
    )

    assessment = detector.analyze_event(new_event, db)

    # Should have: 0.3 (failed logins) + 0.4 (failed 2FA) + 0.2 (IP change) + 0.1 (UA change) = 1.0 (capped)
    assert assessment.risk_score >= 0.7, f"Risk score should be >= 0.7, got {assessment.risk_score}"
    assert assessment.alert is True, "Alert should be True for high risk score"

    db.close()
    print(f"  Verified: Risk score = {assessment.risk_score:.2f}, Alert = {assessment.alert}")


def test_event_persistence_with_fraud_analysis():
    """Test that events are updated with fraud analysis results"""
    print("\n✓ Test Event Persistence with Fraud Analysis")

    user_id = 5007
    base_time = datetime.utcnow()

    # Create event via API
    event_data = {
        "user_id": user_id,
        "username": f"test_user_{user_id}",
        "event_type": "login_success",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0",
        "timestamp": base_time.isoformat() + "Z",
        "metadata": {}
    }

    response = client.post("/mcp/ingest", json=event_data)
    assert response.status_code == 201

    event_id = response.json()["event_id"]

    # Query database to verify fraud analysis was performed
    db = SessionLocal()
    stored_event = db.query(MCPAuthEvent).filter(MCPAuthEvent.id == event_id).first()

    assert stored_event is not None
    assert stored_event.risk_score is not None, "Risk score should be set"
    assert stored_event.fraud_reason is not None, "Fraud reason should be set"
    assert stored_event.analyzed_at is not None, "Analyzed timestamp should be set"

    db.close()
    print(f"  Verified: Event stored with risk_score={stored_event.risk_score:.2f}, reason='{stored_event.fraud_reason}'")


def test_normal_authentication_pattern():
    """Test that normal authentication has low risk score"""
    print("\n✓ Test Normal Authentication Pattern")

    db = SessionLocal()
    detector = FraudDetector(fraud_threshold=0.7)

    user_id = 5008
    base_time = datetime.utcnow()

    # Create normal previous login
    prev_event = MCPAuthEvent(
        id=generate_unique_id(f"prev-login-{user_id}"),
        user_id=user_id,
        username=f"test_user_{user_id}",
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
        timestamp=base_time - timedelta(hours=1),
        event_metadata={}
    )
    db.add(prev_event)
    db.commit()

    # Analyze normal new event (same IP, same UA, no failures)
    new_event = AuthEventIn(
        user_id=user_id,
        username=f"test_user_{user_id}",
        event_type="login_success",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
        timestamp=base_time.isoformat() + "Z",
        metadata={}
    )

    assessment = detector.analyze_event(new_event, db)

    assert assessment.risk_score == 0.0, f"Risk score should be 0.0 for normal pattern, got {assessment.risk_score}"
    assert assessment.alert is False, "Alert should be False for normal pattern"
    assert "normal" in assessment.reason.lower()

    db.close()
    print(f"  Verified: Risk score = {assessment.risk_score:.2f}, Alert = {assessment.alert}")


if __name__ == "__main__":
    print("=" * 60)
    print("Task 5: Fraud Detection Engine Verification")
    print("=" * 60)

    try:
        test_fraud_assessment_model()
        test_fraud_detector_initialization()
        test_rule_multiple_failed_logins()
        test_rule_multiple_failed_2fa()
        test_rule_ip_address_change()
        test_rule_user_agent_change()
        test_combined_rules()
        test_alert_threshold()
        test_event_persistence_with_fraud_analysis()
        test_normal_authentication_pattern()

        print("\n" + "=" * 60)
        print("✓ ALL FRAUD DETECTION TESTS PASSED")
        print("=" * 60)
        print("\nTask 5 Implementation Summary:")
        print("  ✓ Created fraud_detector.py with FraudDetector class")
        print("  ✓ Created FraudAssessment model with risk_score, alert, reason")
        print("  ✓ Implemented _rule_based_analysis with all scoring rules:")
        print("    - Multiple failed login attempts (3+ in 5 min): +0.3")
        print("    - Multiple failed 2FA attempts (3+ in 5 min): +0.4")
        print("    - IP address change: +0.2")
        print("    - User agent change: +0.1")
        print("  ✓ Implemented helper methods for querying recent events")
        print("  ✓ Integrated fraud detection into event ingestion")
        print("  ✓ MCPAuthEvent updated with risk_score and fraud_reason")
        print("  ✓ Requirements 3.1, 3.2, 3.3, 3.4, 3.5 satisfied")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
