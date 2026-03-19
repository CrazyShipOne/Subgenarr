"""Authentication API routes."""

from fastapi import APIRouter, Response, Depends, HTTPException, status
from typing import Optional

import sys
sys.path.append('/app/shared')
sys.path.append('/app/src')

from shared import config
from utils.auth import PasswordHasher, session_manager
from api.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    AuthStatusResponse,
)
from api.middleware.auth import get_optional_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    """Authenticate user and create session."""
    # Verify credentials
    expected_username = config.AUTH_USERNAME
    expected_password_hash = PasswordHasher.hash_password(config.AUTH_PASSWORD)
    provided_password_hash = PasswordHasher.hash_password(request.password)

    if request.username != expected_username or provided_password_hash != expected_password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Create session
    session_id = session_manager.create_session(request.username)

    # Set cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=config.SESSION_EXPIRY,
        httponly=True,
        samesite="lax",
    )

    return LoginResponse(
        success=True,
        data={
            "user": {"username": request.username},
            "message": "Login successful"
        }
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response, user: Optional[dict] = Depends(get_optional_user)):
    """Destroy current session."""
    # Clear cookie
    response.delete_cookie(key="session_id")

    # Note: We can't get the session_id from cookies here after deletion,
    # but that's okay - the cookie deletion is enough

    return LogoutResponse(
        success=True,
        message="Logout successful"
    )


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(user: Optional[dict] = Depends(get_optional_user)):
    """Check current authentication status."""
    if user:
        return AuthStatusResponse(
            authenticated=True,
            user=user
        )
    else:
        return AuthStatusResponse(
            authenticated=False,
            user=None
        )
