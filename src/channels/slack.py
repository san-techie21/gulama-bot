"""
Slack channel for Gulama.

Uses Slack's Bolt framework for event handling and slash commands.
Supports:
- Direct messages
- App mentions in channels
- Slash commands (/gulama)
- Interactive message actions
- Thread-based conversations
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import time
from typing import Any

import httpx

from src.channels.base import BaseChannel
from src.utils.logging import get_logger

logger = get_logger("slack_channel")

SLACK_API_BASE = "https://slack.com/api"


class SlackChannel(BaseChannel):
    """
    Slack bot channel.

    Configuration:
    - SLACK_BOT_TOKEN: Bot User OAuth Token (xoxb-...)
    - SLACK_APP_TOKEN: App-Level Token for Socket Mode (xapp-...)
    - SLACK_SIGNING_SECRET: For verifying webhook requests
    - SLACK_ALLOWED_USERS: Comma-separated user IDs (optional)
    """

    def __init__(
        self,
        bot_token: str,
        signing_secret: str,
        app_token: str | None = None,
        allowed_user_ids: list[str] | None = None,
        allowed_channel_ids: list[str] | None = None,
    ):
        super().__init__(channel_name="slack")
        self.bot_token = bot_token
        self.signing_secret = signing_secret
        self.app_token = app_token
        self.allowed_user_ids = set(allowed_user_ids) if allowed_user_ids else None
        self.allowed_channel_ids = set(allowed_channel_ids) if allowed_channel_ids else None
        self._agent_brain = None
        self._message_handler = None
        self._http_client: httpx.AsyncClient | None = None
        self._bot_user_id: str | None = None

    def set_agent(self, agent_brain: Any) -> None:
        """Set the agent brain for processing messages."""
        self._agent_brain = agent_brain

    def set_message_handler(self, handler: Any) -> None:
        """Set an external message handler."""
        self._message_handler = handler

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=SLACK_API_BASE,
                headers={
                    "Authorization": f"Bearer {self.bot_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                timeout=30.0,
            )
        return self._http_client

    async def _identify_bot(self) -> None:
        """Get the bot's user ID."""
        client = await self._get_http_client()
        response = await client.post("/auth.test")
        data = response.json()
        if data.get("ok"):
            self._bot_user_id = data.get("user_id")
            logger.info("slack_identified", bot_user_id=self._bot_user_id)

    def verify_request(self, timestamp: str, body: bytes, signature: str) -> bool:
        """Verify incoming Slack request signature."""
        # Check timestamp (prevent replay attacks)
        if abs(time.time() - float(timestamp)) > 300:
            return False

        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        expected = (
            "v0="
            + hmac.new(
                self.signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        return hmac.compare_digest(expected, signature)

    async def handle_event(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Handle incoming Slack event."""
        event_type = payload.get("type")

        # URL verification challenge
        if event_type == "url_verification":
            return {"challenge": payload.get("challenge", "")}

        # Event callback
        if event_type == "event_callback":
            event = payload.get("event", {})
            await self._process_event(event)

        return None

    async def _process_event(self, event: dict[str, Any]) -> None:
        """Process a Slack event."""
        event_type = event.get("type")
        user = event.get("user", "")
        channel = event.get("channel", "")
        text = event.get("text", "")
        thread_ts = event.get("thread_ts") or event.get("ts")

        # Skip bot messages
        if event.get("bot_id") or user == self._bot_user_id:
            return

        # Check authorization
        if not self._is_authorized(user, channel):
            return

        if event_type == "message":
            # DM — respond to everything
            if event.get("channel_type") == "im":
                await self._handle_message(text, user, channel, thread_ts)

        elif event_type == "app_mention":
            # Mentioned in channel — strip mention and respond
            cleaned = text
            if self._bot_user_id:
                cleaned = text.replace(f"<@{self._bot_user_id}>", "").strip()
            await self._handle_message(cleaned, user, channel, thread_ts)

    async def handle_slash_command(self, payload: dict[str, Any]) -> str:
        """Handle slash command (/gulama)."""
        user = payload.get("user_id", "")
        text = payload.get("text", "").strip()
        channel = payload.get("channel_id", "")

        if not self._is_authorized(user, channel):
            return "You are not authorized to use this bot."

        if not text:
            return "Usage: /gulama <your message>"

        # Process in background and send response via webhook
        response_url = payload.get("response_url")
        if response_url:
            asyncio.create_task(self._async_slash_response(text, user, response_url))
            return "Thinking..."

        response = await self._get_response(text, user)
        return response[:3000]

    async def _async_slash_response(self, text: str, user: str, response_url: str) -> None:
        """Send async response to slash command."""
        response = await self._get_response(text, user)
        async with httpx.AsyncClient() as client:
            await client.post(
                response_url,
                json={"text": response[:3000], "response_type": "ephemeral"},
            )

    async def _handle_message(
        self, text: str, user: str, channel: str, thread_ts: str | None
    ) -> None:
        """Handle a message and respond."""
        if not text.strip():
            return

        logger.info("slack_message_received", user=user[:6] + "***")

        response = await self._get_response(text, user)
        await self._send_to_channel(channel, response, thread_ts)

    async def _get_response(self, content: str, user_id: str) -> str:
        """Get a response from the agent."""
        try:
            if self._message_handler:
                return await self._message_handler(content, user_id, "slack")
            elif self._agent_brain:
                result = await self._agent_brain.process_message(content, channel="slack")
                return result.get("response", "No response.")
            return "Bot is not configured."
        except Exception as e:
            logger.error("slack_response_failed", error=str(e))
            return f"Error: {str(e)[:100]}"

    async def _send_to_channel(self, channel: str, text: str, thread_ts: str | None = None) -> None:
        """Send a message to a Slack channel."""
        client = await self._get_http_client()

        # Split long messages (Slack limit: 4000 chars)
        chunks = self._split_message(text, 3900)

        for chunk in chunks:
            payload: dict[str, Any] = {
                "channel": channel,
                "text": chunk,
            }
            if thread_ts:
                payload["thread_ts"] = thread_ts

            try:
                response = await client.post("/chat.postMessage", json=payload)
                data = response.json()
                if not data.get("ok"):
                    logger.error("slack_send_failed", error=data.get("error"))
            except Exception as e:
                logger.error("slack_send_error", error=str(e))

    async def send_message(self, user_id: str, content: str, **kwargs: Any) -> None:
        """Send a direct message to a Slack user."""
        client = await self._get_http_client()

        # Open DM channel
        try:
            response = await client.post(
                "/conversations.open",
                json={"users": user_id},
            )
            data = response.json()
            if data.get("ok"):
                channel_id = data["channel"]["id"]
                await self._send_to_channel(channel_id, content)
        except Exception as e:
            logger.error("slack_dm_failed", error=str(e))

    def _is_authorized(self, user_id: str, channel_id: str | None = None) -> bool:
        """Check if a user/channel is authorized."""
        if self.allowed_user_ids and user_id not in self.allowed_user_ids:
            return False
        if self.allowed_channel_ids and channel_id and channel_id not in self.allowed_channel_ids:
            return False
        return True

    def run(self) -> None:
        """Start the Slack channel."""
        self._running = True
        logger.info("slack_channel_ready", msg="Event endpoints registered")

    def stop(self) -> None:
        """Stop the Slack channel."""
        self._running = False
        if self._http_client:
            asyncio.get_event_loop().create_task(self._http_client.aclose())
        logger.info("slack_stopped")

    @staticmethod
    def _split_message(text: str, max_length: int) -> list[str]:
        """Split a long message into chunks."""
        if len(text) <= max_length:
            return [text]
        chunks = []
        while text:
            if len(text) <= max_length:
                chunks.append(text)
                break
            split_at = text.rfind("\n", 0, max_length)
            if split_at == -1:
                split_at = text.rfind(" ", 0, max_length)
            if split_at == -1:
                split_at = max_length
            chunks.append(text[:split_at])
            text = text[split_at:].lstrip()
        return chunks


def register_slack_routes(app: Any, channel: SlackChannel) -> None:
    """Register Slack event/command routes on the FastAPI app."""
    from fastapi import Request, Response
    from fastapi.responses import JSONResponse

    @app.post("/webhook/slack/events")
    async def slack_events(request: Request):
        """Slack Events API endpoint."""
        body = await request.body()
        timestamp = request.headers.get("x-slack-request-timestamp", "0")
        signature = request.headers.get("x-slack-signature", "")

        if not channel.verify_request(timestamp, body, signature):
            return Response(status_code=403)

        payload = await request.json()
        result = await channel.handle_event(payload)

        if result:
            return JSONResponse(result)
        return Response(status_code=200)

    @app.post("/webhook/slack/commands")
    async def slack_commands(request: Request):
        """Slack slash command endpoint."""
        body = await request.body()
        timestamp = request.headers.get("x-slack-request-timestamp", "0")
        signature = request.headers.get("x-slack-signature", "")

        if not channel.verify_request(timestamp, body, signature):
            return Response(status_code=403)

        form = await request.form()
        payload = dict(form)
        response_text = await channel.handle_slash_command(payload)
        return JSONResponse({"text": response_text, "response_type": "ephemeral"})
