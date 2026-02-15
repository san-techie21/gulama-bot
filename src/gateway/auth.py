"""
Authentication for Gulama gateway — TOTP + session tokens.

All API requests to the gateway must be authenticated:
- TOTP (Time-based One-Time Password) for initial auth
- Session tokens for subsequent requests
- Sessions expire after configurable timeout
- No persistent cookies — session tokens only
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field

import pyotp

from src.utils.logging import get_logger

logger = get_logger("auth")

# Session token length (256-bit)
TOKEN_BYTES = 32


@dataclass
class Session:
    """An authenticated session."""

    token: str
    created_at: float
    last_active: float
    user_agent: str = ""


@dataclass
class AuthManager:
    """
    Manages TOTP authentication and session tokens.

    TOTP secret is stored encrypted in the secrets vault,
    never in plaintext config or environment variables.
    """

    totp_secret: str = ""
    session_timeout: int = 3600  # 1 hour default
    _sessions: dict[str, Session] = field(default_factory=dict)

    def setup_totp(self) -> str:
        """Generate a new TOTP secret. Returns the provisioning URI."""
        self.totp_secret = pyotp.random_base32()
        uri = pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name="gulama",
            issuer_name="Gulama Bot",
        )
        logger.info("totp_setup", msg="New TOTP secret generated")
        return uri

    def verify_totp(self, code: str) -> str | None:
        """
        Verify a TOTP code and return a session token if valid.
        Returns None if code is invalid.
        """
        if not self.totp_secret:
            logger.error("totp_not_configured")
            return None

        totp = pyotp.TOTP(self.totp_secret)
        if totp.verify(code, valid_window=1):
            token = self._create_session()
            logger.info("auth_success", method="totp")
            return token

        logger.warning("auth_failed", method="totp")
        return None

    def verify_session(self, token: str) -> bool:
        """Verify a session token is valid and not expired."""
        session = self._sessions.get(token)
        if session is None:
            return False

        now = time.time()
        if now - session.last_active > self.session_timeout:
            # Session expired
            self._sessions.pop(token, None)
            logger.info("session_expired", token_hash=_hash_token(token))
            return False

        # Update last active
        session.last_active = now
        return True

    def revoke_session(self, token: str) -> None:
        """Revoke a session token."""
        if token in self._sessions:
            del self._sessions[token]
            logger.info("session_revoked", token_hash=_hash_token(token))

    def revoke_all_sessions(self) -> int:
        """Revoke all active sessions. Returns count of revoked sessions."""
        count = len(self._sessions)
        self._sessions.clear()
        logger.info("all_sessions_revoked", count=count)
        return count

    def get_active_session_count(self) -> int:
        """Get number of active (non-expired) sessions."""
        self._cleanup_expired()
        return len(self._sessions)

    def _create_session(self) -> str:
        """Create a new session and return its token."""
        token = secrets.token_hex(TOKEN_BYTES)
        now = time.time()
        self._sessions[token] = Session(
            token=token,
            created_at=now,
            last_active=now,
        )
        logger.info("session_created", token_hash=_hash_token(token))
        return token

    def _cleanup_expired(self) -> None:
        """Remove expired sessions."""
        now = time.time()
        expired = [
            token
            for token, session in self._sessions.items()
            if now - session.last_active > self.session_timeout
        ]
        for token in expired:
            del self._sessions[token]


def _hash_token(token: str) -> str:
    """Hash a token for safe logging (never log raw tokens)."""
    return hashlib.sha256(token.encode()).hexdigest()[:12]
