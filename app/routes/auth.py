# app/routes/auth.py

import logging
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session

from app.database import get_db
from app.schemas.user import (
    UserRegister,
    UserResponse,
    TokenResponse
)
from app.services.auth import (
    register_user,
    login_user,
    get_current_user
)

logger = logging.getLogger(__name__)

# ─── Router Setup ─────────────────────────────────────────────────────────────
# APIRouter is like a mini FastAPI app
# We group related routes together
# prefix means all routes here start with /auth
# tags groups routes in API documentation
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# ─── OAuth2 Scheme ────────────────────────────────────────────────────────────
# This tells FastAPI how client will send token
# tokenUrl is where client gets token from
# Client sends token in header like:
# Authorization: Bearer eyJhbGci...
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ─── Dependency: Get Current User ─────────────────────────────────────────────
# This dependency is used on all protected routes
# It extracts token from header and returns current user
# Any route that needs logged in user just adds:
# current_user: User = Depends(get_authenticated_user)
def get_authenticated_user(
    # OAuth2PasswordBearer extracts token from Authorization header
    # FastAPI injects this automatically
    token: str = Depends(oauth2_scheme),
    # get_db provides fresh database session
    db: Session = Depends(get_db)
):
    # get_current_user decodes token and finds user in database
    return get_current_user(token=token, db=db)


# ═════════════════════════════════════════════════════════════════════════════
# PUBLIC ROUTES — No token required
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/register",
    # What we return — FastAPI uses this to shape response
    response_model=UserResponse,
    # HTTP 201 Created is correct status for resource creation
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Creates a new user account with username, email and password"
)
def register(
    # FastAPI automatically validates incoming JSON
    # against UserRegister schema
    # If validation fails — returns 422 error automatically
    user_data: UserRegister,
    # Depends injects fresh database session automatically
    db: Session = Depends(get_db)
):
    """
    Register a new user.

    Request body:
        {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "securepassword123"
        }

    Response:
        {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com",
            "is_active": true,
            "created_at": "2024-01-01T00:00:00"
        }
    """
    logger.info(f"Register request received for email: {user_data.email}")
    # Route just calls service — no business logic here
    return register_user(user_data=user_data, db=db)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticates user and returns JWT access token"
)
def login(
    # OAuth2PasswordRequestForm is FastAPI built-in form
    # It expects form data with username and password fields
    # This is the OAuth2 standard for login
    # Client sends: username=john@example.com&password=secret
    # Note: field is called 'username' but we use it as email
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with email and password.

    Request form data:
        username: john@example.com  (we use this as email)
        password: securepassword123

    Response:
        {
            "access_token": "eyJhbGciOiJIUzI1NiIs...",
            "token_type": "bearer"
        }
    """
    logger.info(f"Login request received for: {form_data.username}")

    # OAuth2PasswordRequestForm uses 'username' field
    # We treat it as email in our UserLogin schema
    from app.schemas.user import UserLogin
    user_data = UserLogin(
        email=form_data.username,
        password=form_data.password
    )
    return login_user(user_data=user_data, db=db)


# ═════════════════════════════════════════════════════════════════════════════
# PROTECTED ROUTES — Token required
# ═════════════════════════════════════════════════════════════════════════════

@router.get(
    "/profile",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Returns profile of currently logged in user"
)
def get_profile(
    # Depends(get_authenticated_user) does three things:
    # 1. Extracts token from Authorization header
    # 2. Decodes token and gets email
    # 3. Finds and returns user from database
    # If token is missing or invalid — returns 401 automatically
    current_user=Depends(get_authenticated_user)
):
    """
    Get profile of currently logged in user.

    Requires Authorization header:
        Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

    Response:
        {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com",
            "is_active": true,
            "created_at": "2024-01-01T00:00:00"
        }
    """
    # current_user is already fetched by dependency
    # Just return it — clean and simple
    return current_user


@router.put(
    "/deactivate",
    status_code=status.HTTP_200_OK,
    summary="Deactivate user account",
    description="Deactivates currently logged in user account"
)
def deactivate_account(
    current_user=Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    """
    Deactivate current user account.

    Requires Authorization header:
        Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

    Response:
        {
            "message": "Account deactivated successfully"
        }
    """
    # Set is_active to False
    current_user.is_active = False
    db.add(current_user)
    db.commit()

    # Publish deactivation event to Kafka
    from app.services.kafka import publish_user_deactivated
    publish_user_deactivated(
        user_id=current_user.id,
        email=current_user.email
    )

    logger.info(f"Account deactivated: {current_user.email}")
    return {"message": "Account deactivated successfully"}


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if auth service is running"
)
def health_check():
    """
    Simple health check endpoint.
    Used by Docker and load balancers to verify service is running.
    No authentication required.

    Response:
        {
            "status": "healthy",
            "service": "auth-service"
        }
    """
    return {
        "status": "healthy",
        "service": "auth-service"
    }