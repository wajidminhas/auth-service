# app/database.py

# SQLModel combines SQLAlchemy and Pydantic in one package
# create_engine creates our database connection
from sqlmodel import create_engine, Session, SQLModel

# Import our settings to get DATABASE_URL
from app.core.config import settings


# ─── Database Engine ──────────────────────────────────────────────────────────
# Engine is the core connection to our PostgreSQL database
# It manages a connection pool so we do not create
# a new connection on every single request — that would be slow
engine = create_engine(
    settings.DATABASE_URL,
    # Print all SQL queries in terminal
    # Very helpful during development to see what is happening
    # Always set this to False in production
    echo=True,
    # How many connections to keep ready in pool
    pool_size=5,
    # Extra connections allowed when pool is full
    max_overflow=10
)


# ─── Create Tables ────────────────────────────────────────────────────────────
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# ─── Database Session ─────────────────────────────────────────────────────────
def get_db():
   
    # 'with' block automatically closes session when done
    # even if an error occurs inside the route
    with Session(engine) as session:
        yield session