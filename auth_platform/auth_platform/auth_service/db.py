from sqlalchemy import create_engine, Index, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)

    # Create index for TOTP attempts if not exists
    from .models import TOTPAttempt, AuthEvent  # Import here to avoid circular dependency
    inspector = inspect(engine)

    # TOTP attempts index
    existing_totp_indexes = [idx['name'] for idx in inspector.get_indexes('totp_attempts')]
    if 'idx_totp_attempts_user_time' not in existing_totp_indexes:
        idx = Index('idx_totp_attempts_user_time', TOTPAttempt.user_id, TOTPAttempt.attempted_at)
        try:
            idx.create(bind=engine)
        except SQLAlchemyError:
            # Index may already exist (race condition)
            pass

    # AuthEvent indexes (already defined in model __table_args__, but verify creation)
    # The indexes are: ix_auth_events_user_id, ix_auth_events_timestamp,
    # ix_auth_events_event_type, ix_auth_events_user_id_timestamp
    # These are automatically created by Base.metadata.create_all() above

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
