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


# ──────────────────────── Skills ────────────────────────


@api_router.get("/skills")
async def list_skills(request: Request) -> dict:
    """List all registered skills and their metadata."""
    from src.agent.brain import AgentBrain

    config = request.app.state.config
    brain = AgentBrain(config=config)
    skills = brain.skill_registry.list_skills()

    return {
        "count": len(skills),
        "skills": [
            {
                "name": s.name,
                "description": s.description,
                "version": s.version,
                "author": s.author,
                "builtin": s.is_builtin,
            }
            for s in skills
        ],
    }


# ──────────────────────── Scheduler ────────────────────────


class ScheduleTaskRequest(BaseModel):
    name: str
    schedule_type: str  # "cron", "interval", "once"
    schedule_value: str
    action_type: str  # "message", "skill", "summarize", "heartbeat"
    action_config: dict | None = None


@api_router.get("/scheduler/tasks")
async def list_scheduled_tasks(request: Request) -> dict:
    """List all scheduled tasks."""
    scheduler = getattr(request.app.state, "scheduler", None)
    if not scheduler:
        return {"tasks": [], "error": "Scheduler not initialized"}
    return {"tasks": scheduler.list_tasks()}


@api_router.post("/scheduler/tasks")
async def create_scheduled_task(request: Request, body: ScheduleTaskRequest) -> dict:
    """Create a new scheduled task."""
    scheduler = getattr(request.app.state, "scheduler", None)
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")

    task_id = scheduler.add_task(
        name=body.name,
        schedule_type=body.schedule_type,
        schedule_value=body.schedule_value,
        action_type=body.action_type,
        action_config=body.action_config or {},
    )
    return {"task_id": task_id, "status": "created"}


@api_router.delete("/scheduler/tasks/{task_id}")
async def delete_scheduled_task(request: Request, task_id: str) -> dict:
    """Delete a scheduled task."""
    scheduler = getattr(request.app.state, "scheduler", None)
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")

    if scheduler.remove_task(task_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Task not found")


# ──────────────────────── Sub-Agents ────────────────────────


class SpawnAgentRequest(BaseModel):
    message: str
    channel: str = "api"


@api_router.get("/agents")
async def list_sub_agents(request: Request) -> dict:
    """List all sub-agents and their status."""
    mgr = getattr(request.app.state, "sub_agent_manager", None)
    if not mgr:
        return {"agents": [], "active_count": 0}
    return {
        "agents": mgr.list_agents(),
        "active_count": mgr.active_count,
    }


@api_router.post("/agents/spawn")
async def spawn_sub_agent(request: Request, body: SpawnAgentRequest) -> dict:
    """Spawn a new background sub-agent."""
    mgr = getattr(request.app.state, "sub_agent_manager", None)
    if not mgr:
        raise HTTPException(status_code=503, detail="Sub-agent manager not initialized")

    try:
        agent_id = await mgr.spawn(
            message=body.message,
            channel=body.channel,
        )
        return {"agent_id": agent_id, "status": "spawned"}
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))


@api_router.get("/agents/{agent_id}")
async def get_sub_agent(request: Request, agent_id: str) -> dict:
    """Get a sub-agent's status and result."""
    mgr = getattr(request.app.state, "sub_agent_manager", None)
    if not mgr:
        raise HTTPException(status_code=503, detail="Sub-agent manager not initialized")

    result = mgr.get_result(agent_id)
    if not result:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "id": result.agent_id,
        "status": result.status.value,
        "output": result.output,
        "error": result.error,
        "tools_used": result.tools_used,
        "tokens_used": result.tokens_used,
        "cost_usd": result.cost_usd,
        "started_at": str(result.started_at) if result.started_at else None,
        "completed_at": str(result.completed_at) if result.completed_at else None,
    }


@api_router.post("/agents/{agent_id}/cancel")
async def cancel_sub_agent(request: Request, agent_id: str) -> dict:
    """Cancel a running sub-agent."""
    mgr = getattr(request.app.state, "sub_agent_manager", None)
    if not mgr:
        raise HTTPException(status_code=503, detail="Sub-agent manager not initialized")

    if await mgr.cancel(agent_id):
        return {"status": "cancelled"}
    raise HTTPException(status_code=404, detail="Agent not found or not running")


# ──────────────────────── Conversations ────────────────────────


@api_router.get("/conversations")
async def list_conversations(request: Request, limit: int = 20) -> dict:
    """List recent conversations."""
    from src.memory.store import MemoryStore

    store = MemoryStore()
    store.open()
    try:
        rows = store.conn.execute(
            "SELECT id, channel, user_id, started_at, ended_at, summary "
            "FROM conversations ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return {"conversations": [dict(r) for r in rows]}
    except Exception:
        return {"conversations": []}
    finally:
        store.close()


@api_router.get("/conversations/{conversation_id}")
async def get_conversation(request: Request, conversation_id: str) -> dict:
    """Get messages in a conversation."""
    from src.memory.store import MemoryStore

    store = MemoryStore()
    store.open()
    try:
        messages = store.get_messages(conversation_id)
        return {"conversation_id": conversation_id, "messages": messages}
    finally:
        store.close()


# ──────────────────────── Audit Log ────────────────────────


@api_router.get("/audit")
async def get_audit_log(request: Request, limit: int = 50) -> dict:
    """Get recent audit log entries."""
    from src.security.audit_logger import AuditLogger

    audit = AuditLogger()
    entries = audit.read_entries()  # Reads today's entries
    # Return the last N entries
    recent = entries[-limit:] if len(entries) > limit else entries
    return {
        "entries": [
            {
                "timestamp": e.timestamp,
                "action": e.action,
                "actor": e.actor,
                "resource": e.resource[:200],
                "decision": e.decision,
                "policy": e.policy,
                "detail": e.detail[:200],
                "channel": e.channel,
            }
            for e in reversed(recent)
        ],
        "count": len(recent),
    }
