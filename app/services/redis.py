

# app/services/redis.py

import logging
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    # Singleton pattern — one connection for entire app
    _client: redis.Redis = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        if cls._client is None:
            try:
                cls._client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True
                )
                # Test connection
                cls._client.ping()
                logger.info("Redis connected successfully")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                return None
        return cls._client

    @classmethod
    def close(cls) -> None:
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            logger.info("Redis connection closed")


def blacklist_token(token: str, expires_in: int) -> None:
    """
    Add token to blacklist when user logs out.
    Token stored in Redis with same expiry as JWT.
    After expiry Redis automatically deletes it.
    """
    client = RedisClient.get_client()
    if client:
        # Store token with expiry time
        # Key: blacklist:token_value
        # Value: "1" (just a marker)
        # expires_in: seconds until token expires
        client.setex(
            name=f"blacklist:{token}",
            time=expires_in,
            value="1"
        )
        logger.info("Token blacklisted successfully")


def is_token_blacklisted(token: str) -> bool:
    """
    Check if token is in blacklist.
    Called on every protected route request.
    Returns True if blacklisted — reject request.
    Returns False if not blacklisted — allow request.
    """
    client = RedisClient.get_client()
    if client:
        return client.exists(f"blacklist:{token}") > 0
    # If Redis is down — allow request to prevent lockout
    return False