
# tests/conftest.py

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_db


# ─── Test Database Setup ──────────────────────────────────────────
# Use SQLite in memory for testing
# Why SQLite?
# → No need to run PostgreSQL for tests
# → Creates fresh database for every test run
# → Fast and lightweight
# → Tests stay isolated from real data

TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    # StaticPool keeps same connection for entire test
    # Required for in-memory SQLite
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# ─── Fixtures ─────────────────────────────────────────────────────
# Fixtures are reusable setup functions
# pytest injects them automatically into test functions
# Just add fixture name as parameter — pytest handles rest

@pytest.fixture(name="session")
def session_fixture():
    """
    Creates fresh database tables before each test
    Drops all tables after each test
    Every test gets clean empty database
    """
    # Create all tables
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    # Drop all tables after test — clean slate
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """
    Creates test HTTP client with test database injected.

    Why override get_db?
    Our app normally uses PostgreSQL via get_db()
    For tests we replace it with our SQLite test session
    This is dependency injection in action!
    """
    def get_test_db():
        yield session

    # Override real database with test database
    app.dependency_overrides[get_db] = get_test_db

    # TestClient lets us make HTTP requests without running server
    with TestClient(app) as client:
        yield client

    # Clean up overrides after test
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user_data")
def test_user_data_fixture():
    """
    Returns sample user data for registration tests
    Using fixed data makes tests predictable
    """
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }


@pytest.fixture(name="registered_user")
def registered_user_fixture(client: TestClient, test_user_data: dict):
    """
    Registers a user and returns response
    Used by tests that need an existing user
    """
    response = client.post("/auth/register", json=test_user_data)
    return response.json()


@pytest.fixture(name="auth_token")
def auth_token_fixture(client: TestClient, test_user_data: dict, registered_user):
    """
    Registers user, logs in and returns JWT token
    Used by tests that need authenticated user
    """
    response = client.post("/auth/login", json={
        "identifier": test_user_data["email"],
        "password": test_user_data["password"]
    })
    return response.json()["access_token"]


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(auth_token: str):
    """
    Returns authorization headers with Bearer token
    Used by protected route tests
    """
    return {"Authorization": f"Bearer {auth_token}"}