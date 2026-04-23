# app/routes/auth.py

import logging
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.database import get_db
from app.schemas.user import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UpdateProfileRequest
)
from app.services.auth import (
    register_user,
    login_user,
    get_current_user,
    change_password,
    forgot_password,
    reset_password,
    refresh_token,
    logout,
    update_profile,
    deactivate_account
)

logger = logging.getLogger(__name__)

# ─── Router Setup ─────────────────────────────────────────────────
router = APIRouter(prefix="/auth", tags=["Authentication"])

# ─── HTTP Bearer Scheme ───────────────────────────────────────────
# HTTPBearer is cleaner than OAuth2PasswordBearer
# No client_id or client_secret fields in Swagger
# Just a clean Bearer token input
bearer_scheme = HTTPBearer()


# ─── Reusable Auth Dependency ─────────────────────────────────────
def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    # Extract token from Authorization: Bearer <token>
    return get_current_user(token=credentials.credentials, db=db)


# ═════════════════════════════════════════════════════════════════
# PUBLIC ROUTES — No token required
# ═════════════════════════════════════════════════════════════════

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user"
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    return register_user(user_data=user_data, db=db)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email or username"
)
def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    return login_user(user_data=user_data, db=db)


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Request password reset OTP"
)
def forgot_password_route(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    return forgot_password(data=data, db=db)


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset password using OTP"
)
def reset_password_route(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    return reset_password(data=data, db=db)


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check"
)
def health_check():
    return {
        "status": "healthy",
        "service": "auth-service"
    }


# ═════════════════════════════════════════════════════════════════
# PROTECTED ROUTES — Token required
# ═════════════════════════════════════════════════════════════════

@router.get(
    "/profile",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile"
)
def get_profile(
    current_user=Depends(get_authenticated_user)
):
    return current_user


@router.put(
    "/profile/update",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user profile"
)
def update_profile_route(
    data: UpdateProfileRequest,
    current_user=Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    return update_profile(data=data, current_user=current_user, db=db)


@router.put(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change password"
)
def change_password_route(
    data: ChangePasswordRequest,
    current_user=Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    return change_password(data=data, current_user=current_user, db=db)


@router.post(
    "/refresh-token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token"
)
def refresh_token_route(
    current_user=Depends(get_authenticated_user)
):
    return refresh_token(current_user=current_user)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout user"
)
def logout_route(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user=Depends(get_authenticated_user)
):
    # Pass actual token to logout for blacklisting
    return logout(current_user=current_user, token=credentials.credentials)


@router.put(
    "/deactivate",
    status_code=status.HTTP_200_OK,
    summary="Deactivate account"
)
def deactivate_route(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user=Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    # Pass actual token for blacklisting
    return deactivate_account(
        current_user=current_user,
        token=credentials.credentials,
        db=db
    )