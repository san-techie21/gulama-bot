"""
Security middleware for the Gulama gateway.

- Rate limiting per IP
- Request size limits
- CORS with strict origin validation
- Security headers (CSP, HSTS, X-Frame-Options, etc.)
- Authentication enforcement
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.utils.logging import get_logger

logger = get_logger("middleware")

# Rate limiting: max requests per IP per window
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 60  # requests per window


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self' ws://localhost:* wss://localhost:*; "
            "frame-ancestors 'none'"
        )

        # Remove server header (information disclosure)
        if "server" in response.headers:
            del response.headers["server"]

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting per client IP."""

    def __init__(self, app, max_requests: int = RATE_LIMIT_MAX, window: int = RATE_LIMIT_WINDOW):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean old entries
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if now - t < self.window
        ]

        if len(self._requests[client_ip]) >= self.max_requests:
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                count=len(self._requests[client_ip]),
            )
            return JSONResponse(
                {"error": "Rate limit exceeded. Try again later."},
                status_code=429,
                headers={"Retry-After": str(self.window)},
            )

        self._requests[client_ip].append(now)
        return await call_next(request)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests that exceed the size limit."""

    def __init__(self, app, max_size_bytes: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size_bytes = max_size_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size_bytes:
            return JSONResponse(
                {"error": "Request too large."},
                status_code=413,
            )
        return await call_next(request)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Enforce authentication on protected endpoints."""

    # Endpoints that don't require auth
    PUBLIC_PATHS = {"/health", "/api/v1/auth/totp", "/docs", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Skip auth for public endpoints
        if path in self.PUBLIC_PATHS or path.startswith("/static"):
            return await call_next(request)

        # Check for session token
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            # Also check query param (for WebSocket connections)
            token = request.query_params.get("token", "")

        if not token:
            return JSONResponse(
                {"error": "Authentication required."},
                status_code=401,
            )

        # Verify token via the auth manager (injected into app state)
        auth_manager = request.app.state.auth_manager
        if not auth_manager.verify_session(token):
            return JSONResponse(
                {"error": "Invalid or expired session."},
                status_code=401,
            )

        # Attach session info to request state
        request.state.authenticated = True
        return await call_next(request)
