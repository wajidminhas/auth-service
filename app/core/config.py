# app/core/config.py

# pydantic-settings helps us read environment variables
# from .env file and validate them automatically
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    All application settings are defined here.
    Pydantic will automatically read these from .env file.
    If any required variable is missing it will raise an error immediately.
    """

    # ─── Database Settings ────────────────────────────────────────
    # This is the full connection string to our PostgreSQL database
    # Format: postgresql://username:password@host:port/database_name
    DATABASE_URL: str

    # ─── JWT Settings ─────────────────────────────────────────────
    # Secret key used to sign JWT tokens — keep this private always
    SECRET_KEY: str

    # Algorithm used to encode JWT tokens — HS256 is industry standard
    ALGORITHM: str = "HS256"

    # How long token stays valid — 30 minutes by default
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ─── Kafka Settings ───────────────────────────────────────────
    # Address of our Kafka broker running in Docker
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    # Topic name where we publish user events
    KAFKA_TOPIC: str = "auth-events"

    # ─── App Settings ─────────────────────────────────────────────
    # Name of our application
    APP_NAME: str = "Auth Service"

    class Config:
        # Tell pydantic where to find our environment variables
        env_file = ".env"
        # Allow extra fields without raising errors
        extra = "ignore"


# Create a single instance of Settings
# This instance is imported and used everywhere in the app
# We only create it once — this is called Singleton pattern
settings = Settings()