

# app/services/auth.py

import logging
from sqlmodel import Session, select
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, TokenResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token
)
from app.services.kafka import (
    publish_user_registered,
    publish_user_logged_in
)

logger = logging.getLogger(__name__)


def register_user(user_data: UserRegister, db: Session) -> User:
    """
    Handles complete user registration flow.

    Flow:
        Receive user data
            ↓
        Check email not already registered
            ↓
        Hash plain password
            ↓
        Save new user to PostgreSQL
            ↓
        Publish event to Kafka
            ↓
        Return created user
    """

    # ─── Step 1: Check if email already exists ────────────────────
    # select(User) builds a SQL SELECT query
    # where() adds WHERE clause
    # This translates to:
    # SELECT * FROM user WHERE email = 'john@example.com' LIMIT 1
    existing_user = db.exec(
        select(User).where(User.email == user_data.email)
    ).first()

    if existing_user:
        # Raise HTTP 400 Bad Request — email already taken
        # HTTPException automatically returns proper error response
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # ─── Step 2: Check if username already exists ─────────────────
    existing_username = db.exec(
        select(User).where(User.username == user_data.username)
    ).first()

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # ─── Step 3: Hash the password ────────────────────────────────
    # NEVER save plain password to database
    # hash_password() from security.py converts it to bcrypt hash
    # Example:
    #   plain:  "mypassword123"
    #   hashed: "$2b$12$KIXsV7rB..."
    hashed = hash_password(user_data.password)

    # ─── Step 4: Create User object ───────────────────────────────
    # This creates a User instance but does NOT save to database yet
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed
    )

    # ─── Step 5: Save to PostgreSQL ───────────────────────────────
    # add() stages the user for insertion
    db.add(new_user)

    # commit() executes the INSERT query and saves to database
    # After commit() new_user.id is automatically populated
    # by PostgreSQL auto increment
    db.commit()

    # refresh() reloads user data from database
    # This ensures we have latest data including auto generated id
    db.refresh(new_user)

    logger.info(f"New user registered: {new_user.email}")

    # ─── Step 6: Publish Kafka Event ──────────────────────────────
    # Notify other services that new user registered
    # This is async — does not block registration flow
    # Even if Kafka is down user is already saved to database
    publish_user_registered(
        user_id=new_user.id,
        email=new_user.email,
        username=new_user.username
    )

    return new_user


def login_user(user_data: UserLogin, db: Session) -> TokenResponse:
    """
    Handles complete user login flow.

    Flow:
        Receive email and password
            ↓
        Find user by email in database
            ↓
        Verify password against hash
            ↓
        Check account is active
            ↓
        Generate JWT token
            ↓
        Publish login event to Kafka
            ↓
        Return token to client
    """

    # ─── Step 1: Find user by email ───────────────────────────────
    # Search database for user with this email
    user = db.exec(
        select(User).where(User.email == user_data.email)
    ).first()

    # If no user found — return 401 Unauthorized
    # We say "invalid credentials" not "email not found"
    # This is intentional — never reveal if email exists
    # Security best practice — prevents email enumeration attacks
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # ─── Step 2: Verify password ──────────────────────────────────
    # verify_password() compares plain password with stored hash
    # Returns True if match, False if not
    password_valid = verify_password(
        user_data.password,
        user.hashed_password
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # ─── Step 3: Check account is active ──────────────────────────
    # Deactivated users cannot login
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support."
        )

    # ─── Step 4: Generate JWT token ───────────────────────────────
    # Create token with user email as subject
    # 'sub' is standard JWT claim meaning subject
    # Token expires based on settings.ACCESS_TOKEN_EXPIRE_MINUTES
    access_token = create_access_token(
        data={"sub": user.email}
    )

    logger.info(f"User logged in: {user.email}")

    # ─── Step 5: Publish Kafka Event ──────────────────────────────
    # Notify other services that user logged in
    # Analytics service can track login patterns
    # Security service can detect suspicious logins
    publish_user_logged_in(
        user_id=user.id,
        email=user.email
    )

    # ─── Step 6: Return token ─────────────────────────────────────
    # TokenResponse schema shapes this response
    # Client receives:
    # {
    #     "access_token": "eyJhbGci...",
    #     "token_type": "bearer"
    # }
    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )


def get_current_user(token: str, db: Session) -> User:
    """
    Validates JWT token and returns current logged in user.

    This is called on every protected route.
    Client sends token in header:
        Authorization: Bearer eyJhbGci...

    Flow:
        Receive token
            ↓
        Decode token and extract email
            ↓
        Find user by email in database
            ↓
        Return user if found and active
    """
    from app.core.security import decode_access_token

    # Decode token and get email
    email = decode_access_token(token)

    # If email is None — token is invalid or expired
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            # This header tells client to authenticate again
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Find user by email from token
    user = db.exec(
        select(User).where(User.email == email)
    ).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    return user