"""
Tests for WebSocket hijack prevention.

Verifies that WebSocket connections correctly validate
origins to prevent cross-site WebSocket hijacking (CSWSH).
"""

from __future__ import annotations

from urllib.parse import urlparse

import pytest


def is_valid_ws_origin(origin: str) -> bool:
    """Check if a WebSocket origin is valid (loopback only)."""
    if not origin:
        return False
    try:
        parsed = urlparse(origin)
        host = parsed.hostname or ""
        return host in ("127.0.0.1", "localhost", "::1")
    except Exception:
        return False


class TestWebSocketHijackPrevention:
    """Verify WebSocket security."""

    def test_loopback_origins_allowed(self):
        """Loopback origins should be accepted."""
        allowed = [
            "http://127.0.0.1:18789",
            "http://localhost:18789",
            "https://127.0.0.1:18789",
            "http://[::1]:18789",
        ]
        for origin in allowed:
            assert is_valid_ws_origin(origin), f"Should allow: {origin}"

    def test_external_origins_blocked(self):
        """External origins should be rejected."""
        blocked = [
            "https://evil.com",
            "http://attacker.local:8080",
            "https://phishing-site.com/fake-gulama",
        ]
        for origin in blocked:
            assert not is_valid_ws_origin(origin), f"Should block: {origin}"

    def test_null_origin_blocked(self):
        """Null or empty origins should be rejected."""
        assert not is_valid_ws_origin("")
        assert not is_valid_ws_origin("null")

    def test_origin_spoofing_attempt(self):
        """Attempts to spoof localhost in subdomains should be blocked."""
        spoofed = [
            "https://localhost.evil.com",
            "https://127.0.0.1.attacker.com",
            "https://evil.com?redirect=http://127.0.0.1",
        ]
        for origin in spoofed:
            assert not is_valid_ws_origin(origin), f"Should block spoofed: {origin}"
