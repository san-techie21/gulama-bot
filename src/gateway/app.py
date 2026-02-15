"""
FastAPI gateway for Gulama — loopback-only, TOTP-authenticated.

This is the main HTTP/WebSocket server that:
- Binds to 127.0.0.1 ONLY (never 0.0.0.0 without explicit flag)
- Requires TOTP authentication for all API access
- Provides REST API and WebSocket for real-time chat
- Applies security headers, rate limiting, and request size limits
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.constants import PROJECT_DISPLAY_NAME, PROJECT_VERSION
from src.gateway.auth import AuthManager
from src.gateway.config import load_config
from src.gateway.middleware import (
    AuthenticationMiddleware,
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from src.utils.logging import get_logger, setup_logging

logger = get_logger("gateway")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = load_config()

    setup_logging(
        level=config.logging.level,
        json_format=config.logging.format == "json",
    )

    app = FastAPI(
        title=f"{PROJECT_DISPLAY_NAME} API",
        version=PROJECT_VERSION,
        description="Secure personal AI agent gateway",
        docs_url="/docs" if os.getenv("GULAMA_DEV") else None,
        redoc_url=None,
    )

    # Store config and auth manager in app state
    app.state.config = config
    app.state.auth_manager = AuthManager(
        session_timeout=config.auth.session_timeout_seconds,
    )

    # Apply middleware (order matters — outermost first)
    _add_middleware(app, config)

    # Register routes
    _register_routes(app)

    # Startup/shutdown hooks
    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info(
            "gateway_started",
            host=config.gateway.host,
            port=config.gateway.port,
            version=PROJECT_VERSION,
        )
        # Write PID file
        from src.constants import DATA_DIR
        pid_file = DATA_DIR / "gulama.pid"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(os.getpid()))

        # Initialize sub-agent manager and scheduler
        try:
            from src.agent.sub_agents import SubAgentManager, create_scheduler_handlers
            from src.channels.scheduler import TaskScheduler

            sub_agent_mgr = SubAgentManager(max_concurrent=5)
            scheduler = TaskScheduler()

            # Wire scheduler handlers
            handlers = create_scheduler_handlers(sub_agent_mgr)
            for action_type, handler in handlers.items():
                scheduler.register_handler(action_type, handler)

            # Add default scheduled tasks
            scheduler.add_heartbeat(interval_seconds=300)
            scheduler.add_memory_cleanup(interval_hours=24)

            # Store in app state for route access
            app.state.sub_agent_manager = sub_agent_mgr
            app.state.scheduler = scheduler

            # Start scheduler loop
            await scheduler.start()
            logger.info("scheduler_and_subagents_ready")
        except Exception as e:
            logger.warning("scheduler_init_failed", error=str(e))

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("gateway_stopped")

        # Stop scheduler
        if hasattr(app.state, "scheduler"):
            try:
                await app.state.scheduler.stop()
            except Exception:
                pass

        # Cancel sub-agents
        if hasattr(app.state, "sub_agent_manager"):
            try:
                await app.state.sub_agent_manager.cancel_all()
            except Exception:
                pass

        from src.constants import DATA_DIR
        pid_file = DATA_DIR / "gulama.pid"
        pid_file.unlink(missing_ok=True)

    return app


def _add_middleware(app: FastAPI, config) -> None:
    """Add all security middleware layers."""
    # Authentication (innermost — runs last on request, first on response)
    app.add_middleware(AuthenticationMiddleware)

    # Request size limit
    app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=10 * 1024 * 1024)

    # Rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=60,
        window=60,
    )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS — strict origin validation
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.gateway.websocket_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


def _register_routes(app: FastAPI) -> None:
    """Register all API route handlers."""
    from src.gateway.router import api_router
    from src.gateway.health import health_router
    from src.gateway.websocket import ws_router
    from src.gateway.debug_ws import debug_router

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(ws_router, prefix="/ws")
    app.include_router(debug_router, prefix="/ws")
