"""Authentication middleware and dependencies."""

from fastapi import Depends, HTTPException, status, Cookie
from typing import Optional

import sys
sys.path.append('/app/src')

from utils.auth import session_manager


async def get_current_user(session_id: Optional[str] = Cookie(None)) -> dict:
    """
    Dependency to get current authenticated user.

    Raises HTTPException if not authenticated.
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    return {"username": session['username']}


async def get_optional_user(session_id: Optional[str] = Cookie(None)) -> Optional[dict]:
    """
    Dependency to get current user if authenticated, None otherwise.

    Does not raise exception if not authenticated.
    """
    if not session_id:
        return None

    session = session_manager.get_session(session_id)

    if not session:
        return None

    return {"username": session['username']}
