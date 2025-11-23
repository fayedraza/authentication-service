"""Tests for database initialization."""
import pytest
from sqlalchemy import inspect, create_engine
from sqlalchemy.orm import sessionmaker
import os
import tempfile

from auth_platform.auth_platform.auth_service.db import Base, init_db
from auth_platform.auth_platform.auth_service.models import AuthEvent, User, TOTPAttempt


def test_init_db_creates_auth_events_table():
    """Test that init_db creates the auth_events table with all required columns."""
    # Create a temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        tmp_db_path = tmp.name

    try:
        # Create engine and initialize database
        test_engine = create_engine(f"sqlite:///{tmp_db_path}", connect_args={"check_same_thread": False})

        # Temporarily override the engine in the db module
        import auth_platform.auth_platform.auth_service.db as db_module
        original_engine = db_module.engine
        db_module.engine = test_engine
        db_module.Base.metadata.bind = test_engine

        # Initialize database
        init_db()

        # Inspect the database
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()

        # Verify auth_events table exists
        assert 'auth_events' in tables, "auth_events table should be created"

        # Verify all required columns exist
        columns = {col['name']: col for col in inspector.get_columns('auth_events')}
        required_columns = ['id', 'user_id', 'username', 'event_type', 'ip_address',
                          'user_agent', 'timestamp', 'event_metadata']

        for col_name in required_columns:
            assert col_name in columns, f"Column {col_name} should exist in auth_events table"

        # Verify column types
        assert columns['id']['type'].__class__.__name__ in ['VARCHAR', 'STRING'], "id should be string (UUID)"
        assert columns['user_id']['type'].__class__.__name__ == 'INTEGER', "user_id should be integer"
        assert columns['username']['type'].__class__.__name__ in ['VARCHAR', 'STRING'], "username should be string"
        assert columns['event_type']['type'].__class__.__name__ in ['VARCHAR', 'STRING', 'ENUM'], "event_type should be enum/string"
        assert columns['timestamp']['type'].__class__.__name__ == 'DATETIME', "timestamp should be datetime"

        # Verify nullable constraints
        assert columns['id']['nullable'] is False, "id should not be nullable"
        assert columns['user_id']['nullable'] is False, "user_id should not be nullable"
        assert columns['username']['nullable'] is False, "username should not be nullable"
        assert columns['event_type']['nullable'] is False, "event_type should not be nullable"
        assert columns['ip_address']['nullable'] is True, "ip_address should be nullable"
        assert columns['user_agent']['nullable'] is True, "user_agent should be nullable"
        assert columns['timestamp']['nullable'] is False, "timestamp should not be nullable"

        # Restore original engine
        db_module.engine = original_engine
        db_module.Base.metadata.bind = original_engine

    finally:
        # Clean up temporary database
        if os.path.exists(tmp_db_path):
            os.unlink(tmp_db_path)


def test_init_db_creates_auth_events_indexes():
    """Test that init_db creates all required indexes for auth_events table."""
    # Create a temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        tmp_db_path = tmp.name

    try:
        # Create engine and initialize database
        test_engine = create_engine(f"sqlite:///{tmp_db_path}", connect_args={"check_same_thread": False})

        # Temporarily override the engine in the db module
        import auth_platform.auth_platform.auth_service.db as db_module
        original_engine = db_module.engine
        db_module.engine = test_engine
        db_module.Base.metadata.bind = test_engine

        # Initialize database
        init_db()

        # Inspect the database
        inspector = inspect(test_engine)
        indexes = inspector.get_indexes('auth_events')
        index_names = [idx['name'] for idx in indexes]

        # Verify required indexes exist
        required_indexes = [
            'ix_auth_events_user_id',
            'ix_auth_events_timestamp',
            'ix_auth_events_event_type',
            'ix_auth_events_user_id_timestamp'
        ]

        for idx_name in required_indexes:
            assert idx_name in index_names, f"Index {idx_name} should be created"

        # Verify composite index structure
        composite_idx = next((idx for idx in indexes if idx['name'] == 'ix_auth_events_user_id_timestamp'), None)
        assert composite_idx is not None, "Composite index should exist"
        assert 'user_id' in composite_idx['column_names'], "Composite index should include user_id"
        assert 'timestamp' in composite_idx['column_names'], "Composite index should include timestamp"

        # Restore original engine
        db_module.engine = original_engine
        db_module.Base.metadata.bind = original_engine

    finally:
        # Clean up temporary database
        if os.path.exists(tmp_db_path):
            os.unlink(tmp_db_path)


def test_init_db_creates_foreign_key_constraint():
    """Test that auth_events table has foreign key constraint to users table."""
    # Create a temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        tmp_db_path = tmp.name

    try:
        # Create engine and initialize database
        test_engine = create_engine(f"sqlite:///{tmp_db_path}", connect_args={"check_same_thread": False})

        # Temporarily override the engine in the db module
        import auth_platform.auth_platform.auth_service.db as db_module
        original_engine = db_module.engine
        db_module.engine = test_engine
        db_module.Base.metadata.bind = test_engine

        # Initialize database
        init_db()

        # Inspect the database
        inspector = inspect(test_engine)
        foreign_keys = inspector.get_foreign_keys('auth_events')

        # Verify foreign key exists
        assert len(foreign_keys) > 0, "auth_events should have at least one foreign key"

        # Find the foreign key to users table
        user_fk = next((fk for fk in foreign_keys if fk['referred_table'] == 'users'), None)
        assert user_fk is not None, "Foreign key to users table should exist"
        assert 'user_id' in user_fk['constrained_columns'], "Foreign key should be on user_id column"

        # Restore original engine
        db_module.engine = original_engine
        db_module.Base.metadata.bind = original_engine

    finally:
        # Clean up temporary database
        if os.path.exists(tmp_db_path):
            os.unlink(tmp_db_path)
