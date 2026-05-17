# app/core/security.py
import secrets
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash plain password using bcrypt."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generate signed JWT token with expiry."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def decode_access_token(token: str) -> Optional[str]:
    """Decode JWT token and return email. Returns None if invalid or expired."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload.get("sub")
    except JWTError:
        return None
    


# ─────────────────────────────────────────────────────────────
# Refresh Token Utilities (Rotation Support)
# ─────────────────────────────────────────────────────────────

def generate_refresh_token() -> str:
    """
    Generate a cryptographically secure refresh token.
    
    Returns:
        str: URL-safe, high-entropy token string (default 256-bit)
    
    Security Note:
        - Uses secrets.token_urlsafe() for cryptographic randomness
        - Token is opaque (not JWT) to enable instant revocation
        - Length configurable via REFRESH_TOKEN_BYTES setting
    """
    return secrets.token_urlsafe(settings.REFRESH_TOKEN_BYTES)

def hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token for secure storage using SHA-256 + optional pepper.
    
    Args:
        token: Raw refresh token string
        
    Returns:
        str: Hexadecimal hash string (64 characters for SHA-256)
    
    Security Rationale:
        - SHA-256 is sufficient for high-entropy tokens (unlike passwords)
        - HMAC with pepper adds server-side secret protection
        - Never store raw tokens; hash before any database interaction
    """
    if settings.TOKEN_PEPPER:
        # Use HMAC for peppered hashing (constant-time comparison safe)
        return hmac.new(
            key=settings.TOKEN_PEPPER.encode(),
            msg=token.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
    else:
        # Simple SHA-256 hash if no pepper configured
        return hashlib.sha256(token.encode()).hexdigest()


def verify_refresh_token(token: str, token_hash: str) -> bool:
    """
    Verify a raw token against its stored hash using constant-time comparison.
    
    Args:
        token: Raw refresh token provided by client
        token_hash: Hashed token retrieved from database
        
    Returns:
        bool: True if token matches hash, False otherwise
    
    Security Note:
        - Uses hmac.compare_digest() to prevent timing attacks
        - Critical for authentication endpoints exposed to network
    """
    computed_hash = hash_refresh_token(token)
    return hmac.compare_digest(computed_hash, token_hash)

def get_token_expiry() -> datetime:
    """
    Calculate refresh token expiration timestamp.
    
    Returns:
        datetime: UTC timestamp when token should expire
    """
    return datetime.now(timezone.utc) + settings.refresh_token_expire_delta


def is_token_expired(expires_at: datetime) -> bool:
    """
    Check if a token has expired.
    
    Args:
        expires_at: Token expiration timestamp (UTC)
        
    Returns:
        bool: True if expired, False otherwise
    """
    return datetime.now(timezone.utc) > expires_at


