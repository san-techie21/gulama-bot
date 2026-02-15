"""
API routes for the Gulama gateway.

All routes require authentication (enforced by middleware)
except those in AuthenticationMiddleware.PUBLIC_PATHS.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

api_router = APIRouter()


# ──────────────────────── Auth ────────────────────────


class TOTPRequest(BaseModel):
    code: str


class TOTPResponse(BaseModel):
    token: str
    expires_in: int


class SetupTOTPResponse(BaseModel):
    provisioning_uri: str
    message: str


@api_router.post("/auth/totp", response_model=TOTPResponse)
async def authenticate_totp(request: Request, body: TOTPRequest) -> TOTPResponse:
    """Authenticate with a TOTP code and receive a session token."""
    auth_manager = request.app.state.auth_manager

    token = auth_manager.verify_totp(body.code)
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid TOTP code.")

    return TOTPResponse(
        token=token,
        expires_in=auth_manager.session_timeout,
    )


@api_router.post("/auth/setup-totp", response_model=SetupTOTPResponse)
async def setup_totp(request: Request) -> SetupTOTPResponse:
    """Set up TOTP authentication. Returns provisioning URI for authenticator apps."""
    auth_manager = request.app.state.auth_manager

    if auth_manager.totp_secret:
        raise HTTPException(
            status_code=409,
            detail="TOTP already configured. Revoke first to reconfigure.",
        )

    uri = auth_manager.setup_totp()
    return SetupTOTPResponse(
        provisioning_uri=uri,
        message="Scan the QR code with your authenticator app.",
    )


@api_router.post("/auth/logout")
async def logout(request: Request) -> dict:
    """Revoke the current session."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        request.app.state.auth_manager.revoke_session(token)
    return {"status": "logged_out"}


# ──────────────────────── Chat ────────────────────────


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    tokens_used: int = 0
    cost_usd: float = 0.0


@api_router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """Send a message to the Gulama agent and get a response."""
    from src.agent.brain import AgentBrain

    config = request.app.state.config
    brain = AgentBrain(config=config)

    result = await brain.process_message(
        message=body.message,
        conversation_id=body.conversation_id,
        channel="gateway",
    )

    return ChatResponse(
        response=result["response"],
        conversation_id=result["conversation_id"],
        tokens_used=result.get("tokens_used", 0),
        cost_usd=result.get("cost_usd", 0.0),
    )


# ──────────────────────── Status ────────────────────────


@api_router.get("/status")
async def get_status(request: Request) -> dict:
    """Get current agent status and statistics."""
    config = request.app.state.config
    auth_manager = request.app.state.auth_manager

    return {
        "active_sessions": auth_manager.get_active_session_count(),
        "llm": {
            "provider": config.llm.provider,
            "model": config.llm.model,
        },
        "autonomy_level": config.autonomy.default_level,
        "security": {
            "sandbox": config.security.sandbox_enabled,
            "policy_engine": config.security.policy_engine_enabled,
        },
    }


# ──────────────────────── Cost ────────────────────────


@api_router.get("/cost/today")
async def get_today_cost(request: Request) -> dict:
    """Get today's token usage and cost."""
    from src.memory.store import MemoryStore

    store = MemoryStore()
    store.open()
    cost = store.get_today_cost()
    stats = store.get_stats()
    store.close()

    config = request.app.state.config
    budget = config.cost.daily_budget_usd

    return {
        "today_cost_usd": cost,
        "daily_budget_usd": budget,
        "budget_remaining_usd": max(0.0, budget - cost),
        "budget_used_percent": (cost / budget * 100) if budget > 0 else 0,
        "stats": stats,
    }


@api_router.get("/cost/history")
async def get_cost_history(request: Request, days: int = 7) -> dict:
    """Get cost history for the last N days."""
    from src.memory.store import MemoryStore

    store = MemoryStore()
    store.open()
    history = store.get_cost_summary(days=days)
    store.close()

    return {"days": days, "history": history}
