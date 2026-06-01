# app/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session
import logging

# ✅ Import from YOUR actual schema files
from app.database import get_db
from app.schemas.user import (
    UserRegister, UserLogin, UserResponse,
    ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest, UpdateProfileRequest
)
from app.schemas.refresh_token import RefreshTokenRequest, TokenResponse
from app.services.auth import AuthService, get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# ────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.get("/health", tags=["Health"])
async def health_check():
    return {"message": "Auth service is healthy"}

@router.post("/register", response_model=TokenResponse, tags=["Auth"])
async def register(payload: UserRegister, db: Session = Depends(get_db)):
    try:
        user_id, access_token, refresh_token = await AuthService.register(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            db=db
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60,
            token_type="bearer"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.error("Registration failed", exc_info=True)
        raise HTTPException(status_code=500, detail="internal_server_error")

@router.post("/login", response_model=TokenResponse, tags=["Auth"])
async def login(payload: UserLogin, db: Session = Depends(get_db)):
    try:
        # payload.identifier matches your UserLogin schema
        user_id, access_token, refresh_token = await AuthService.login(
            identifier=payload.identifier,
            password=payload.password,
            db=db
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60,
            token_type="bearer"
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception:
        logger.error("Login failed", exc_info=True)
        raise HTTPException(status_code=500, detail="internal_server_error")

@router.post("/forgot-password", tags=["Auth"])
async def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # STUB: Email/OTP service not implemented yet
    return {"message": "Password reset functionality will be available soon."}

@router.post("/reset-password", tags=["Auth"])
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    # STUB: OTP verification not implemented yet
    raise HTTPException(status_code=501, detail="Not implemented yet")

# ─────────────────────────────────────────────────────────────
# PROTECTED ENDPOINTS (Require Authentication)
# ────────────────────────────────────────────────────────────

@router.get("/profile", response_model=UserResponse, tags=["Profile"])
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/profile/update", response_model=UserResponse, tags=["Profile"])
async def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        updated_user = await AuthService.update_profile(
            user_id=current_user.id,
            updates=payload.model_dump(exclude_unset=True),
            db=db
        )
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.error("Profile update failed", exc_info=True)
        raise HTTPException(status_code=500, detail="internal_server_error")

@router.put("/change-password", tags=["Auth"])
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Maps your schema's 'current_password' to service's expected 'old_password'
        await AuthService.change_password(
            user_id=current_user.id,
            old_password=payload.current_password,
            new_password=payload.new_password,
            db=db
        )
        return {"message": "Password changed successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.error("Password change failed", exc_info=True)
        raise HTTPException(status_code=500, detail="internal_server_error")

@router.post("/logout", tags=["Auth"])
async def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        await AuthService.logout(user_id=current_user.id, db=db)
        return {"message": "Successfully logged out."}
    except Exception:
        logger.error("Logout failed", exc_info=True)
        raise HTTPException(status_code=500, detail="internal_server_error")

@router.put("/deactivate", tags=["Auth"])
async def deactivate_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        await AuthService.deactivate_account(user_id=current_user.id, db=db)
        return {"message": "Account deactivated successfully."}
    except Exception:
        logger.error("Account deactivation failed", exc_info=True)
        raise HTTPException(status_code=500, detail="internal_server_error")

@router.post("/refresh", response_model=TokenResponse, tags=["Auth"])
async def refresh_tokens(
    payload: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        user_id, new_refresh_token = await AuthService.refresh_tokens(
            raw_token=payload.refresh_token,
            db=db,
            ip_address=client_ip,
            user_agent=user_agent
        )
    except ValueError as e:
        error_map = {
            "invalid_token": ("invalid_token", 401),
            "token_reused": ("token_reused", 401),
            "token_expired": ("token_expired", 401),
        }
        error_key, status_code = error_map.get(str(e), ("internal_server_error", 500))
        raise HTTPException(status_code=status_code, detail=error_key)
    except Exception:
        logger.error("Token refresh failed", exc_info=True)
        raise HTTPException(status_code=500, detail="internal_server_error")

    access_token = AuthService.create_access_token_for_user(user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=30 * 60,
        token_type="bearer"
    )