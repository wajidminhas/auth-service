# app/core/config.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC: str = "auth-events"

    # Redis
    REDIS_URL: str = "redis://redis:6379"

    # OTP
    OTP_EXPIRE_MINUTES: int = 15

    # App
    APP_NAME: str = "Auth Service"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()