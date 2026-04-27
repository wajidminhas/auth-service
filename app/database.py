# app/database.py

from sqlmodel import create_engine, Session, SQLModel
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  # Set True for SQL query debugging
    pool_size=5,
    max_overflow=10
)


def create_db_and_tables() -> None:
    """Create all database tables on startup."""
    SQLModel.metadata.create_all(engine)


def get_db():
    """FastAPI dependency — provides database session per request."""
    with Session(engine) as session:
        yield session