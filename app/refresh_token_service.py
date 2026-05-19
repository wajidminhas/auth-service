

import uuid
from datetime import datetime, timezone
from sqlmodel import Session, select
from models.refresh_token import RefreshToken
from app.core.security import (
    generate_refresh_token,
    hash_refresh_token,
    get_token_expiry,
    is_token_expired
)
from app.core.config import settings
from fastapi import HTTPException


class RefreshTokenService:
    @staticmethod
    def create_for_user(
        user_id: int,
        db: Session,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> str:
        raw_token = generate_refresh_token()
        token_hash = hash_refresh_token(raw_token)

        record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            family_id=uuid.uuid4(),
            created_ip=ip_address,
            user_agent=user_agent,
            expires_at=get_token_expiry()
        )
        db.add(record)
        db.commit()
        return raw_token

    @staticmethod
    def validate_and_rotate(
        raw_token: str,
        db: Session,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> tuple[int, str]:
        token_hash = hash_refresh_token(raw_token)

        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        record = db.exec(stmt).first()

        if not record:
            raise HTTPException(status_code=401, detail="invalid_token")
        if record.revoked_at:
            raise HTTPException(status_code=401, detail="token_revoked")
        if is_token_expired(record.expires_at):
            raise HTTPException(status_code=401, detail="token_expired")
        if record.used_at:
            RefreshTokenService.revoke_family(record.family_id, db, reason="reuse_detected")
            raise HTTPException(status_code=401, detail="token_reused")

        record.used_at = datetime.now(timezone.utc)
        
        new_raw = generate_refresh_token()
        new_record = RefreshToken(
            user_id=record.user_id,
            token_hash=hash_refresh_token(new_raw),
            family_id=record.family_id,
            created_ip=ip_address,
            user_agent=user_agent,
            expires_at=get_token_expiry()
        )
        db.add(new_record)
        db.commit()

        return record.user_id, new_raw

    @staticmethod
    def revoke_family(family_id: uuid.UUID, db: Session, reason: str = "security_incident") -> int:
        stmt = select(RefreshToken).where(RefreshToken.family_id == family_id)
        records = db.exec(stmt).all()
        
        now = datetime.now(timezone.utc)
        revoked_count = 0
        for r in records:
            if not r.revoked_at:
                r.revoked_at = now
                r.revoked_reason = reason
                revoked_count += 1
                
        db.commit()
        return revoked_count