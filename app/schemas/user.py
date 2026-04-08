# app/schemas/user.py

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel


# ─── Register Schema ──────────────────────────────────────────────
class UserRegister(SQLModel):
    username: str
    email: str
    password: str


# ─── Login Schema ─────────────────────────────────────────────────
class UserLogin(SQLModel):
    email: str
    password: str


# ─── User Response Schema ─────────────────────────────────────────
# What we send back to client — never includes password
class UserResponse(SQLModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: bool
    created_at: datetime


# ─── Token Schema ─────────────────────────────────────────────────
class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"


# ─── Token Data Schema ────────────────────────────────────────────
class TokenData(SQLModel):
    email: Optional[str] = None


# ─── Change Password Schema ───────────────────────────────────────
class ChangePasswordRequest(SQLModel):
    current_password: str
    new_password: str
    confirm_password: str


# ─── Forgot Password Schema ───────────────────────────────────────
class ForgotPasswordRequest(SQLModel):
    email: str


# ─── Reset Password Schema ────────────────────────────────────────
class ResetPasswordRequest(SQLModel):
    email: str
    otp: str
    new_password: str
    confirm_password: str


# ─── Update Profile Schema ────────────────────────────────────────
# All fields optional — user updates only what they want
class UpdateProfileRequest(SQLModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None