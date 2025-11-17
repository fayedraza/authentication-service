from sqlalchemy import create_engine, Index
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
    from .models import TOTPAttempt
    idx = Index('idx_totp_attempts_user_time', TOTPAttempt.user_id, TOTPAttempt.attempted_at)
    try:
        idx.create(bind=engine, checkfirst=True)
    except SQLAlchemyError:
        # Index may already exist
        pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
