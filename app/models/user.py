# app/models/user.py

from typing import Optional
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Login credentials
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str

    # Profile info
    full_name: Optional[str] = Field(default=None)
    phone_number: Optional[str] = Field(default=None)

    # Account status
    is_active: bool = Field(default=True)

    # Password reset fields
    # Stores OTP code when user requests password reset
    password_reset_otp: Optional[str] = Field(default=None)
    # Stores when OTP expires — 15 minutes after generation
    otp_expires_at: Optional[datetime] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)