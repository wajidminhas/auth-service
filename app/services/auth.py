# app/services/auth.py

import secrets
import logging
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from fastapi import Depends, HTTPException, status
from jose import jwt

from app.database import get_db
from app.models.user import User
from app.refresh_token_service import RefreshTokenService
from app.schemas.user import (
    UserRegister, UserLogin, TokenResponse,
    ChangePasswordRequest, ForgotPasswordRequest,
    ResetPasswordRequest, UpdateProfileRequest
)
from app.core.security import (
    hash_password, verify_password,
    create_access_token, decode_access_token
)
from app.core.config import settings
from app.services.redis import blacklist_token, is_token_blacklisted
from app.services.kafka import (
    publish_user_registered, publish_user_logged_in,
    publish_user_logged_out, publish_user_deactivated,
    publish_password_changed, publish_password_reset_requested,
    publish_password_reset_completed, publish_token_refreshed,
    publish_profile_updated
)

logger = logging.getLogger(__name__)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")



# ─── Helpers ──────────────────────────────────────────────────────

def get_user_by_email(email: str, db: Session) -> User | None:
    """Fetch user by email address."""
    return db.exec(select(User).where(User.email == email)).first()


def get_user_by_username(username: str, db: Session) -> User | None:
    """Fetch user by username."""
    return db.exec(select(User).where(User.username == username)).first()


