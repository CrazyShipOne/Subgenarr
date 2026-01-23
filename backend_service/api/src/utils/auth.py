"""Authentication utilities for password hashing and session management."""

import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import sys
sys.path.append('/app/shared')

from shared import config


class PasswordHasher:
    """Simple password hasher using SHA-256."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against a hash."""
        return PasswordHasher.hash_password(password) == hashed


class SessionManager:
    """In-memory session manager."""

    def __init__(self):
        self.sessions = {}  # session_id -> {username, created_at, expires_at}
        self.session_expiry = config.SESSION_EXPIRY

    def create_session(self, username: str) -> str:
        """Create a new session for a user."""
        session_id = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.session_expiry)

        self.sessions[session_id] = {
            'username': username,
            'created_at': now,
            'expires_at': expires_at,
        }

        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data if valid."""
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]
        now = datetime.now(timezone.utc)

        # Check if expired
        if now > session['expires_at']:
            del self.sessions[session_id]
            return None

        return session

    def delete_session(self, session_id: str):
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def cleanup_expired_sessions(self):
        """Remove all expired sessions."""
        now = datetime.now(timezone.utc)
        expired_sessions = [
            sid for sid, session in self.sessions.items()
            if now > session['expires_at']
        ]

        for sid in expired_sessions:
            del self.sessions[sid]


# Global session manager instance
session_manager = SessionManager()
