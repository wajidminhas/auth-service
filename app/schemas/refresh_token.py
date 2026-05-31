# app/schemas/refresh_token.py
from pydantic import BaseModel, ConfigDict

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    
    # ✅ Pydantic V2 config: allow serialization from dict/orm
    model_config = ConfigDict(from_attributes=True)