"""Health check endpoints — no authentication required."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.constants import PROJECT_DISPLAY_NAME, PROJECT_VERSION

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
async def health_check(request: Request) -> dict:
    """Basic health check. No auth required."""
    return {
        "status": "ok",
        "service": PROJECT_DISPLAY_NAME,
        "version": PROJECT_VERSION,
    }


@health_router.get("/health/detailed")
async def detailed_health(request: Request) -> dict:
    """Detailed health check with component status."""
    config = request.app.state.config

    return {
        "status": "ok",
        "version": PROJECT_VERSION,
        "components": {
            "gateway": "ok",
            "auth": "ok",
            "llm_provider": config.llm.provider,
            "llm_model": config.llm.model,
            "security": {
                "sandbox": config.security.sandbox_enabled,
                "policy_engine": config.security.policy_engine_enabled,
                "canary_tokens": config.security.canary_tokens_enabled,
                "egress_filtering": config.security.egress_filtering_enabled,
                "audit_logging": config.security.audit_logging_enabled,
            },
        },
    }
