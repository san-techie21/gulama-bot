"""
Web UI channel for Gulama.

Provides a REST + WebSocket backend for the React web frontend.
Handles:
- Chat messages via WebSocket (streaming)
- Session management
- File upload/download
- Settings management
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from src.channels.base import BaseChannel
from src.utils.logging import get_logger

logger = get_logger("web_channel")


class WebChannel(BaseChannel):
    """
    Web UI channel backend.

    The frontend connects via WebSocket for real-time streaming chat.
    REST endpoints handle session management, settings, and file operations.
    """

    def __init__(self):
        super().__init__(channel_name="web")
        self._agent_brain = None
        self._message_handler = None
        self._sessions: dict[str, dict[str, Any]] = {}

    def set_agent(self, agent_brain: Any) -> None:
        """Set the agent brain."""
        self._agent_brain = agent_brain

    def set_message_handler(self, handler: Any) -> None:
        """Set an external message handler."""
        self._message_handler = handler

    def create_session(self, user_id: str = "web_user") -> str:
        """Create a new chat session."""
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "id": session_id,
            "user_id": user_id,
            "conversation_id": None,
            "created_at": None,
            "messages": [],
        }
        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session data."""
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all active sessions."""
        return [
            {"id": s["id"], "user_id": s["user_id"], "message_count": len(s["messages"])}
            for s in self._sessions.values()
        ]

    async def handle_ws_message(
        self,
        session_id: str,
        message: str,
        send_fn: Any,
    ) -> None:
        """Handle a WebSocket message and stream the response."""
        session = self._sessions.get(session_id)
        if not session:
            await send_fn(json.dumps({"type": "error", "content": "Invalid session"}))
            return

        # Add user message to session
        session["messages"].append({"role": "user", "content": message})

        # Send acknowledgment
        await send_fn(json.dumps({"type": "ack", "content": "Processing..."}))

        try:
            # Try streaming response
            if self._agent_brain and hasattr(self._agent_brain, "stream_message"):
                full_response = ""
                async for chunk in self._agent_brain.stream_message(
                    message, channel="web"
                ):
                    full_response += chunk
                    await send_fn(json.dumps({
                        "type": "chunk",
                        "content": chunk,
                    }))

                # Send completion
                await send_fn(json.dumps({
                    "type": "done",
                    "content": full_response,
                }))

                session["messages"].append({"role": "assistant", "content": full_response})

            elif self._message_handler:
                response = await self._message_handler(message, session["user_id"], "web")
                await send_fn(json.dumps({
                    "type": "done",
                    "content": response,
                }))
                session["messages"].append({"role": "assistant", "content": response})

            elif self._agent_brain:
                result = await self._agent_brain.process_message(
                    message, channel="web"
                )
                response = result.get("text", "No response.")
                await send_fn(json.dumps({
                    "type": "done",
                    "content": response,
                }))
                session["messages"].append({"role": "assistant", "content": response})

            else:
                await send_fn(json.dumps({
                    "type": "error",
                    "content": "No agent configured.",
                }))

        except Exception as e:
            logger.error("web_message_error", error=str(e))
            await send_fn(json.dumps({
                "type": "error",
                "content": f"Error: {str(e)[:200]}",
            }))

    async def send_message(self, user_id: str, content: str, **kwargs: Any) -> None:
        """Send a message (no-op for web channel — responses go via WebSocket)."""
        logger.debug("web_send_message", user_id=user_id, length=len(content))

    def run(self) -> None:
        """Start the web channel (endpoints registered on gateway)."""
        self._running = True
        logger.info("web_channel_ready")

    def stop(self) -> None:
        """Stop the web channel."""
        self._running = False
        self._sessions.clear()
        logger.info("web_channel_stopped")


def register_web_routes(app: Any, channel: WebChannel) -> None:
    """Register web UI routes on the FastAPI app."""
    from fastapi import WebSocket, WebSocketDisconnect
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    from pathlib import Path

    # Serve static web UI files if they exist
    web_dist = Path(__file__).parent.parent.parent / "web" / "dist"
    if web_dist.exists():
        app.mount("/ui", StaticFiles(directory=str(web_dist), html=True), name="web-ui")

    @app.post("/api/v1/web/session")
    async def create_session():
        session_id = channel.create_session()
        return JSONResponse({"session_id": session_id})

    @app.get("/api/v1/web/sessions")
    async def list_sessions():
        return JSONResponse({"sessions": channel.list_sessions()})

    @app.websocket("/api/v1/web/ws/{session_id}")
    async def web_ws(websocket: WebSocket, session_id: str):
        session = channel.get_session(session_id)
        if not session:
            await websocket.close(code=4004, reason="Invalid session")
            return

        await websocket.accept()
        logger.info("web_ws_connected", session_id=session_id)

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    content = msg.get("content", data)
                except json.JSONDecodeError:
                    content = data

                await channel.handle_ws_message(
                    session_id,
                    content,
                    websocket.send_text,
                )
        except WebSocketDisconnect:
            logger.info("web_ws_disconnected", session_id=session_id)
