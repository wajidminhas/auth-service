

from typing import Optional
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Relationship
import uuid
from .user import User

class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE", index=True)

    # Core rotation fields
    token_hash: str = Field(max_length=64, unique=True, index=True)
    family_id: Optional[uuid.UUID] = Field(default=None, index=True)

    # Audit & security metadata
    created_ip: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=512)

    # Lifecycle tracking
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    used_at: Optional[datetime] = Field(default=None)
    revoked_at: Optional[datetime] = Field(default=None)
    revoked_reason: Optional[str] = Field(default=None, max_length=200)

    user: Optional["User"] = Relationship(back_populates="refresh_tokens")