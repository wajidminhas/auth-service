# tests/conftest.py

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool
from unittest.mock import patch, MagicMock

from app.main import app
from app.database import get_db

TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="session")
def session_fixture():
    """Fresh SQLite database for each test."""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Test client with mocked database and disabled lifespan."""

    def get_test_db():
        yield session

    app.dependency_overrides[get_db] = get_test_db

    # Mock Redis client properly
    # is_token_blacklisted must return False (not MagicMock)
    # blacklist_token must do nothing
    with patch("app.main.create_db_and_tables"), \
         patch("app.services.kafka.KafkaEventProducer.get_producer"), \
         patch("app.services.redis.RedisClient.get_client"), \
         patch("app.services.auth.is_token_blacklisted", return_value=False), \
         patch("app.services.auth.blacklist_token", return_value=None):

        with TestClient(app) as client:
            yield client

    app.dependency_overrides.clear()


@pytest.fixture(name="test_user_data")
def test_user_data_fixture():
    """Sample user data for tests."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }


@pytest.fixture(name="registered_user")
def registered_user_fixture(client: TestClient, test_user_data: dict):
    """Register a user and return response."""
    response = client.post("/auth/register", json=test_user_data)
    return response.json()


@pytest.fixture(name="auth_token")
def auth_token_fixture(
    client: TestClient,
    test_user_data: dict,
    registered_user
):
    """Login and return JWT token."""
    response = client.post("/auth/login", json={
        "identifier": test_user_data["email"],
        "password": test_user_data["password"]
    })
    return response.json()["access_token"]


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(auth_token: str):
    """Return authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}