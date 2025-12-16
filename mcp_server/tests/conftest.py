"""
Pytest configuration for MCP Server tests.

Ensures the parent directory is in the Python path so imports work correctly.
Sets up test database isolation.
"""
import sys
import os
import tempfile
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to Python path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Set test environment variables before importing modules
# Use a temporary file database that can be shared between connections
test_db_file = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_file}"
os.environ["LOG_LEVEL"] = "ERROR"  # Reduce log noise during tests

# Import after setting environment variables
from mcp_server.base import Base
from mcp_server.db import engine, SessionLocal, get_db
from mcp_server.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Set up test database for the entire test session."""
    # Create all tables in the test database
    Base.metadata.create_all(bind=engine)
    yield
    # Clean up after all tests
    Base.metadata.drop_all(bind=engine)
    # Remove the temporary database file
    if os.path.exists(test_db_file):
        os.unlink(test_db_file)


@pytest.fixture(scope="function")
def db_session():
    """Provide a clean database session for each test."""
    # Create a new session for the test
    session = SessionLocal()
    try:
        yield session
    finally:
        # Clean up after each test
        session.rollback()

        # Clear all data from tables for next test
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()


@pytest.fixture(scope="function")
def test_client(db_session):
    """Create a test client with database dependency override."""
    from fastapi.testclient import TestClient

    def get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = get_test_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
