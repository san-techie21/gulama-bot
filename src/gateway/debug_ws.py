"""
WebSocket debug tools for Gulama.

Provides real-time inspection of:
- Agent actions and tool calls
- Policy engine decisions
- Token usage and costs
- Memory operations
- Sub-agent activity
- Audit log stream

Connect to ws://localhost:18789/ws/debug?token=SESSION_TOKEN
to get a live stream of agent activity.

Message format:
    {"type": "tool_call", "skill": "shell_exec", "args": {...}, "timestamp": "..."}
    {"type": "policy_decision", "action": "SHELL_EXEC", "decision": "allow", "timestamp": "..."}
    {"type": "token_usage", "tokens": 150, "cost_usd": 0.003, "timestamp": "..."}
    {"type": "sub_agent", "agent_id": "sa-12345", "status": "completed", "timestamp": "..."}
    {"type": "audit", "action": "file_read", "resource": "/tmp/test.txt", "timestamp": "..."}
"""

from __future__ import annotations

import asyncio
import json
from collections import deque
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.utils.logging import get_logger

logger = get_logger("debug_ws")

debug_router = APIRouter()


class DebugEventBus:
    """
    Global event bus for debug events.

    Components publish events here, and all connected debug WebSocket
    clients receive them in real-time.
    """

    _instance: DebugEventBus | None = None

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue] = []
        self._history: deque[dict[str, Any]] = deque(maxlen=200)
        self._enabled = False

    @classmethod
    def get(cls) -> DebugEventBus:
        """Get the singleton debug event bus."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to debug events. Returns a queue to read from."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from debug events."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def publish(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Publish a debug event to all subscribers."""
        if not self._enabled and not self._subscribers:
            return

        event = {
            "type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            **(data or {}),
        }

        self._history.append(event)

        dead_queues = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(queue)

        for q in dead_queues:
            self._subscribers.remove(q)

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent debug events."""
        items = list(self._history)
        return items[-limit:] if len(items) > limit else items

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# Convenience functions for publishing debug events
async def debug_tool_call(skill: str, args: dict[str, Any], result: str = "") -> None:
    """Publish a tool call debug event."""
    await DebugEventBus.get().publish(
        "tool_call",
        {
            "skill": skill,
            "args": {k: str(v)[:100] for k, v in args.items()},
            "result_preview": result[:200],
        },
    )


async def debug_policy_decision(
    action: str, resource: str, decision: str, policy: str = ""
) -> None:
    """Publish a policy engine decision debug event."""
    await DebugEventBus.get().publish(
        "policy_decision",
        {
            "action": action,
            "resource": resource[:200],
            "decision": decision,
            "policy": policy,
        },
    )


async def debug_token_usage(tokens: int, cost_usd: float, model: str = "") -> None:
    """Publish a token usage debug event."""
    await DebugEventBus.get().publish(
        "token_usage",
        {
            "tokens": tokens,
            "cost_usd": round(cost_usd, 6),
            "model": model,
        },
    )


async def debug_memory_op(operation: str, key: str = "", size: int = 0) -> None:
    """Publish a memory operation debug event."""
    await DebugEventBus.get().publish(
        "memory_op",
        {
            "operation": operation,
            "key": key[:100],
            "size": size,
        },
    )


async def debug_sub_agent(agent_id: str, status: str, message: str = "") -> None:
    """Publish a sub-agent activity debug event."""
    await DebugEventBus.get().publish(
        "sub_agent",
        {
            "agent_id": agent_id,
            "status": status,
            "message": message[:200],
        },
    )


async def debug_audit(action: str, resource: str, decision: str) -> None:
    """Publish an audit log debug event."""
    await DebugEventBus.get().publish(
        "audit",
        {
            "action": action,
            "resource": resource[:200],
            "decision": decision,
        },
    )


# ── WebSocket endpoint ──────────────────────────────────────────


@debug_router.websocket("/debug")
async def websocket_debug(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time debug event streaming.

    Connect: ws://localhost:18789/ws/debug?token=SESSION_TOKEN

    Commands (send):
        {"type": "subscribe"}           — Start receiving events
        {"type": "history", "limit": N}  — Get recent events
        {"type": "ping"}                 — Heartbeat

    Events (receive):
        {"type": "tool_call", ...}
        {"type": "policy_decision", ...}
        {"type": "token_usage", ...}
        {"type": "memory_op", ...}
        {"type": "sub_agent", ...}
        {"type": "audit", ...}
    """
    # Authenticate
    token = websocket.query_params.get("token", "")
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    auth_manager = websocket.app.state.auth_manager
    if not auth_manager.verify_session(token):
        await websocket.close(code=4001, reason="Invalid session")
        return

    await websocket.accept()

    bus = DebugEventBus.get()
    bus.enable()
    queue = bus.subscribe()

    logger.info("debug_ws_connected")

    # Send initial history
    history = bus.get_history(50)
    await websocket.send_json(
        {
            "type": "connected",
            "history_count": len(history),
            "subscriber_count": bus.subscriber_count,
        }
    )

    # Two concurrent tasks: read commands, stream events
    async def stream_events() -> None:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                await websocket.send_json(event)
            except TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})
            except Exception:
                break

    async def read_commands() -> None:
        while True:
            try:
                raw = await websocket.receive_text()
                data = json.loads(raw)
                cmd_type = data.get("type", "")

                if cmd_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif cmd_type == "history":
                    limit = data.get("limit", 50)
                    history = bus.get_history(min(limit, 200))
                    await websocket.send_json(
                        {
                            "type": "history",
                            "events": history,
                        }
                    )
                elif cmd_type == "stats":
                    await websocket.send_json(
                        {
                            "type": "stats",
                            "subscriber_count": bus.subscriber_count,
                            "history_size": len(bus._history),
                        }
                    )

            except (WebSocketDisconnect, Exception):
                break

    try:
        await asyncio.gather(stream_events(), read_commands())
    except Exception:
        pass
    finally:
        bus.unsubscribe(queue)
        logger.info("debug_ws_disconnected")
