"""
Integration tests for fraud assessment query endpoint
"""
import json
from datetime import datetime, timedelta
import pytest

from mcp_server.models import MCPAuthEvent


@pytest.fixture
def setup_test_data(db_session):
    """Create test events with fraud analysis results in the database"""
    print("\n=== Setting up test data ===")

    # Clear existing test data
    db_session.query(MCPAuthEvent).delete()
    db_session.commit()

    # Create test events with fraud analysis
    base_time = datetime.utcnow()

    test_events = [
        # Low risk events
        MCPAuthEvent(
            user_id=123,
            username="john.doe",
            event_type="login_success",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(hours=5),
            event_metadata={"device": "desktop"},
            risk_score=0.1,
            fraud_reason="Normal login pattern",
            analyzed_at=base_time - timedelta(hours=5, minutes=-1)
        ),
        MCPAuthEvent(
            user_id=456,
            username="jane.smith",
            event_type="login_success",
            ip_address="10.0.0.50",
            user_agent="Chrome/91.0",
            timestamp=base_time - timedelta(hours=4),
            event_metadata={"device": "mobile"},
            risk_score=0.2,
            fraud_reason="Normal login pattern",
            analyzed_at=base_time - timedelta(hours=4, minutes=-1)
        ),
        # Medium risk events
        MCPAuthEvent(
            user_id=123,
            username="john.doe",
            event_type="login_failure",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=base_time - timedelta(hours=3),
            event_metadata={"reason": "wrong_password"},
            risk_score=0.5,
            fraud_reason="Failed login attempt detected",
            analyzed_at=base_time - timedelta(hours=3, minutes=-1)
        ),
        MCPAuthEvent(
            user_id=789,
            username="bob.jones",
            event_type="login_success",
            ip_address="203.0.113.50",
            user_agent="Safari/14.0",
            timestamp=base_time - timedelta(hours=2),
            event_metadata={},
            risk_score=0.6,
            fraud_reason="IP address change detected",
            analyzed_at=base_time - timedelta(hours=2, minutes=-1)
        ),
        # High risk events
        MCPAuthEvent(
            user_id=123,
            username="john.doe",
            event_type="login_failure",
            ip_address="198.51.100.10",
            user_agent="Unknown",
            timestamp=base_time - timedelta(hours=1),
            event_metadata={"reason": "wrong_password"},
            risk_score=0.8,
            fraud_reason="Multiple failed login attempts and IP change detected",
            analyzed_at=base_time - timedelta(hours=1, minutes=-1)
        ),
        MCPAuthEvent(
            user_id=456,
            username="jane.smith",
            event_type="2fa_failure",
            ip_address="203.0.113.100",
            user_agent="Chrome/91.0",
            timestamp=base_time - timedelta(minutes=30),
            event_metadata={},
            risk_score=0.9,
            fraud_reason="Multiple failed 2FA attempts and suspicious IP",
            analyzed_at=base_time - timedelta(minutes=30, seconds=-10)
        ),
        # Event without analysis (should not appear in fraud assessments)
        MCPAuthEvent(
            user_id=999,
            username="test.user",
            event_type="login_success",
            ip_address="192.168.1.1",
            user_agent="Test",
            timestamp=base_time,
            event_metadata={},
            risk_score=None,
            fraud_reason=None,
            analyzed_at=None
        ),
    ]

    for event in test_events:
        db_session.add(event)

    db_session.commit()

    # Create alerts for high-risk events (risk_score > 0.7)
    from mcp_server.models import MCPAlert

    high_risk_events = [event for event in test_events if event.risk_score and event.risk_score > 0.7]

    for event in high_risk_events:
        alert = MCPAlert(
            user_id=event.user_id,
            username=event.username,
            event_ids=[event.id],
            risk_score=event.risk_score,
            reason=event.fraud_reason,
            status="open",
            created_at=event.timestamp,
            updated_at=event.timestamp
        )
        db_session.add(alert)

    db_session.commit()

    print(f"✓ Created {len(test_events)} test events (6 with fraud analysis, 1 without)")
    print(f"✓ Created {len(high_risk_events)} alerts for high-risk events")

    yield  # This makes it a fixture


