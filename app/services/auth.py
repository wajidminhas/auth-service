# app/services/auth.py

import secrets
import logging
from datetime import datetime, timedelta
from sqlmodel import Session, select
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.user import (
    UserRegister,
    UserLogin,
    TokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UpdateProfileRequest
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)
from app.core.config import settings
from app.services.kafka import (
    publish_user_registered,
    publish_user_logged_in,
    publish_user_logged_out,
    publish_user_deactivated,
    publish_password_changed,
    publish_password_reset_requested,
    publish_password_reset_completed,
    publish_token_refreshed,
    publish_profile_updated
)

logger = logging.getLogger(__name__)


# ─── Helper ───────────────────────────────────────────────────────
def get_user_by_email(email: str, db: Session):
    return db.exec(select(User).where(User.email == email)).first()

def get_user_by_username(username: str, db: Session):
    return db.exec(select(User).where(User.username == username)).first()


# ─── Register ─────────────────────────────────────────────────────
def register_user(user_data: UserRegister, db: Session) -> User:

    # Check email not already taken
    if get_user_by_email(user_data.email, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check username not already taken
    if get_user_by_username(user_data.username, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Create and save new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"New user registered: {new_user.email}")
    publish_user_registered(new_user.id, new_user.email, new_user.username)

    return new_user


# ─── Login ────────────────────────────────────────────────────────
def login_user(user_data: UserLogin, db: Session) -> TokenResponse:

    user = get_user_by_email(user_data.email, db)

    # Never reveal if email exists or not — security best practice
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    token = create_access_token(data={"sub": user.email})

    logger.info(f"User logged in: {user.email}")
    publish_user_logged_in(user.id, user.email)

    return TokenResponse(access_token=token, token_type="bearer")


# ─── Get Current User ─────────────────────────────────────────────
def get_current_user(token: str, db: Session) -> User:

    email = decode_access_token(token)

    if email is None:
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

    # Verify current password is correct
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # New password and confirm must match
    if data.new_password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match"
        )

    # New password must be different from current
    if verify_password(data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )

    # Minimum 8 characters
    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters"
        )

    # Hash and save new password
    current_user.hashed_password = hash_password(data.new_password)
    current_user.updated_at = datetime.utcnow()
    db.add(current_user)
    db.commit()

    logger.info(f"Password changed: {current_user.email}")
    publish_password_changed(current_user.id, current_user.email)

    return {"message": "Password changed successfully"}


# ─── Forgot Password ──────────────────────────────────────────────
def forgot_password(data: ForgotPasswordRequest, db: Session) -> dict:

    user = get_user_by_email(data.email, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )

    # Generate secure 6 digit OTP
    # secrets module is more secure than random for OTPs
    otp = str(secrets.randbelow(900000) + 100000)

    # Store OTP and expiry in database
    user.password_reset_otp = otp
    user.otp_expires_at = datetime.utcnow() + timedelta(
        minutes=settings.OTP_EXPIRE_MINUTES
    )
    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()

    logger.info(f"Password reset OTP generated: {user.email}")
    publish_password_reset_requested(user.id, user.email)

    # In production — send OTP via email
    # For development — return OTP in response
    return {
        "message": "Password reset OTP sent to your email",
        "otp": otp  # Remove this in production!
    }


# ─── Reset Password ───────────────────────────────────────────────
def reset_password(data: ResetPasswordRequest, db: Session) -> dict:

    user = get_user_by_email(data.email, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )

    # Check OTP exists and matches
    if not user.password_reset_otp or user.password_reset_otp != data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )

    # Check OTP not expired
    if datetime.utcnow() > user.otp_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one."
        )

    # Passwords must match
    if data.new_password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    # Minimum 8 characters
    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters"
        )

    # Save new password and clear OTP
    user.hashed_password = hash_password(data.new_password)
    user.password_reset_otp = None
    user.otp_expires_at = None
    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()

    logger.info(f"Password reset completed: {user.email}")
    publish_password_reset_completed(user.id, user.email)

    return {"message": "Password reset successfully"}


# ─── Refresh Token ────────────────────────────────────────────────
def refresh_token(current_user: User) -> TokenResponse:

    # Generate fresh token for already authenticated user
    new_token = create_access_token(data={"sub": current_user.email})

    logger.info(f"Token refreshed: {current_user.email}")
    publish_token_refreshed(current_user.id, current_user.email)

    return TokenResponse(access_token=new_token, token_type="bearer")


# ─── Logout ───────────────────────────────────────────────────────
def logout(current_user: User) -> dict:

    # JWT is stateless — actual token deletion happens client side
    # We just publish event so other services know user logged out
    logger.info(f"User logged out: {current_user.email}")
    publish_user_logged_out(current_user.id, current_user.email)

    return {"message": "Logged out successfully"}


# ─── Update Profile ───────────────────────────────────────────────
def update_profile(
    data: UpdateProfileRequest,
    current_user: User,
    db: Session
) -> User:

    # Check new username not taken by another user
    if data.username and data.username != current_user.username:
        existing = get_user_by_username(data.username, db)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        current_user.username = data.username

    # Validate phone number format — 10 to 15 digits
    if data.phone_number:
        phone = data.phone_number.replace("+", "").replace("-", "").replace(" ", "")
        if not phone.isdigit() or not (10 <= len(phone) <= 15):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid phone number format"
            )
        current_user.phone_number = data.phone_number

    # Update full name if provided
    if data.full_name:
        current_user.full_name = data.full_name

    current_user.updated_at = datetime.utcnow()
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    logger.info(f"Profile updated: {current_user.email}")
    publish_profile_updated(current_user.id, current_user.email)

    return current_user


# ─── Deactivate Account ───────────────────────────────────────────
def deactivate_account(current_user: User, db: Session) -> dict:

    current_user.is_active = False
    current_user.updated_at = datetime.utcnow()
    db.add(current_user)
    db.commit()

    logger.info(f"Account deactivated: {current_user.email}")
    publish_user_deactivated(current_user.id, current_user.email)

    return {"message": "Account deactivated successfully"}
