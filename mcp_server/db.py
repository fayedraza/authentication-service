"""
Database connection and session management for MCP Server
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

from mcp_server.config import settings
from mcp_server.base import Base
from mcp_server.models import MCPAuthEvent, MCPAlert

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
if "sqlite" in settings.DATABASE_URL:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.LOG_LEVEL == "DEBUG"
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        echo=settings.LOG_LEVEL == "DEBUG"
    )

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database by creating all tables.
    Should be called on application startup.
    """
    try:
        # Models are already imported at module level
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def check_db_connection() -> bool:
    """
    Check if database connection is working.

    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
