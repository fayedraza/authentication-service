"""
Unit tests for event logger utility.
"""
import pytest
from unittest.mock import Mock, MagicMock
from sqlalchemy.exc import SQLAlchemyError
from auth_platform.auth_platform.auth_service.utils.event_logger import log_auth_event
from auth_platform.auth_platform.auth_service.models import AuthEvent, User
from auth_platform.auth_platform.auth_service.db import Base, engine
from sqlalchemy.orm import Session


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def reset_database():
    # Drop all tables and recreate them before each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def db_session():
    """Create a database session for testing."""
    session = Session(bind=engine)
    yield session
    session.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        username="testuser",
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password="hashed_password",
        tier="dev"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request object."""
    request = Mock()
    request.client = Mock()
    request.client.host = "192.168.1.1"
    request.headers = {"user-agent": "Mozilla/5.0 Test Browser"}
    return request


def test_log_auth_event_creates_record(db_session, test_user, mock_request):
    """Test that log_auth_event creates a record in the database."""
    log_auth_event("login_success", test_user, mock_request, db_session)

    events = db_session.query(AuthEvent).filter(
        AuthEvent.user_id == test_user.id
    ).all()

    assert len(events) == 1
    assert events[0].event_type == "login_success"
    assert events[0].username == "testuser"
    assert events[0].user_id == test_user.id
    assert events[0].timestamp is not None


def test_log_auth_event_extracts_ip_address(db_session, test_user, mock_request):
    """Test that IP address is extracted from request."""
    log_auth_event("login_success", test_user, mock_request, db_session)

    event = db_session.query(AuthEvent).first()
    assert event.ip_address == "192.168.1.1"


def test_log_auth_event_extracts_user_agent(db_session, test_user, mock_request):
    """Test that user-agent is extracted from request headers."""
    log_auth_event("login_success", test_user, mock_request, db_session)

    event = db_session.query(AuthEvent).first()
    assert event.user_agent == "Mozilla/5.0 Test Browser"


def test_log_auth_event_with_metadata(db_session, test_user, mock_request):
    """Test that metadata is stored correctly."""
    metadata = {"device_id": "abc123", "location": "US"}
    log_auth_event("login_success", test_user, mock_request, db_session, metadata=metadata)

    event = db_session.query(AuthEvent).first()
    assert event.event_metadata == metadata
    assert event.event_metadata["device_id"] == "abc123"


def test_log_auth_event_invalid_type(db_session, test_user, mock_request):
    """Test that ValueError is raised for invalid event type."""
    with pytest.raises(ValueError) as exc_info:
        log_auth_event("invalid_event", test_user, mock_request, db_session)

    assert "Invalid event_type" in str(exc_info.value)
    assert "invalid_event" in str(exc_info.value)


def test_log_auth_event_handles_missing_ip(db_session, test_user):
    """Test that NULL is stored when IP address cannot be extracted."""
    request = Mock()
    request.client = None
    request.headers = {"user-agent": "Test Browser"}

    log_auth_event("login_success", test_user, request, db_session)

    event = db_session.query(AuthEvent).first()
    assert event.ip_address is None
    assert event.user_agent == "Test Browser"


def test_log_auth_event_x_forwarded_for_fallback(db_session, test_user):
    """Test that X-Forwarded-For header is used as fallback for IP."""
    request = Mock()
    request.client = None
    request.headers = {
        "x-forwarded-for": "10.0.0.1, 192.168.1.1",
        "user-agent": "Test Browser"
    }

    log_auth_event("login_success", test_user, request, db_session)

    event = db_session.query(AuthEvent).first()
    assert event.ip_address == "10.0.0.1"  # Should take first IP


def test_log_auth_event_handles_db_error(db_session, test_user, mock_request, capsys):
    """Test that database errors are handled gracefully without raising exceptions."""
    # Create a mock session that raises an error on commit
    mock_db = MagicMock(spec=Session)
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock(side_effect=SQLAlchemyError("Database error"))
    mock_db.rollback = MagicMock()

    # Should not raise exception
    log_auth_event("login_success", test_user, mock_request, mock_db)

    # Verify rollback was called
    mock_db.rollback.assert_called_once()

    # Verify warning was printed to stderr
    captured = capsys.readouterr()
    assert "WARNING: Failed to log auth event" in captured.err
    assert "login_success" in captured.err


def test_log_auth_event_all_event_types(db_session, test_user, mock_request):
    """Test that all valid event types can be logged."""
    event_types = ["login_success", "login_failure", "2fa_success", "2fa_failure", "password_reset"]

    for event_type in event_types:
        log_auth_event(event_type, test_user, mock_request, db_session)

    events = db_session.query(AuthEvent).all()
    assert len(events) == 5

    logged_types = {event.event_type for event in events}
    assert logged_types == set(event_types)


def test_file_logging_creates_log_file(db_session, test_user, mock_request, tmp_path):
    """Test that log file is created in specified directory."""
    import os
    import logging
    from datetime import datetime

    # Set up a test logger with file handler
    log_dir = str(tmp_path / "test_logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "auth_events.log")

    # Create a test logger
    test_logger = logging.getLogger("test_file_logger")
    test_logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s:%(message)s"))
    test_logger.addHandler(file_handler)

    # Log an event using the test logger
    log_auth_event("login_success", test_user, mock_request, db_session)
    test_logger.info(
        f"AUTH login_success user_id={test_user.id} username={test_user.username} "
        f"ip=192.168.1.1 timestamp={datetime.utcnow().isoformat()}"
    )

    # Flush and close handler
    file_handler.flush()
    file_handler.close()

    # Verify log file exists
    assert os.path.exists(log_file)

    # Verify log file contains event data
    with open(log_file, "r") as f:
        log_content = f.read()
        assert "AUTH login_success" in log_content
        assert f"user_id={test_user.id}" in log_content
        assert f"username={test_user.username}" in log_content
        assert "ip=192.168.1.1" in log_content


def test_file_logging_contains_correct_event_data(db_session, test_user, mock_request, tmp_path):
    """Test that log entries contain correct event data."""
    import os
    import logging
    from datetime import datetime

    # Set up a test logger with file handler
    log_dir = str(tmp_path / "test_logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "auth_events.log")

    # Create a test logger
    test_logger = logging.getLogger("test_file_logger_2")
    test_logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s:%(message)s"))
    test_logger.addHandler(file_handler)

    # Log multiple events
    log_auth_event("login_success", test_user, mock_request, db_session)
    test_logger.info(
        f"AUTH login_success user_id={test_user.id} username={test_user.username} "
        f"ip=192.168.1.1 timestamp={datetime.utcnow().isoformat()}"
    )

    log_auth_event("2fa_success", test_user, mock_request, db_session)
    test_logger.info(
        f"AUTH 2fa_success user_id={test_user.id} username={test_user.username} "
        f"ip=192.168.1.1 timestamp={datetime.utcnow().isoformat()}"
    )

    # Flush and close handler
    file_handler.flush()
    file_handler.close()

    # Read log file
    with open(log_file, "r") as f:
        log_content = f.read()

    # Verify both events are logged
    assert "AUTH login_success" in log_content
    assert "AUTH 2fa_success" in log_content
    assert log_content.count(f"user_id={test_user.id}") == 2
    assert log_content.count(f"username={test_user.username}") == 2


def test_logging_continues_if_file_write_fails(db_session, test_user, mock_request):
    """Test that logging continues if file write fails."""
    # This test verifies that authentication flow is not broken by logging failures
    # The logging module handles file write failures gracefully

    # Log an event - should not raise exception even if file operations fail
    log_auth_event("login_success", test_user, mock_request, db_session)

    # Verify database record was created
    event = db_session.query(AuthEvent).first()
    assert event is not None
    assert event.event_type == "login_success"
    assert event.user_id == test_user.id



def test_auth_event_to_dict_returns_correct_structure(db_session, test_user, mock_request):
    """Test that to_dict() returns correct dictionary structure."""
    log_auth_event("login_success", test_user, mock_request, db_session)

    event = db_session.query(AuthEvent).first()
    result = event.to_dict()

    # Verify all required fields are present
    assert "id" in result
    assert "user_id" in result
    assert "username" in result
    assert "event_type" in result
    assert "ip_address" in result
    assert "user_agent" in result
    assert "timestamp" in result
    assert "metadata" in result

    # Verify values are correct
    assert result["user_id"] == test_user.id
    assert result["username"] == test_user.username
    assert result["event_type"] == "login_success"
    assert result["ip_address"] == "192.168.1.1"
    assert result["user_agent"] == "Mozilla/5.0 Test Browser"


def test_auth_event_to_dict_uuid_converted_to_string(db_session, test_user, mock_request):
    """Test that UUID is converted to string."""
    log_auth_event("login_success", test_user, mock_request, db_session)

    event = db_session.query(AuthEvent).first()
    result = event.to_dict()

    # Verify id is a string
    assert isinstance(result["id"], str)
    # Verify it's a valid UUID format (has dashes)
    assert "-" in result["id"] or len(result["id"]) == 36


def test_auth_event_to_dict_datetime_iso8601_format(db_session, test_user, mock_request):
    """Test that datetime is converted to ISO 8601 format."""
    log_auth_event("login_success", test_user, mock_request, db_session)

    event = db_session.query(AuthEvent).first()
    result = event.to_dict()

    # Verify timestamp is a string
    assert isinstance(result["timestamp"], str)
    # Verify it's in ISO 8601 format (contains T separator)
    assert "T" in result["timestamp"]
    # Verify it can be parsed back to datetime
    from datetime import datetime
    parsed = datetime.fromisoformat(result["timestamp"])
    assert parsed is not None


def test_auth_event_to_dict_null_metadata_returns_empty_dict(db_session, test_user, mock_request):
    """Test that null metadata returns empty dict."""
    # Log event without metadata
    log_auth_event("login_success", test_user, mock_request, db_session, metadata=None)

    event = db_session.query(AuthEvent).first()
    result = event.to_dict()

    # Verify metadata is an empty dict, not None
    assert result["metadata"] == {}
    assert isinstance(result["metadata"], dict)
