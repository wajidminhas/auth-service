# app/services/redis.py

import logging
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Singleton Redis client — one connection shared across all requests."""

    _client: redis.Redis = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        """Return existing client or create new connection."""
        if cls._client is None:
            try:
                cls._client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True
                )
                cls._client.ping()
                logger.info("Redis connected")
            except Exception as e:
                logger.error(f"Redis connection error: {e}")
                return None
        return cls._client

    @classmethod
    def close(cls) -> None:
        """Close Redis connection gracefully."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            logger.info("Redis connection closed")


def blacklist_token(token: str, expires_in: int) -> None:
    """Add token to blacklist with TTL matching remaining JWT lifetime."""
    client = RedisClient.get_client()
    if client:
        client.setex(name=f"blacklist:{token}", time=expires_in, value="1")
        logger.info("Token blacklisted")


def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted. Returns False if Redis unavailable."""
    client = RedisClient.get_client()
    if client:
        return client.exists(f"blacklist:{token}") > 0
    return False