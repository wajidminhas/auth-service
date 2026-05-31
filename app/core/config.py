# app/core/config.py
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ─────────────────────────────────────────────────────────────
    # Application
    # ─────────────────────────────────────────────────────────────
    APP_NAME: str = "Auth Service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # ─────────────────────────────────────────────────────────────
    # JWT Configuration
    # ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # ─────────────────────────────────────────────────────────────
    # Refresh Token Security
    # ─────────────────────────────────────────────────────────────
    TOKEN_PEPPER: str = Field(..., min_length=32)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_BYTES: int = 32  # ← ADD THIS (the missing field)
    ENABLE_TOKEN_REUSE_DETECTION: bool = True
    REVOKE_FAMILY_ON_REUSE: bool = True
    
    # ─────────────────────────────────────────────────────────────
    # Database Credentials
    # ─────────────────────────────────────────────────────────────
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str  # Or compute from components below
    
    # Optional: Build URL from components if not provided directly
    # @property
    # def async_database_url(self) -> str:
    #     return self.DATABASE_URL.replace("postgresql+psycopg", "postgresql+asyncpg")
    
    # ─────────────────────────────────────────────────────────────
    # Kafka Configuration
    # ─────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:29092"
    KAFKA_TOPIC: str = "auth_events"
    
    # ─────────────────────────────────────────────────────────────
    # Redis Configuration
    # ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    
    # ─────────────────────────────────────────────────────────────
    # Email / OTP
    # ─────────────────────────────────────────────────────────────
    OTP_EXPIRE_MINUTES: int = 10
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAIL_FROM: str | None = None
    
        
    # ─────────────────────────────────────────────────────────────
    # Pydantic V2 Configuration
    # ─────────────────────────────────────────────────────────────
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        # extra="ignore",  # ← Uncomment ONLY for quick testing (NOT for production)
    )

# Instantiate settings (this is where validation happens)
settings = Settings()