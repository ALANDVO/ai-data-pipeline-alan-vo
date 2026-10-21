"""Database session and engine management."""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.app.models.database import Base
from backend.app.core.config import settings


# SQLite database file in the data volume
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "pipeline.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Create engine with SQLite optimizations
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    pool_pre_ping=True,
    echo=False,
)


# Enable WAL mode for better concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables immediately on import
Base.metadata.create_all(bind=engine)


def init_db():
    """Initialize database tables (idempotent)."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Session:
    """Get database session with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """Get database session for dependency injection."""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise