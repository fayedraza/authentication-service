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
