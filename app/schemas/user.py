# app/schemas/user.py

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel
from pydantic import BaseModel, ConfigDict  



class UserRegister(SQLModel):
    """Registration request payload."""
    username: str
    email: str
    password: str


class UserLogin(SQLModel):
    """Login request — accepts email or username as identifier."""
    identifier: str
    password: str


class UserResponse(BaseModel):
    """Public user profile — never exposes password."""
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(SQLModel):
    """JWT token response after successful login."""
    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    """Data extracted from decoded JWT token."""
    email: Optional[str] = None


class ChangePasswordRequest(SQLModel):
    """Change password request — requires current password verification."""
    current_password: str
    new_password: str
    confirm_password: str


class ForgotPasswordRequest(SQLModel):
    """Forgot password — triggers OTP generation."""
    email: str


class ResetPasswordRequest(SQLModel):
    """Reset password using OTP received via email."""
    email: str
    otp: str
    new_password: str
    confirm_password: str


class UpdateProfileRequest(SQLModel):
    """Partial profile update — all fields optional."""
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    