def _save(user: User, db: Session) -> User:
    """Persist user changes and refresh from database."""
    user.updated_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_token_remaining_seconds(token: str) -> int:
    """Return remaining seconds until token expires. Returns 0 if expired."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        exp = payload.get("exp", 0)
        from datetime import timezone
        remaining = int(exp - datetime.now(timezone.utc).timestamp())
        return max(remaining, 0)
    except Exception:
        return 0


# ─── Register ─────────────────────────────────────────────────────

def register_user(user_data: UserRegister, db: Session) -> User:
    """
    Register new user account.

    Raises:
        400: Email or username already taken
    """
    if get_user_by_email(user_data.email, db):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    if get_user_by_username(user_data.username, db):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already taken")

    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"User registered: {user.email}")
    publish_user_registered(user.id, user.email, user.username)
    return user


# ─── Login ────────────────────────────────────────────────────────

def login_user(user_data: UserLogin, db: Session) -> TokenResponse:
    """
    Authenticate user with email or username and return JWT token.

    Raises:
        401: Invalid credentials
        403: Account deactivated
    """
    user = get_user_by_email(user_data.identifier, db)
    if not user:
        user = get_user_by_username(user_data.identifier, db)

    # Never reveal which field was wrong — security best practice
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")

    token = create_access_token(data={"sub": user.email})
    logger.info(f"User logged in: {user.email}")
    publish_user_logged_in(user.id, user.email)
    return TokenResponse(access_token=token, token_type="bearer")


# ─── Get Current User ─────────────────────────────────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),  # ← pulls Bearer token from request
    db: Session = Depends(get_db)    # ← injects DB session
) -> User:
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalidated — please login again",
            headers={"WWW-Authenticate": "Bearer"}
        )

    email = decode_access_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = get_user_by_email(email, db)
    if not user:
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


# ─── Change Password ──────────────────────────────────────────────

def change_password(
    data: ChangePasswordRequest,
    current_user: User,
    db: Session
) -> dict:
    """
    Change user password after verifying current password.

    Raises:
        400: Current password wrong, passwords don't match, or same password
        422: Password too short
    """
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")

    if data.new_password != data.confirm_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passwords do not match")

    if verify_password(data.new_password, current_user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "New password must differ from current")

    if len(data.new_password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Password must be at least 8 characters")

    current_user.hashed_password = hash_password(data.new_password)
    _save(current_user, db)

    logger.info(f"Password changed: {current_user.email}")
    publish_password_changed(current_user.id, current_user.email)
    return {"message": "Password changed successfully"}


# ─── Forgot Password ──────────────────────────────────────────────

def forgot_password(data: ForgotPasswordRequest, db: Session) -> dict:
    """
    Generate OTP for password reset and store with 15 min expiry.

    Raises:
        404: Email not found
    """
    user = get_user_by_email(data.email, db)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Email not found")

    otp = str(secrets.randbelow(900000) + 100000)
    user.password_reset_otp = otp
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    _save(user, db)

    logger.info(f"OTP generated: {user.email}")
    publish_password_reset_requested(user.id, user.email)

    # TODO: Send OTP via email in production
    return {"message": "OTP sent to your email", "otp": otp}


# ─── Reset Password ───────────────────────────────────────────────

def reset_password(data: ResetPasswordRequest, db: Session) -> dict:
    """
    Reset password using valid OTP.

    Raises:
        404: Email not found
        400: Invalid/expired OTP or passwords don't match
        422: Password too short
    """
    user = get_user_by_email(data.email, db)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Email not found")

    if not user.password_reset_otp or user.password_reset_otp != data.otp:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid OTP")

    # Handle both naive and aware datetimes for SQLite compatibility
    now = datetime.now(timezone.utc)
    otp_expiry = user.otp_expires_at

    # If otp_expiry is naive datetime — make it aware for comparison
    if otp_expiry and otp_expiry.tzinfo is None:
        from datetime import timezone as tz
        otp_expiry = otp_expiry.replace(tzinfo=timezone.utc)

    if otp_expiry and now > otp_expiry:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OTP expired — request a new one")

    if data.new_password != data.confirm_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passwords do not match")

    if len(data.new_password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Password must be at least 8 characters")

    user.hashed_password = hash_password(data.new_password)
    user.password_reset_otp = None
    user.otp_expires_at = None
    _save(user, db)

    logger.info(f"Password reset: {user.email}")
    publish_password_reset_completed(user.id, user.email)
    return {"message": "Password reset successfully"}


# ─── Refresh Token ────────────────────────────────────────────────

def refresh_token(current_user: User) -> TokenResponse:
    """Generate new access token for authenticated user."""
    token = create_access_token(data={"sub": current_user.email})
    logger.info(f"Token refreshed: {current_user.email}")
    publish_token_refreshed(current_user.id, current_user.email)
    return TokenResponse(access_token=token, token_type="bearer")


# ─── Logout ───────────────────────────────────────────────────────

def logout(current_user: User, token: str) -> dict:
    """Blacklist current token and publish logout event."""
    expires_in = _get_token_remaining_seconds(token)
    if expires_in > 0:
        blacklist_token(token, expires_in)

    logger.info(f"User logged out: {current_user.email}")
    publish_user_logged_out(current_user.id, current_user.email)
    return {"message": "Logged out successfully"}


# ─── Update Profile ───────────────────────────────────────────────

def update_profile(
    data: UpdateProfileRequest,
    current_user: User,
    db: Session
) -> User:
    """
    Partial profile update — only updates provided fields.

    Raises:
        400: Username already taken
        422: Invalid phone number format
    """
    if data.username and data.username != current_user.username:
        if get_user_by_username(data.username, db):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already taken")
        current_user.username = data.username

    if data.phone_number:
        phone = data.phone_number.replace("+", "").replace("-", "").replace(" ", "")
        if not phone.isdigit() or not (10 <= len(phone) <= 15):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid phone number format")
        current_user.phone_number = data.phone_number

    if data.full_name:
        current_user.full_name = data.full_name

    _save(current_user, db)
    logger.info(f"Profile updated: {current_user.email}")
    publish_profile_updated(current_user.id, current_user.email)
    return current_user


# ─── Deactivate Account ───────────────────────────────────────────

def deactivate_account(
    current_user: User,
    token: str,
    db: Session
) -> dict:
    """
    Deactivate account and blacklist current token.

    Raises:
        400: Account already deactivated
    """
    if not current_user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Account already deactivated")

    current_user.is_active = False
    current_user.deactivated_by = "user"
    current_user.deactivated_at = datetime.now(timezone.utc)
    _save(current_user, db)

    expires_in = _get_token_remaining_seconds(token)
    if expires_in > 0:
        blacklist_token(token, expires_in)

    logger.info(f"Account deactivated: {current_user.email}")
    publish_user_deactivated(current_user.id, current_user.email)
    return {"message": "Account deactivated successfully"}


class AuthService:
    """Facade that coordinates JWT and Refresh Token services."""

    @staticmethod
    async def refresh_tokens(
        raw_token: str,
        db: Session,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> tuple[int, str]:
        """Delegates validation/rotation to RefreshTokenService."""
        return await RefreshTokenService.validate_and_rotate(
            raw_token=raw_token,
            db=db,
            ip_address=ip_address,
            user_agent=user_agent
        )
    @staticmethod
    def create_access_token_for_user(user_id: int) -> str:
        """Generates a short-lived JWT for the authenticated user."""
        return create_access_token(
            data={"sub": str(user_id)},
            expires_delta=settings.access_token_expire_delta
        )