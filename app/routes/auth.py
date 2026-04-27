# app/routes/auth.py

import logging
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.database import get_db
from app.schemas.user import (
    UserRegister, UserResponse, TokenResponse,
    ChangePasswordRequest, ForgotPasswordRequest,
    ResetPasswordRequest, UpdateProfileRequest, UserLogin
)
from app.services.auth import (
    register_user, login_user, get_current_user,
    change_password, forgot_password, reset_password,
    refresh_token, logout, update_profile, deactivate_account
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer()


def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> object:
    """Extract and validate Bearer token — returns current user."""
    return get_current_user(token=credentials.credentials, db=db)


# ═════════════════════════════════════════════════════════════════
# PUBLIC ROUTES
# ═════════════════════════════════════════════════════════════════

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register new user account."""
    return register_user(user_data=user_data, db=db)


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login with email or username — returns JWT token."""
    return login_user(user_data=user_data, db=db)


@router.post("/forgot-password")
def forgot_password_route(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request OTP for password reset."""
    return forgot_password(data=data, db=db)


@router.post("/reset-password")
def reset_password_route(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using valid OTP."""
    return reset_password(data=data, db=db)


@router.get("/health")
def health_check():
    """Service health check endpoint."""
    return {"status": "healthy", "service": "auth-service"}


# ═════════════════════════════════════════════════════════════════
# PROTECTED ROUTES
# ═════════════════════════════════════════════════════════════════

@router.get("/profile", response_model=UserResponse)
def get_profile(current_user=Depends(get_authenticated_user)):
    """Get current authenticated user profile."""
    return current_user


@router.put("/profile/update", response_model=UserResponse)
def update_profile_route(
    data: UpdateProfileRequest,
    current_user=Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    """Update profile — username, full name or phone number."""
    return update_profile(data=data, current_user=current_user, db=db)


@router.put("/change-password")
def change_password_route(
    data: ChangePasswordRequest,
    current_user=Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    """Change password after verifying current password."""
    return change_password(data=data, current_user=current_user, db=db)


@router.post("/refresh-token", response_model=TokenResponse)
def refresh_token_route(current_user=Depends(get_authenticated_user)):
    """Refresh JWT access token."""
    return refresh_token(current_user=current_user)


@router.post("/logout")
def logout_route(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user=Depends(get_authenticated_user)
):
    """Logout and blacklist current token."""
    return logout(current_user=current_user, token=credentials.credentials)


@router.put("/deactivate")
def deactivate_route(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user=Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    """Deactivate account and invalidate current token."""
    return deactivate_account(
        current_user=current_user,
        token=credentials.credentials,
        db=db
    )