def test_get_all_assessments(setup_test_data, test_client):
    """Test retrieving all fraud assessments"""
    print("\n=== Test 1: Get All Fraud Assessments ===")

    response = test_client.get("/mcp/fraud-assessments")

    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Total assessments: {data['total']}")
    print(f"Returned assessments: {len(data['assessments'])}")
    print(f"Statistics: {json.dumps(data['statistics'], indent=2)}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data['total'] == 6, f"Expected 6 assessments (excluding unanalyzed), got {data['total']}"
    assert len(data['assessments']) == 6, f"Expected 6 assessments returned"
    assert 'statistics' in data, "Response should contain statistics"
    assert 'limit' in data, "Response should contain limit"
    assert 'offset' in data, "Response should contain offset"

    # Verify statistics
    stats = data['statistics']
    assert stats['total_events'] == 6, f"Expected 6 total events, got {stats['total_events']}"
    assert stats['high_risk_events'] == 2, f"Expected 2 high-risk events, got {stats['high_risk_events']}"
    assert stats['medium_risk_events'] == 2, f"Expected 2 medium-risk events, got {stats['medium_risk_events']}"
    assert stats['low_risk_events'] == 2, f"Expected 2 low-risk events, got {stats['low_risk_events']}"
    assert 0 < stats['average_risk_score'] < 1, f"Average risk score should be between 0 and 1"

    print("✓ Test passed: Retrieved all fraud assessments successfully")


def test_filter_by_user_id(setup_test_data, test_client):
    """Test filtering assessments by user_id"""
    print("\n=== Test 2: Filter by User ID ===")

    response = test_client.get("/mcp/fraud-assessments?user_id=123")

    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Total assessments for user 123: {data['total']}")
    print(f"Returned assessments: {len(data['assessments'])}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data['total'] == 3, f"Expected 3 assessments for user 123, got {data['total']}"

    # Verify all returned assessments are for user 123
    for assessment in data['assessments']:
        assert assessment['event']['user_id'] == 123, f"Expected user_id 123, got {assessment['event']['user_id']}"

    print("✓ Test passed: Filtered by user_id successfully")


def test_filter_by_risk_score_range(setup_test_data, test_client):
    """Test filtering assessments by risk score range"""
    print("\n=== Test 3: Filter by Risk Score Range ===")

    # Get high-risk events only (score > 0.7)
    response = test_client.get("/mcp/fraud-assessments?min_risk_score=0.7")

    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Total high-risk assessments: {data['total']}")
    print(f"Returned assessments: {len(data['assessments'])}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data['total'] == 2, f"Expected 2 high-risk assessments, got {data['total']}"

    # Verify all returned assessments have risk_score >= 0.7
    for assessment in data['assessments']:
        assert assessment['risk_score'] >= 0.7, f"Expected risk_score >= 0.7, got {assessment['risk_score']}"
        assert assessment['alert_generated'] is True, "High-risk events should have alert_generated=True"

    # Test medium-risk range
    response2 = test_client.get("/mcp/fraud-assessments?min_risk_score=0.4&max_risk_score=0.7")
    data2 = response2.json()

    print(f"Medium-risk assessments: {data2['total']}")
    assert data2['total'] == 2, f"Expected 2 medium-risk assessments, got {data2['total']}"

    for assessment in data2['assessments']:
        assert 0.4 < assessment['risk_score'] <= 0.7, f"Expected 0.4 < risk_score <= 0.7, got {assessment['risk_score']}"

    print("✓ Test passed: Filtered by risk score range successfully")


def test_sort_by_risk_score(setup_test_data, test_client):
    """Test sorting assessments by risk score"""
    print("\n=== Test 4: Sort by Risk Score ===")

    # Test descending order (default)
    response_desc = test_client.get("/mcp/fraud-assessments?sort_by=risk_score&order=desc")

    print(f"Status Code (desc): {response_desc.status_code}")
    data_desc = response_desc.json()
    print(f"Returned assessments: {len(data_desc['assessments'])}")

    assert response_desc.status_code == 200, f"Expected 200, got {response_desc.status_code}"

    # Verify descending order
    risk_scores_desc = [a['risk_score'] for a in data_desc['assessments']]
    print(f"Risk scores (desc): {risk_scores_desc}")
    for i in range(len(risk_scores_desc) - 1):
        assert risk_scores_desc[i] >= risk_scores_desc[i + 1], "Risk scores should be in descending order"

    # Test ascending order
    response_asc = test_client.get("/mcp/fraud-assessments?sort_by=risk_score&order=asc")
    data_asc = response_asc.json()

    # Verify ascending order
    risk_scores_asc = [a['risk_score'] for a in data_asc['assessments']]
    print(f"Risk scores (asc): {risk_scores_asc}")
    for i in range(len(risk_scores_asc) - 1):
        assert risk_scores_asc[i] <= risk_scores_asc[i + 1], "Risk scores should be in ascending order"

    print("✓ Test passed: Sorting by risk score works correctly")


def test_pagination(setup_test_data, test_client):
    """Test pagination with limit and offset"""
    print("\n=== Test 5: Pagination ===")

    # Get first 3 assessments
    response1 = test_client.get("/mcp/fraud-assessments?limit=3&offset=0&order=desc")
    data1 = response1.json()

    print(f"Page 1 - Status Code: {response1.status_code}")
    print(f"Page 1 - Returned assessments: {len(data1['assessments'])}")
    print(f"Page 1 - Total: {data1['total']}")

    assert response1.status_code == 200, f"Expected 200, got {response1.status_code}"
    assert len(data1['assessments']) == 3, f"Expected 3 assessments, got {len(data1['assessments'])}"
    assert data1['limit'] == 3, f"Expected limit 3, got {data1['limit']}"
    assert data1['offset'] == 0, f"Expected offset 0, got {data1['offset']}"

    # Get next 3 assessments
    response2 = test_client.get("/mcp/fraud-assessments?limit=3&offset=3&order=desc")
    data2 = response2.json()

    print(f"Page 2 - Status Code: {response2.status_code}")
    print(f"Page 2 - Returned assessments: {len(data2['assessments'])}")

    assert response2.status_code == 200, f"Expected 200, got {response2.status_code}"
    assert len(data2['assessments']) == 3, f"Expected 3 assessments, got {len(data2['assessments'])}"
    assert data2['offset'] == 3, f"Expected offset 3, got {data2['offset']}"

    # Verify different assessments returned
    page1_ids = {a['event']['id'] for a in data1['assessments']}
    page2_ids = {a['event']['id'] for a in data2['assessments']}
    assert page1_ids.isdisjoint(page2_ids), "Pages should return different assessments"

    print("✓ Test passed: Pagination works correctly")


def test_combined_filters(setup_test_data, test_client):
    """Test combining multiple filters"""
    print("\n=== Test 6: Combined Filters ===")

    response = test_client.get("/mcp/fraud-assessments?user_id=123&min_risk_score=0.5")

    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Total assessments: {data['total']}")
    print(f"Returned assessments: {len(data['assessments'])}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data['total'] == 2, f"Expected 2 assessments, got {data['total']}"

    # Verify all assessments match both filters
    for assessment in data['assessments']:
        assert assessment['event']['user_id'] == 123, f"Expected user_id 123"
        assert assessment['risk_score'] >= 0.5, f"Expected risk_score >= 0.5"

    print("✓ Test passed: Combined filters work correctly")


def test_invalid_risk_score_range(setup_test_data, test_client):
    """Test with invalid risk score range"""
    print("\n=== Test 7: Invalid Risk Score Range ===")

    response = test_client.get("/mcp/fraud-assessments?min_risk_score=0.8&max_risk_score=0.3")

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    print("✓ Test passed: Invalid risk score range rejected")


def test_assessment_structure(setup_test_data, test_client):
    """Test that assessment structure is correct"""
    print("\n=== Test 8: Assessment Structure ===")

    response = test_client.get("/mcp/fraud-assessments?limit=1")

    print(f"Status Code: {response.status_code}")
    data = response.json()

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(data['assessments']) >= 1, "Need at least 1 assessment"

    # Verify assessment structure
    assessment = data['assessments'][0]
    assert 'event' in assessment, "Assessment should contain event"
    assert 'risk_score' in assessment, "Assessment should contain risk_score"
    assert 'email_notification' in assessment, "Assessment should contain email_notification"
    assert 'alert_generated' in assessment, "Assessment should contain alert_generated"
    assert 'reason' in assessment, "Assessment should contain reason"
    assert 'analyzed_at' in assessment, "Assessment should contain analyzed_at"

    # Verify event structure
    event = assessment['event']
    assert 'id' in event, "Event should contain id"
    assert 'user_id' in event, "Event should contain user_id"
    assert 'username' in event, "Event should contain username"
    assert 'event_type' in event, "Event should contain event_type"
    assert 'risk_score' in event, "Event should contain risk_score"

    # Verify email_notification logic
    if assessment['risk_score'] > 0.7:
        assert assessment['email_notification'] is True, "High-risk events should have email_notification=True"
    else:
        assert assessment['email_notification'] is False, "Low/medium-risk events should have email_notification=False"

    print("✓ Test passed: Assessment structure is correct")


def test_statistics_calculation(setup_test_data, test_client):
    """Test that statistics are calculated correctly"""
    print("\n=== Test 9: Statistics Calculation ===")

    response = test_client.get("/mcp/fraud-assessments")

    print(f"Status Code: {response.status_code}")
    data = response.json()
    stats = data['statistics']

    print(f"Statistics: {json.dumps(stats, indent=2)}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Verify statistics add up
    total_by_risk = stats['high_risk_events'] + stats['medium_risk_events'] + stats['low_risk_events']
    assert total_by_risk == stats['total_events'], \
        f"Risk level counts should add up to total: {total_by_risk} != {stats['total_events']}"

    # Verify average is reasonable
    assert 0 <= stats['average_risk_score'] <= 1, \
        f"Average risk score should be between 0 and 1, got {stats['average_risk_score']}"

    # Calculate expected average manually
    assessments = data['assessments']
    if assessments:
        expected_avg = sum(a['risk_score'] for a in assessments) / len(assessments)
        # Allow small floating point difference
        assert abs(stats['average_risk_score'] - expected_avg) < 0.01, \
            f"Average risk score mismatch: {stats['average_risk_score']} != {expected_avg}"

    print("✓ Test passed: Statistics calculated correctly")
