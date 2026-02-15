"""
WebSocket handler for real-time Gulama chat.

Supports:
- Authenticated WebSocket connections (token in query param)
- Streaming responses from the LLM
- Connection management with heartbeat
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.utils.logging import get_logger

logger = get_logger("websocket")

ws_router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self) -> None:
        self._active: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        self._active[session_id] = websocket
        logger.info("ws_connected", session_id=session_id[:12])

    def disconnect(self, session_id: str) -> None:
        self._active.pop(session_id, None)
        logger.info("ws_disconnected", session_id=session_id[:12])

    async def send_json(self, session_id: str, data: dict) -> None:
        ws = self._active.get(session_id)
        if ws:
            await ws.send_json(data)

    @property
    def active_count(self) -> int:
        return len(self._active)


manager = ConnectionManager()


@ws_router.websocket("/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time chat.

    Connect with: ws://localhost:18789/ws/chat?token=SESSION_TOKEN

    Message format (send):
        {"type": "message", "content": "Hello", "conversation_id": "optional-id"}

    Message format (receive):
        {"type": "chunk", "content": "partial response..."}
        {"type": "complete", "content": "full response", "conversation_id": "...", "tokens_used": 0}
        {"type": "error", "content": "error message"}
    """
    # Authenticate via query param token
    token = websocket.query_params.get("token", "")
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    auth_manager = websocket.app.state.auth_manager
    if not auth_manager.verify_session(token):
        await websocket.close(code=4001, reason="Invalid or expired session")
        return

    session_id = token
    await manager.connect(websocket, session_id)

    try:
        while True:
            # Receive message
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid JSON",
                })
                continue

            msg_type = data.get("type", "message")
            content = data.get("content", "")
            conversation_id = data.get("conversation_id")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type != "message" or not content:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid message format. Expected {type: 'message', content: '...'}",
                })
                continue

            # Process through agent brain
            try:
                config = websocket.app.state.config
                from src.agent.brain import AgentBrain

                brain = AgentBrain(config=config)

                # Stream response chunks
                async for chunk in brain.stream_message(
                    message=content,
                    conversation_id=conversation_id,
                    channel="websocket",
                ):
                    if chunk.get("type") == "chunk":
                        await websocket.send_json({
                            "type": "chunk",
                            "content": chunk["content"],
                        })
                    elif chunk.get("type") == "complete":
                        await websocket.send_json({
                            "type": "complete",
                            "content": chunk["content"],
                            "conversation_id": chunk.get("conversation_id", ""),
                            "tokens_used": chunk.get("tokens_used", 0),
                            "cost_usd": chunk.get("cost_usd", 0.0),
                        })

            except Exception as e:
                logger.error("ws_processing_error", error=str(e))
                await websocket.send_json({
                    "type": "error",
                    "content": f"Processing error: {str(e)}",
                })

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error("ws_error", error=str(e))
        manager.disconnect(session_id)
