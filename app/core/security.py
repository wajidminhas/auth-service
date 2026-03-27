# app/core/security.py

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional
from app.core.config import settings


# ─── Password Hashing Setup ───────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Password Functions ───────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    Takes a plain text password and returns a hashed version.
    
    Why we hash passwords?
    We NEVER store plain passwords in database.
    If database is ever hacked, attacker only sees hashed values
    which are impossible to reverse back to original password.
    
    Example:
        plain_password = "mypassword123"
        hashed = "$2b$12$KIXsV7rB1234..." (this is what gets saved)
    """
    return pwd_context.hash(plain_password)
    

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compares plain password with hashed password during login.
    
    Returns True if password matches, False if it does not.
    
    Why not just hash and compare directly?
    bcrypt adds a random 'salt' each time it hashes.
    So same password hashed twice gives different results.
    passlib handles this comparison correctly internally.
    
    Example:
        verify_password("mypassword123", "$2b$12$KIXsV7rB1234...") → True
        verify_password("wrongpassword", "$2b$12$KIXsV7rB1234...") → False
    """
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT Token Functions ──────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a JWT access token containing user data.
    
    What is JWT?
    JSON Web Token — a secure way to transmit information between
    parties as a JSON object. It is digitally signed so it cannot
    be tampered with.
    
    Structure of JWT:
        header.payload.signature
        - header: algorithm used
        - payload: data we store (user id, email etc)
        - signature: proves token was not tampered with
    
    Args:
        data: Dictionary containing user info to store in token
              Usually contains 'sub' (subject) which is user email
        expires_delta: How long token should be valid
                      If not provided uses default from settings
    
    Returns:
        Encoded JWT token string
    
    Example:
        token = create_access_token({"sub": "user@example.com"})
        # Returns: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    """
    # Copy data so we do not modify original dictionary
    to_encode = data.copy()

    # Set token expiry time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Use default expiry from settings (30 minutes)
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Add expiry time to token payload
    # 'exp' is a standard JWT claim that libraries recognize automatically
    to_encode.update({"exp": expire})

    # Encode and sign the token using our secret key
    # Only someone with SECRET_KEY can verify this token is genuine
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[str]:
    """
    Decodes a JWT token and returns the user email stored inside.
    
    This is used on protected routes to verify who is making the request.
    
    Returns user email if token is valid.
    Returns None if token is invalid or expired.
    
    Example:
        email = decode_access_token("eyJhbGciOiJIUzI1NiIs...")
        # Returns: "user@example.com"
    """
    try:
        # Decode token using our secret key
        # This also automatically checks if token is expired
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Extract email from payload
        # 'sub' stands for subject — standard JWT claim
        email: str = payload.get("sub")

        # If no email found in token it is invalid
        if email is None:
            return None

        return email

    except JWTError:
        # Token is invalid, expired or tampered with
        return None

