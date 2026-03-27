

# app/schemas/user.py

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel


# ─── Register Schema ──────────────────────────────────────────────────────────
class UserRegister(SQLModel):
    # Username must be provided — no default value
    username: str
    email: str
    password: str


# ─── Login Schema ─────────────────────────────────────────────────────────────
class UserLogin(SQLModel):
    email: str # Email to identify which user is logging in
    password: str # Plain password to verify against hashed password in database



# ─── User Response Schema ─────────────────────────────────────────────────────
class UserResponse(SQLModel):
   
    id: int # Send back user id
    username: str  # Send back username
    email: str  # Send back email
    is_active: bool  # Send back account status
    created_at: datetime # Send back registration time
    


# ─── Token Schema ─────────────────────────────────────────────────────────────
class TokenResponse(SQLModel):

    access_token: str  # The JWT token client will use for future requests
    # Always 'bearer' — this is the standard token type
    # Client sends it as: Authorization: Bearer <token>
    token_type: str = "bearer"


# ─── Token Data Schema ────────────────────────────────────────────────────────
class TokenData(SQLModel):

    email: Optional[str] = None     # Email extracted from decoded JWT token
    