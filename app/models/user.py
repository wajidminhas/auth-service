# app/models/user.py

from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Relationship
# from app.models.refresh_token import RefreshToken


class User(SQLModel, table=True):
    """User account model — maps to 'user' table in PostgreSQL."""

    id: Optional[int] = Field(default=None, primary_key=True)

    # Credentials
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str

    # Profile
    full_name: Optional[str] = Field(default=None)
    phone_number: Optional[str] = Field(default=None)

    # Account state
    is_active: bool = Field(default=True)
    deactivated_by: Optional[str] = Field(default=None)
    deactivated_at: Optional[datetime] = Field(default=None)

    # Password reset
    password_reset_otp: Optional[str] = Field(default=None)
    otp_expires_at: Optional[datetime] = Field(default=None)

    # Timestamps — set automatically, never hardcoded anywhere
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)
    
    refresh_tokens: list["RefreshToken"] = Relationship(back_populates="user")
    
    
    # refresh_tokens: list["RefreshToken"] = Relationship(back_populates="user")
    if TYPE_CHECKING:
        from app.models.refresh_token import RefreshToken