# app/core/config.py

from pydantic_settings import BaseSettings
from datetime import timedelta


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # JWT - Refresh Tokens (NEW)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Trade-off: Security vs. UX
    REFRESH_TOKEN_BYTES: int = 32       # 256-bit entropy for cryptographic security
    TOKEN_PEPPER: str = ""              # Server-side secret for token hashing (optional but recommended)


    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC: str = "auth-events"

    # Redis
    REDIS_URL: str = "redis://redis:6379"

    # OTP
    OTP_EXPIRE_MINUTES: int = 15

    # App
    APP_NAME: str = "Auth Service"
    
    # Security Hardening (NEW)
    ENABLE_TOKEN_REUSE_DETECTION: bool = True
    REVOKE_FAMILY_ON_REUSE: bool = True  # Cascade revocation on reuse attack

    class Config:
        env_file = ".env"
        extra = "ignore"
        
        
    # Helper properties for timedelta consistency 
    @property
    def access_token_expire_delta(self) -> timedelta:
        return timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    @property
    def refresh_token_expire_delta(self) -> timedelta:
        return timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)
    
    

settings = Settings()